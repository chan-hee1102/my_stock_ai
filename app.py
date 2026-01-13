import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# [설정] 페이지 레이아웃 및 제목
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# [학습반영] Gemini AI 설정 (블로그에서 제시한 모델명 규격 적용)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 블로그 해결책: 'models/' 경로를 포함한 정확한 모델명 사용
        model = genai.GenerativeModel('models/gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 초기화 실패: {e}")
        model = None
else:
    st.error("API 키가 없습니다.")
    model = None

# [기능] 뉴스 크롤링
def get_news(stock_name):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={stock_name}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        titles = soup.select(".news_tit")[:3]
        return "\n".join([f"• {t.get_text()}" for t in titles])
    except:
        return "뉴스를 가져오지 못했습니다."

# [디자인] CSS 주입 (중앙 박스와 채팅창 배경색 통일)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    
    /* 공통 박스 디자인 (#1c2128 배경) */
    .content-box { 
        background-color: #1c2128; 
        border: 1px solid #30363d; 
        border-radius: 12px; 
        padding: 20px; 
        height: 700px; 
        overflow-y: auto; 
    }
    
    /* 왼쪽 버튼 디자인 */
    .stButton > button { 
        width: 100%; background-color: #1c2128; color: #ffffff; 
        border: 1px solid #30363d; margin-bottom: 8px; text-align: left; padding: 12px;
    }

    /* 채팅창 전체 영역 배경색 강제 적용 */
    [data-testid="stChatMessageContainer"] {
        background-color: #1c2128 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# [데이터] 로드
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

# 세션 상태 관리
if data is not None:
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 화면 분할
    col1, col2, col3 = st.columns([2, 4, 3])

    with col1: # 왼쪽 리스트 (번호 추가)
        st.markdown('<div class="section-header">📂 포착 종목</div>', unsafe_allow_html=True)
        with st.container(height=700):
            for i, (idx, row) in enumerate(data.iterrows()):
                if st.button(f"{i+1}. {row['종목명']} | {row['거래대금(억)']}억", key=f"s_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2: # 중앙 상세 정보
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 분석</div>', unsafe_allow_html=True)
        news = get_news(stock['종목명'])
        st.markdown(f"""
            <div class="content-box">
                <h1 style="color:#00e5ff;">{stock['종목명']}</h1>
                <p style="color:#8b949e;">코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억</p>
                <hr style="border-color:#333;">
                <h4 style="color:white;">📰 최신 뉴스</h4>
                <div style="color:#ced4da;">{news}</div>
            </div>
        """, unsafe_allow_html=True)

    with col3: # 오른쪽 AI 채팅
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        chat_box = st.container(height=600)
        with chat_box:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        if prompt := st.chat_input("분석 질문을 입력하세요"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_box:
                with st.chat_message("user"):
                    st.markdown(prompt)
            
            if model:
                try:
                    with chat_box:
                        with st.chat_message("assistant"):
                            cur = st.session_state.selected_stock
                            context = f"당신은 주식 전문가입니다. {cur['종목명']} 종목을 분석하세요."
                            response = model.generate_content(f"{context}\n질문: {prompt}")
                            st.markdown(response.text)
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"에러 발생: {e}")
            st.rerun()
else:
    st.error("데이터 파일이 없습니다.")