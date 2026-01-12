import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 고대비 터미널 디자인 CSS
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 메인 타이틀 */
    .main-title { 
        color: #00e5ff !important; 
        font-size: 2.2rem; 
        font-weight: 900; 
        margin-bottom: 20px;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
    }
    
    /* ★ 왼쪽 종목 버튼: 길이를 통일하고 정렬 ★ */
    .stButton > button {
        width: 100% !important;
        background-color: #1a1d23 !important;
        color: #ffffff !important;
        border: 1px solid #30363d !important;
        border-radius: 6px;
        padding: 12px 20px;
        text-align: left;
        margin-bottom: 8px;
        transition: 0.2s;
    }
    .stButton > button:hover {
        border-color: #00e5ff !important;
        background-color: #21262d !important;
    }

    /* 채팅 영역 구분선 및 배경 */
    [data-testid="stVerticalBlock"] > div:nth-child(2) {
        border-left: 1px solid #21262d;
        padding-left: 20px;
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

# 상단 타이틀
st.markdown('<h1 class="main-title">🛡️ AI STOCK COMMANDER</h1>', unsafe_allow_html=True)

res = load_data()

if res:
    data, fname = res
    
    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! **AI STOCK COMMANDER**입니다. 왼쪽 리스트에서 종목을 선택하거나, 궁금한 점을 직접 물어보세요."}]

    # --- 화면 분할 (왼쪽 4 : 오른쪽 6) ---
    col1, col2 = st.columns([4, 6])

    # --- 왼쪽: 종목 리스트 영역 ---
    with col1:
        st.write(f"📂 분석 대상 종목 ({len(data)})")
        with st.container(height=750):
            for i, row in data.iterrows():
                mkt = row.get('시장', 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ')
                # 종목 버튼 클릭 시 행동
                if st.button(f"[{mkt}] {row['종목명']} ({row['종목코드']})", key=f"btn_{row['종목코드']}"):
                    # AI가 해당 종목 정보를 채팅창에 브리핑하도록 메시지 추가
                    stock_briefing = f"""
🎯 **{row['종목명']} ({row['종목코드']}) 분석을 시작합니다.**
- **거래대금:** {row['거래대금(억)']}억
- **시장구분:** {mkt}
- **현재상태:** 수급 밀도가 매우 높음 (전수 조사 상위 1% 포착)

현재 이 종목에 대해 궁금한 점(최근 뉴스, 매매 전략 등)이 있으신가요?
                    """
                    st.session_state.messages.append({"role": "assistant", "content": stock_briefing})

    # --- 오른쪽: 자유 LLM 채팅 영역 ---
    with col2:
        st.subheader("💬 AI Commander Chat")
        
        # 채팅 메시지 출력
        chat_container = st.container(height=650)
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 채팅 입력창 (자유 대화 가능)
        if prompt := st.chat_input("질문을 입력하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    # 실제 Gemini 연결 전 임시 응답
                    response = f"데이터를 분석한 결과, '{prompt}'에 대한 전략적 답변을 준비 중입니다. (API 연결 대기 중)"
                    st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

else:
    st.error("데이터를 찾을 수 없습니다.")