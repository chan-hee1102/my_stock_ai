import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. Gemini AI 설정
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 엔진 설정 오류: {e}")
        model = None
else:
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
    return news_data

# 3. 디자인 CSS (채팅창 배경색 강제 지정)
st.markdown("""
    <style>
    /* 웹페이지 전체 배경 */
    .stApp { background-color: #05070a; }
    
    /* 섹션 헤더 디자인 */
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    
    /* 중앙 상세 분석 박스 배경색 (#1c2128) */
    .terminal-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 25px; height: 700px; overflow-y: auto; }
    
    /* 왼쪽 종목 리스트 컨테이너 배경 */
    [data-testid="stVerticalBlockBorderWrapper"] > div:has(div.stButton) {
        background-color: #1c2128;
        border-radius: 12px;
        padding: 10px;
    }

    /* [요청 사항] 오른쪽 채팅창 전체 영역(노란 박스) 배경색을 중앙 박스와 통일 */
    [data-testid="stChatMessageContainerArea"] {
        background-color: #1c2128 !important; 
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        padding: 15px !important;
    }

    /* 채팅 말풍선 색상 (박스 배경보다 조금 더 밝게) */
    [data-testid="stChatMessage"] { background-color: #2d333b !important; }
    
    /* 왼쪽 종목 버튼 스타일 */
    .stButton > button { 
        width: 100%; background-color: #1c2128; color: #ffffff; 
        border: 1px solid #30363d; margin-bottom: 8px; text-align: left; 
    }
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

    with col1: # 왼쪽: 종목 리스트
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=700):
            for i, row in data.iterrows():
                if st.button(f"{row['종목명']} | {row['거래대금(억)']}억", key=f"s_{row['종목코드']}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2: # 중앙: 상세 분석
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 분석</div>', unsafe_allow_html=True)
        news_text = get_news(stock['종목명'])
        st.markdown(f"""
            <div class="terminal-box">
                <h1 style="color:#00e5ff;">{stock['종목명']}</h1>
                <p style="color:#8b949e;">종목코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억</p>
                <hr style="border-color:#333;">
                <h4 style="color:white;">📰 최신 뉴스</h4>
                <div style="color:#ced4da;">{news_text}</div>
            </div>
        """, unsafe_allow_html=True)

    with col3: # 오른쪽: AI 채팅 (배경색 수정 영역)
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        chat_container = st.container(height=600)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        if prompt := st.chat_input("질문하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
            # (AI 대답 로직은 일단 제외하고 배경색 변화부터 확인합니다)
            st.rerun()
else:
    st.error("데이터가 없습니다.")