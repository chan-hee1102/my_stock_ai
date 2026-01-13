import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. Gemini AI 설정 (API 버전을 명확히 하여 404 에러 방지)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 최신 안정화 모델 사용
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 엔진 초기화 실패: {e}")
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
            news_data += f"- {t.get_text()}\n"
    except:
        news_data = "뉴스를 가져오지 못했습니다."
    return news_data

# 3. 디자인 CSS (노란 박스 영역 배경색 강제 적용)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    
    /* 왼쪽/가운데 박스 */
    .terminal-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 25px; height: 700px; overflow-y: auto; }
    
    /* 왼쪽 버튼 색상 상향 */
    .stButton > button { 
        width: 100%; background-color: #1c2128; color: #ffffff; 
        border: 1px solid #30363d; margin-bottom: 8px; text-align: left; padding: 12px;
    }

    /* [중요] 사용자가 지목한 노란 박스(채팅 컨테이너) 배경색 강제 지정 */
    /* Streamlit의 모든 채팅 컨테이너를 강제로 밝은 회색으로 바꿉니다. */
    [data-testid="stChatMessageContainerArea"] {
        background-color: #1c2128 !important; 
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
    }
    
    /* 말풍선 가독성 */
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
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    with col1: # 왼쪽: 번호 추가 확인 (직접 문자열 결합)
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=700):
            # 명시적으로 enumerate를 사용하여 인덱스 강제 부여
            for idx, row in data.iterrows():
                # 버튼 텍스트에 번호를 직접 박습니다.
                btn_text = f"{idx + 1}. {row['종목명']} | {row['거래대금(억)']}억"
                if st.button(btn_text, key=f"btn_stock_{idx}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 분석</div>', unsafe_allow_html=True)
        news_text = get_news(stock['종목명'])
        st.markdown(f"""
            <div class="terminal-box">
                <h1 style="color:#00e5ff;">{stock['종목명']}</h1>
                <p style="color:#8b949e;">코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억</p>
                <hr style="border-color:#333;">
                <h4 style="color:#ffffff;">📰 최신 뉴스 요약</h4>
                <div style="color:#ced4da;">{news_text.replace("- ", "• ")}</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        # 채팅창 영역 (CSS에서 지정한 ID와 일치하도록 구성)
        chat_box = st.container(height=600)
        with chat_box:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        if prompt := st.chat_input("질문하세요..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with chat_box:
                with st.chat_message("user"):
                    st.write(prompt)

            if model:
                try:
                    with chat_box:
                        with st.chat_message("assistant"):
                            with st.spinner("AI 분석 중..."):
                                cur = st.session_state.selected_stock
                                news = get_news(cur['종목명'])
                                # AI에게 줄 명령을 더 구체화 (시스템 프롬프트 역할)
                                sys_msg = f"당신은 주식 전문가 'AI 커맨더'입니다. 현재 종목 {cur['종목명']}에 대해 뉴스({news})를 바탕으로 답변하세요."
                                response = model.generate_content(f"{sys_msg}\n\n사용자 질문: {prompt}")
                                st.write(response.text)
                                st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    # 에러 내용을 화면에 더 명확히 표시
                    st.error(f"AI 응답 에러: {str(e)}")
            st.rerun()
else:
    st.error("데이터 파일이 없습니다. scanner.py를 확인하세요.")