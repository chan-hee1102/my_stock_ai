import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 고도화된 터미널 CSS (배경 채우기 및 밀림 방지)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 공통 스타일: 선명한 흰색 소제목 */
    .section-header {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        margin-bottom: 12px !important;
        padding-left: 5px;
    }

    /* ★ 1, 2, 3번 모든 영역에 회색 박스 배경 적용 ★ */
    .terminal-box {
        background-color: #161b22 !important;
        border: 1px solid #21262d;
        border-radius: 12px;
        padding: 15px;
        height: 720px; /* 전체 높이 고정 */
        overflow: hidden; /* 내부 컨테이너로 스크롤 제어 */
        display: flex;
        flex-direction: column;
    }

    /* 종목 버튼 디자인 (회색 배경) */
    .stButton > button {
        width: 100% !important;
        background-color: #323940 !important;
        color: #ffffff !important;
        border: 1px solid #444c56 !important;
        border-radius: 6px;
        padding: 12px;
        text-align: left;
        margin-bottom: 8px;
        font-size: 0.9rem;
    }
    .stButton > button:hover {
        border-color: #00e5ff !important;
        background-color: #444c56 !important;
    }

    /* 채팅 메시지 박스 */
    [data-testid="stChatMessage"] {
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        margin-bottom: 10px;
    }

    /* 날짜 배지 및 타이틀 */
    .date-badge {
        background: rgba(0, 229, 255, 0.1);
        color: #00e5ff;
        padding: 4px 12px;
        border: 1px solid #00e5ff;
        border-radius: 50px;
        font-size: 0.8rem;
        font-weight: 800;
        margin-bottom: 10px;
        display: inline-block;
    }
    .main-title { 
        color: #00e5ff !important; 
        font-size: 2.2rem; 
        font-weight: 900; 
        margin-bottom: 25px;
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

    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # --- 레이아웃 비율 조정 (1번을 줄이고 2번 분석을 강조) ---
    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    # [1번 영역] 종목 리스트 (회색 박스 내부)
    with col1:
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=700, border=True): # border=True가 회색 배경 역할을 함
            for i, row in data.iterrows():
                mkt = row.get('시장', 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ')
                if st.button(f"[{mkt}] {row['종목명']}", key=f"list_{row['종목코드']}"):
                    st.session_state.selected_stock = row.to_dict()

    # [2번 영역] 실시간 종목 분석 (중앙 강조)
    with col2:
        st.markdown('<div class="section-header">📊 실시간 종목 분석</div>', unsafe_allow_html=True)
        stock = st.session_state.selected_stock
        # HTML로 박스 디자인 구현
        st.markdown(f"""
            <div style="background-color: #161b22; border: 1px solid #21262d; border-radius: 12px; padding: 25px; height: 700px;">
                <h2 style="color:#00e5ff; margin-top:0;">{stock['종목명']} <span style="font-size:1rem; color:#8b949e;">({stock['종목코드']})</span></h2>
                <hr style="border-color:#30363d; margin: 20px 0;">
                <p style="color:#ffffff; font-size:1.1rem;"><b>📈 주요 수급 지표</b></p>
                <p style="color:#e6edf3; font-size:1rem;">• 당일 거래대금: <span style="color:#00e5ff;">{stock['거래대금(억)']}억</span></p>
                <p style="color:#e6edf3; font-size:1rem;">• 시장 구분: {mkt}</p>
                <br>
                <div style="background:#0d1117; padding:20px; border-left:4px solid #00e5ff; border-radius:8px;">
                    <p style="color:#ffffff; margin-bottom:5px;"><b>AI COMMANDER ANALYSIS</b></p>
                    <p style="color:#8b949e; line-height:1.6;">
                    해당 종목은 현재 전수 조사 시스템에서 수급 밀집도 상위 1% 이내에 포착되었습니다. 
                    단기적인 과열 상태일 수 있으나, 거래대금의 질이 우수하여 추가 상승 모멘텀이 유효해 보입니다.
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # [3번 영역] AI 채팅 (오른쪽 회색 박스)
    with col3:
        st.markdown('<div class="section-header">💬 AI Commander Chat</div>', unsafe_allow_html=True)
        with st.container(height=640, border=True):
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        if prompt := st.chat_input("종목에 대해 질문하세요..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.session_state.chat_history.append({"role": "assistant", "content": f"'{stock['종목명']}'에 대한 분석을 진행 중입니다."})
            st.rerun()

else:
    st.error("데이터를 찾을 수 없습니다.")