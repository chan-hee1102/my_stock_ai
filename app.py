import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 스타일 및 가독성 긴급 수리 CSS
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 날짜 배지 복구 */
    .date-badge {
        background: rgba(0, 229, 255, 0.1);
        color: #00d4ff;
        padding: 6px 16px;
        border: 1.5px solid #00d4ff;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 800;
        display: inline-block;
        margin-bottom: 10px;
    }

    /* 메인 타이틀: 선명한 하늘색 */
    .main-title { 
        color: #00e5ff !important; 
        font-size: 2.8rem; 
        font-weight: 900; 
        margin-bottom: 20px;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
    }
    
    /* ★ 왼쪽 종목 버튼 수리 ★ 
       길이를 중앙까지 늘리고 모든 버튼의 시작 위치를 일치시킴 */
    .stButton > button {
        width: 100% !important;
        min-width: 450px; /* 길이를 더 늘림 */
        background-color: #1a1d23 !important;
        color: #ffffff !important;
        border: 1px solid #30363d !important;
        border-radius: 6px;
        padding: 14px 22px;
        text-align: left;
        display: block;
        margin: 0 auto 10px 0; /* 왼쪽 정렬 강제 */
        transition: 0.2s;
    }
    .stButton > button:hover {
        border-color: #00e5ff !important;
        background-color: #21262d !important;
    }

    /* ★ 채팅창 가독성 개선 ★ */
    div[data-testid="stChatMessage"] {
        background-color: #1e2329 !important; /* 밝은 회색으로 변경 */
        border-radius: 10px;
        margin-bottom: 10px;
    }
    div[data-testid="stChatMessage"] p {
        color: #ffffff !important; /* 글씨 선명하게 */
        font-size: 1rem;
    }

    /* 채팅 입력창 위치 조절 (너무 아래에 있지 않도록 상단 여백 조절) */
    .stChatInput {
        padding-bottom: 50px !important;
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

    # 상단 날짜 및 타이틀
    st.markdown(f'<div class="date-badge">SYSTEM STATUS: ONLINE | {display_date}</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="main-title">🛡️ AI STOCK COMMANDER</h1>', unsafe_allow_html=True)

    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "분석 준비가 완료되었습니다. 왼쪽에서 종목을 선택하세요."}]

    # --- 화면 분할 (왼쪽 5 : 오른쪽 5로 조정하여 버튼 공간 확보) ---
    col1, col2 = st.columns([5, 5])

    # --- 왼쪽: 종목 리스트 ---
    with col1:
        st.write(f"📂 포착된 종목 ({len(data)})")
        # 높이를 지정하여 내부 스크롤 생성 (버튼 정렬 유지)
        with st.container(height=700):
            for i, row in data.iterrows():
                mkt = row.get('시장', 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ')
                btn_label = f"[{mkt}] {row['종목명']} ({row['종목코드']}) | {row['거래대금(억)']}억"
                
                if st.button(btn_label, key=f"btn_{row['종목코드']}"):
                    briefing = f"🎯 **{row['종목명']}** 분석 리포트:\n\n거래대금 {row['거래대금(억)']}억으로 수급이 집중되었습니다. 현재 AI가 시장 테마와의 연관성을 분석 중입니다."
                    st.session_state.messages.append({"role": "assistant", "content": briefing})

    # --- 오른쪽: AI 채팅 ---
    with col2:
        st.markdown("### 💬 Live AI Chat")
        chat_box = st.container(height=600)
        with chat_container := chat_box:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 입력창
        if prompt := st.chat_input("종목 전략에 대해 질문하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    st.markdown("데이터 분석을 시작합니다. (곧 Gemini API가 연결됩니다)")

else:
    st.error("데이터를 찾을 수 없습니다.")