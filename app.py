import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. Gemini AI 설정 - NotFound 에러를 방지하는 가장 보수적인 호출 방식
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 모델 이름을 명시적 문자열로 전달 (가장 오류가 적은 방식)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 엔진 초기화 실패: {e}")
        model = None
else:
    st.warning("API 키가 없습니다. Streamlit Secrets를 확인하세요.")
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

# 3. 디자인 CSS (채팅창 전체 배경색 수정 포함)
st.markdown("""
    <style>
    /* 전체 배경 */
    .stApp { background-color: #05070a; }
    
    /* 섹션 헤더 */
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    
    /* 왼쪽/가운데 박스 배경 (#1c2128) */
    .terminal-box, .stock-list-container { 
        background-color: #1c2128; 
        border: 1px solid #30363d; 
        border-radius: 12px; 
        padding: 20px; 
    }
    
    /* [요청] 노란 박스(채팅창 전체 영역) 배경색 수정 (#161b22) */
    /* 웹페이지 배경(#05070a)보다 밝게 하여 영역을 구분합니다. */
    [data-testid="stVerticalBlockBorderWrapper"] > div:has(div[data-testid="stChatMessage"]) {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        padding: 10px !important;
    }
    
    /* 채팅 메시지 말풍선 배경 (#2d333b) */
    [data-testid="stChatMessage"] { background-color: #2d333b !important; border-radius: 10px; margin-bottom: 10px; }
    
    /* 왼쪽 종목 버튼 스타일 */
    .stButton > button { 
        width: 100%; background-color: #1c2128; color: #ffffff; 
        border: 1px solid #30363d; border-radius: 6px; padding: 12px; 
        margin-bottom: 8px; text-align: left;
    }
    .stButton > button:hover { border-color: #00e5ff; background-color: #262c36; }
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

    with col1: # 왼쪽: 종목 리스트 (번호 추가)
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=700):
            for i, row in data.iterrows():
                # i+1 로 번호 표시
                if st.button(f"{i+1}. {row['종목명']} | {row['거래대금(억)']}억", key=f"btn_{row['종목코드']}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2: # 중앙: 뉴스 및 분석
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 분석</div>', unsafe_allow_html=True)
        news_text = get_news(stock['종목명'])
        st.markdown(f"""
            <div class="terminal-box" style="height:700px;">
                <h1 style="color:#00e5ff; margin-bottom:5px;">{stock['종목명']}</h1>
                <p style="color:#8b949e;">코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억</p>
                <hr style="border-color:#333;">
                <h4 style="color:#ffffff;">📰 최신 뉴스 요약</h4>
                <div style="color:#ced4da; font-size:0.95rem; line-height:1.6;">{news_text.replace("- ", "• ")}</div>
            </div>
        """, unsafe_allow_html=True)

    with col3: # 오른쪽: AI 채팅 (영역 배경 구분)
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        
        # 채팅창 영역 배경을 위해 컨테이너 사용
        chat_box = st.container(height=600)
        with chat_box:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        if prompt := st.chat_input("질문하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_box:
                with st.chat_message("user"):
                    st.markdown(prompt)

            if model:
                try:
                    with chat_box:
                        with st.chat_message("assistant"):
                            with st.spinner("분석 중..."):
                                cur = st.session_state.selected_stock
                                news = get_news(cur['종목명'])
                                ctx = f"너는 주식 전문가야. {cur['종목명']} 분석 중. 뉴스: {news}"
                                # model.generate_content 직접 호출
                                response = model.generate_content(f"{ctx}\n질문: {prompt}")
                                res_text = response.text
                                st.markdown(res_text)
                                st.session_state.messages.append({"role": "assistant", "content": res_text})
                except Exception as e:
                    st.error(f"AI 응답 에러: {e}. API 키 권한이나 모델명을 확인하세요.")
            st.rerun()
else:
    st.error("데이터를 찾을 수 없습니다.")