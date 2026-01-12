import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 고대비 & 시인성 개선 CSS
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 날짜 배지 */
    .date-badge {
        background: rgba(0, 229, 255, 0.1);
        color: #00e5ff;
        padding: 5px 15px;
        border: 1px solid #00e5ff;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 800;
        display: inline-block;
        margin-bottom: 10px;
    }

    /* 메인 타이틀 */
    .main-title { 
        color: #00e5ff !important; 
        font-size: 2.5rem; 
        font-weight: 900; 
        margin-bottom: 20px;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
    }
    
    /* ★ 노란 동그라미 영역: 소제목들을 선명한 흰색으로 ★ */
    .section-header {
        color: #ffffff !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        margin-bottom: 15px !important;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* ★ 왼쪽 종목 버튼: 배경을 회색으로 변경 ★ */
    .stButton > button {
        width: 100% !important;
        max-width: 550px; 
        background-color: #323940 !important; /* 차분한 회색 배경 */
        color: #ffffff !important; /* 글자는 흰색 유지 */
        border: 1px solid #444c56 !important;
        border-radius: 6px;
        padding: 14px 20px;
        text-align: left;
        margin-bottom: 8px;
        display: flex;
        justify-content: flex-start;
        transition: 0.2s;
    }
    .stButton > button:hover {
        border-color: #00e5ff !important;
        background-color: #444c56 !important; /* 호버 시 약간 밝아짐 */
    }

    /* 오른쪽 채팅 영역 배경 */
    [data-testid="stVerticalBlock"] > div:nth-child(2) [data-testid="stVerticalBlock"] {
        background-color: #161b22; 
        border-radius: 15px;
        padding: 20px;
        border: 1px solid #21262d;
    }
    
    /* 채팅 메시지 가독성 */
    [data-testid="stChatMessage"] {
        background-color: #21262d !important; 
        border: 1px solid #30363d !important;
    }
    [data-testid="stChatMessage"] p {
        color: #e6edf3 !important;
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

    st.markdown(f'<div class="date-badge">MARKET SCAN DATA: {display_date}</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="main-title">🛡️ AI STOCK COMMANDER</h1>', unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "명령을 대기 중입니다. 분석할 종목을 선택하세요."}]

    col1, col2 = st.columns([5, 5])

    with col1:
        # 노란 동그라미 부분 흰색 처리
        st.markdown('<div class="section-header">📂 포착된 종목 (' + str(len(data)) + ')</div>', unsafe_allow_html=True)
        with st.container(height=650):
            for i, row in data.iterrows():
                mkt = row.get('시장', 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ')
                label = f"[{mkt}] {row['종목명']} ({row['종목코드']}) | {row['거래대금(억)']}억"
                if st.button(label, key=f"btn_{row['종목코드']}"):
                    st.session_state.messages.append({"role": "assistant", "content": f"🎯 **{row['종목명']}** 분석을 시작합니다. 궁금한 점을 물어보세요!"})

    with col2:
        # 노란 동그라미 부분 흰색 처리
        st.markdown('<div class="section-header">💬 AI Commander Chat</div>', unsafe_allow_html=True)
        chat_box = st.container(height=580)
        with chat_box:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if prompt := st.chat_input("종목에 대해 질문하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_box:
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    st.markdown("분석 데이터를 가져오는 중입니다.")

else:
    st.error("데이터를 찾을 수 없습니다.")