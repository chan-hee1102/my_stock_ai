import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. Gemini AI 설정 (NotFound 에러 해결을 위해 모델명 고정)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 가장 안정적인 모델명으로 호출 방식을 통일합니다.
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 엔진 오류: {e}")
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

# 3. 디자인 CSS (요청하신 색상 반영)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    
    /* 중앙/왼쪽 박스 배경색 (#1c2128) */
    .terminal-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 25px; height: 700px; overflow-y: auto; }
    
    /* 왼쪽 종목 버튼 배경색을 중앙 박스와 통일 */
    .stButton > button { 
        width: 100%; background-color: #1c2128; color: #ffffff; 
        border: 1px solid #30363d; margin-bottom: 8px; text-align: left; padding: 12px;
    }
    .stButton > button:hover { border-color: #00e5ff; background-color: #2d333b; }
    
    /* 채팅 메시지 배경색을 더 밝게 수정하여 구분감 확보 (#3a414a) */
    [data-testid="stChatMessage"] { 
        background-color: #3a414a !important; 
        border-radius: 10px; 
        margin-bottom: 12px; 
        border: 1px solid #4e5763;
    }
    [data-testid="stChatMessage"] p { color: #ffffff !important; }
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
    # 세션 관리 (종목 선택 및 채팅 기록 저장)
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "messages" not in st.session_state:
        st.session_state.messages = []

    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    with col1: # 왼쪽: 종목 리스트 (번호 추가 및 배경색 수정)
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=700):
            for i, row in data.iterrows():
                # 순번(i+1)을 제목에 포함
                if st.button(f"{i+1}. {row['종목명']} | {row['거래대금(억)']}억", key=f"btn_{row['종목코드']}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2: # 중앙: 뉴스 및 분석
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 분석</div>', unsafe_allow_html=True)
        news_text = get_news(stock['종목명'])
        st.markdown(f"""
            <div class="terminal-box">
                <h1 style="color:#00e5ff;">{stock['종목명']}</h1>
                <p style="color:#8b949e;">종목코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억</p>
                <hr style="border-color:#333;">
                <h4 style="color:#ffffff;">📰 최신 뉴스 요약</h4>
                <div style="color:#ced4da; font-size:0.95rem; line-height:1.6;">{news_text.replace("- ", "• ")}</div>
            </div>
        """, unsafe_allow_html=True)

    with col3: # 오른쪽: AI 채팅 (배경색 가독성 개선)
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        chat_container = st.container(height=600)
        
        # 기존 대화 내용 표시
        for message in st.session_state.messages:
            with chat_container.chat_message(message["role"]):
                st.markdown(message["content"])

        # 사용자 입력 처리
        if prompt := st.chat_input("질문을 입력하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container.chat_message("user"):
                st.markdown(prompt)

            if model:
                try:
                    with chat_container.chat_message("assistant"):
                        with st.spinner("커맨더 분석 중..."):
                            cur = st.session_state.selected_stock
                            news = get_news(cur['종목명'])
                            context = f"주식 전문가야. {cur['종목명']}({cur['거래대금(억)']}억) 분석 중. 뉴스: {news}"
                            response = model.generate_content(f"{context}\n질문: {prompt}")
                            st.markdown(response.text)
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"AI 답변 생성 실패: {e}")
            st.rerun()
else:
    st.error("데이터를 찾을 수 없습니다.")