import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 디자인 정밀 수정 CSS (채팅 가독성 최적화)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 소제목 (흰색) */
    .section-header {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        margin-bottom: 12px !important;
    }

    /* ★ 1, 2, 3번 영역 공통 회색 박스 ★ */
    /* 배경색을 웹 배경보다 밝은 #1c2128로 설정하여 구분감 부여 */
    .terminal-box {
        background-color: #1c2128 !important; 
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        height: 700px;
    }

    /* ★ 채팅 메시지 가독성 UP ★ */
    [data-testid="stChatMessage"] {
        background-color: #2d333b !important; /* 메시지 배경을 더 밝게 */
        border: 1px solid #444c56 !important;
        border-radius: 10px;
        margin-bottom: 12px;
    }
    
    /* 채팅 글자색을 완전 흰색으로 고정 */
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span {
        color: #ffffff !important;
        font-size: 1rem !important;
        line-height: 1.6;
    }

    /* 종목 버튼 디자인 (회색) */
    .stButton > button {
        width: 100% !important;
        background-color: #323940 !important;
        color: #ffffff !important;
        border: 1px solid #444c56 !important;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 8px;
    }
    .stButton > button:hover {
        border-color: #00e5ff !important;
        background-color: #444c56 !important;
    }

    /* 입력창 배경 및 글자색 */
    .stChatInputContainer textarea {
        color: #ffffff !important;
        background-color: #0d1117 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    return df, latest_file

res = load_data()

if res:
    data, fname = res
    raw_date = fname.split('_')[-1].replace('.csv', '')
    display_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

    st.markdown(f'<div style="color:#00e5ff; font-weight:800; margin-bottom:10px;">MARKET SCAN DATA: {display_date}</div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#00e5ff; font-size:2.2rem; font-weight:900;">🛡️ AI STOCK COMMANDER</h1>', unsafe_allow_html=True)

    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 비율 조정 (1번 줄임, 2번 강조)
    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    with col1:
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        # st.container의 높이를 조정하여 밀림 방지
        with st.container(height=680):
            for i, row in data.iterrows():
                mkt = 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ'
                if st.button(f"[{mkt}] {row['종목명']}", key=f"list_{row['종목코드']}"):
                    st.session_state.selected_stock = row.to_dict()

    with col2:
        st.markdown('<div class="section-header">📊 실시간 종목 분석</div>', unsafe_allow_html=True)
        stock = st.session_state.selected_stock
        st.markdown(f"""
            <div class="terminal-box">
                <h2 style="color:#00e5ff; margin-top:0;">{stock['종목명']} ({stock['종목코드']})</h2>
                <hr style="border-color:#30363d;">
                <p style="color:#ffffff;">• 거래대금: <span style="color:#00e5ff;">{stock['거래대금(억)']}억</span></p>
                <div style="background:#0d1117; padding:15px; border-left:4px solid #00e5ff; border-radius:5px; margin-top:20px;">
                    <p style="color:#ffffff;"><b>AI 분석 의견:</b><br>
                    수급이 매우 강합니다. 현재 구간에서 지지 여부를 확인하세요.</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="section-header">💬 AI Commander Chat</div>', unsafe_allow_html=True)
        # 채팅창에 명확한 회색 박스 적용
        with st.container(height=620):
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        if prompt := st.chat_input("종목 질문을 입력하세요..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.session_state.chat_history.append({"role": "assistant", "content": "Gemini AI가 분석 중입니다."})
            st.rerun()

else:
    st.error("데이터 로드 실패")