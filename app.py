import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 디자인 정밀 조정 CSS
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
        font-size: 2.2rem; 
        font-weight: 900; 
        margin-bottom: 20px;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
    }
    
    /* 소제목 (흰색으로 강조) */
    .section-header {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        margin-bottom: 15px !important;
    }

    /* 1번 영역: 종목 버튼 (회색 배경) */
    .stButton > button {
        width: 100% !important;
        background-color: #323940 !important;
        color: #ffffff !important;
        border: 1px solid #444c56 !important;
        border-radius: 6px;
        padding: 12px 15px;
        text-align: left;
        margin-bottom: 8px;
    }
    .stButton > button:hover {
        border-color: #00e5ff !important;
        background-color: #444c56 !important;
    }

    /* 2번 & 3번 영역: 회색 박스 배경 */
    .content-box {
        background-color: #161b22;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #21262d;
        height: 650px;
        overflow-y: auto;
    }

    /* 채팅 메시지 가독성 */
    [data-testid="stChatMessage"] {
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        margin-bottom: 10px;
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

    # 상단 헤더
    st.markdown(f'<div class="date-badge">MARKET SCAN DATA: {display_date}</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="main-title">🛡️ AI STOCK COMMANDER</h1>', unsafe_allow_html=True)

    # 세션 관리
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # --- 3분할 레이아웃 (비율: 2.5 : 4 : 3.5) ---
    col1, col2, col3 = st.columns([2.5, 4, 3.5])

    # [1번 영역] 종목 리스트
    with col1:
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=650):
            for i, row in data.iterrows():
                mkt = row.get('시장', 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ')
                if st.button(f"[{mkt}] {row['종목명']}", key=f"list_{row['종목코드']}"):
                    st.session_state.selected_stock = row.to_dict()

    # [2번 영역] 종목 분석 결과 (중앙)
    with col2:
        st.markdown('<div class="section-header">📊 실시간 종목 분석</div>', unsafe_allow_html=True)
        stock = st.session_state.selected_stock
        st.markdown(f"""
            <div class="content-box">
                <h3 style="color:#00e5ff;">{stock['종목명']} ({stock['종목코드']})</h3>
                <hr style="border-color:#30363d;">
                <p style="color:#8b949e;">📍 <b>주요 지표</b></p>
                <ul>
                    <li style="color:white;">거래대금: {stock['거래대금(억)']}억</li>
                    <li style="color:white;">시장구분: {'KOSPI' if str(stock['종목코드'])[0] in ['0', '1'] else 'KOSDAQ'}</li>
                </ul>
                <br>
                <div style="background:#0d1117; padding:15px; border-left:4px solid #00e5ff; border-radius:5px;">
                    <p style="color:#ffffff;"><b>AI COMMANDER 의견:</b><br>
                    해당 종목은 현재 거래대금이 실시간 상위권에 랭크되어 있으며, 
                    단기 수급 유입이 강하게 발생하고 있습니다. 추가적인 테마 형성을 확인하세요.</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # [3번 영역] AI 채팅 (오른쪽)
    with col3:
        st.markdown('<div class="section-header">💬 AI Commander Chat</div>', unsafe_allow_html=True)
        with st.container(height=580):
            # 자유 채팅 표시
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if prompt := st.chat_input("질문을 입력하세요..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            # (여기에 나중에 Gemini API 연결 예정)
            st.session_state.chat_history.append({"role": "assistant", "content": "데이터 분석 중입니다."})
            st.rerun()

else:
    st.error("데이터 로드 실패")