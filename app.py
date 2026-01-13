import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. Gemini AI 설정 (버전 문제를 해결하기 위한 다중 시도 로직)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 가장 범용적인 모델명 사용
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 설정 오류: {e}")
        model = None
else:
    st.warning("API 키를 확인해주세요.")
    model = None

# 뉴스 크롤링 함수
def get_news(stock_name):
    news_data = ""
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={stock_name}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        titles = soup.select(".news_tit")[:3]
        for t in titles:
            news_data += f"• {t.get_text()}\n"
    except:
        news_data = "뉴스를 가져오지 못했습니다."
    return news_data if news_data else "관련 뉴스가 없습니다."

# 3. 디자인 CSS (노란 박스 영역과 종목 리스트 색상 강제 변경)
st.markdown("""
    <style>
    /* 전체 배경 */
    .stApp { background-color: #05070a !important; }
    
    /* 섹션 헤더 */
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    
    /* 왼쪽/가운데 공통 박스 디자인 */
    .content-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; }
    
    /* [요청] 왼쪽 종목 버튼 배경색 상향 (#1c2128) */
    div.stButton > button {
        background-color: #1c2128 !important;
        color: white !important;
        border: 1px solid #30363d !important;
        text-align: left !important;
        padding: 10px !important;
        width: 100%;
    }

    /* [요청] 노란 박스(채팅 영역 전체) 배경색 강제 구분 (#1c2128) */
    /* st.container(height=...)의 내부 ID를 직접 공격합니다. */
    [data-testid="stChatMessageContainer"] {
        background-color: #1c2128 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
    }
    
    /* 말풍선 가독성 유지 */
    [data-testid="stChatMessage"] { background-color: #2d333b !important; }
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    return df

data = load_data()

if data is not None:
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "messages" not in st.session_state:
        st.session_state.messages = []

    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    with col1: # [요청] 왼쪽 리스트에 번호 강제 표시
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=700):
            # enumerate로 명시적인 번호 부여
            for i, (idx, row) in enumerate(data.iterrows()):
                # f-string으로 번호(1., 2. ...)를 텍스트에 직접 박음
                display_text = f"{i+1}. {row['종목명']} | {row['거래대금(억)']}억"
                if st.button(display_text, key=f"stock_btn_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2: # 중앙 분석창
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 상세 분석</div>', unsafe_allow_html=True)
        news = get_news(stock['종목명'])
        st.markdown(f"""
            <div class="content-box" style="height:700px; overflow-y: auto;">
                <h1 style="color:#00e5ff; margin-bottom:5px;">{stock['종목명']}</h1>
                <p style="color:#8b949e;">코드: {stock['종목코드']} | 유입대금: {stock['거래대금(억)']}억</p>
                <hr style="border-color:#333;">
                <h3 style="color:white;">📰 최신 뉴스 요약</h3>
                <div style="color:#ced4da; line-height:1.8;">{news}</div>
            </div>
        """, unsafe_allow_html=True)

    with col3: # [요청] 오른쪽 AI 채팅 영역 (배경색 구분)
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        chat_box = st.container(height=600)
        
        with chat_box:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.write(m["content"])

        if prompt := st.chat_input("종목에 대해 궁금한 점을 물어보세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_box:
                with st.chat_message("user"):
                    st.write(prompt)

            if model:
                try:
                    with chat_box:
                        with st.chat_message("assistant"):
                            with st.spinner("분석 중..."):
                                cur = st.session_state.selected_stock
                                news_data = get_news(cur['종목명'])
                                prompt_msg = f"당신은 주식 전문가입니다. {cur['종목명']}에 대한 뉴스({news_data})를 바탕으로 질문에 답하세요: {prompt}"
                                response = model.generate_content(prompt_msg)
                                st.write(response.text)
                                st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"AI 응답 오류: {str(e)}")
            st.rerun()
else:
    st.error("데이터를 불러올 수 없습니다.")