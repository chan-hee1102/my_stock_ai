import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. [블로그 학습 반영] Gemini AI 설정
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 모델명을 명확히 지정하여 404 방지
        model = genai.GenerativeModel('models/gemini-1.5-flash')
    except Exception as e:
        model = None
else:
    model = None

# 3. 디자인 CSS 복구 (다시 검은색 테마로)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    .content-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; height: 600px; overflow-y: auto; color: white; }
    .stButton > button { width: 100%; background-color: #1c2128; color: #ffffff; border: 1px solid #30363d; margin-bottom: 8px; text-align: left; }
    /* 채팅 영역 배경색 고정 */
    [data-testid="stChatMessageContainer"] { background-color: #1c2128 !important; border-radius: 10px; }
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

# 5. 세션 상태 (답변 저장 및 유지)
if "messages" not in st.session_state:
    st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# 6. 화면 구성
if data is not None:
    col1, col2, col3 = st.columns([2, 4, 3])

    with col1: # 왼쪽: 종목 리스트 (번호 추가)
        st.markdown('<div class="section-header">📂 포착 종목</div>', unsafe_allow_html=True)
        with st.container(height=650):
            for i, (idx, row) in enumerate(data.iterrows()):
                if st.button(f"{i+1}. {row['종목명']} | {row['거래대금(억)']}억", key=f"s_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2: # 중앙: 상세 분석
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 분석</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="content-box">
            <h1 style="color:#00e5ff;">{stock['종목명']}</h1>
            <p>코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억</p>
            <hr>
            <p>이 종목의 상세 분석 데이터는 AI Commander에게 질문하여 확인하세요.</p>
        </div>""", unsafe_allow_html=True)

    with col3: # 오른쪽: AI 채팅 (답변 고정 로직)
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        chat_container = st.container(height=550)
        
        # 저장된 메시지 출력 (이게 없으면 답장이 사라짐)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        if prompt := st.chat_input("종목에 대해 질문하세요"):
            # 사용자 메시지 저장 및 표시
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
            
            # AI 답변 생성
            if model:
                try:
                    with chat_container:
                        with st.chat_message("assistant"):
                            response = model.generate_content(f"{stock['종목명']} 분석 질문: {prompt}")
                            st.markdown(response.text)
                            # 답변을 세션에 즉시 저장
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"AI 오류: {e}")
            st.rerun() # 전체 상태 반영을 위해 마지막에 리런
else:
    st.error("데이터가 없습니다.")