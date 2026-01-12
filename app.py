import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 통합 CSS (디자인 복구 및 가독성 최적화)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 날짜 배지 디자인 */
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
    
    /* ★ 왼쪽 종목 버튼: 모든 버튼의 길이와 시작점을 통일 ★ */
    div[data-testid="column"] > div:first-child button {
        width: 100% !important;
        background-color: #1a1d23 !important;
        color: #ffffff !important;
        border: 1px solid #30363d !important;
        border-radius: 6px;
        padding: 14px 20px;
        text-align: left;
        display: flex;
        justify-content: flex-start;
        margin-bottom: 10px;
    }
    
    div[data-testid="column"] > div:first-child button:hover {
        border-color: #00e5ff !important;
        background-color: #21262d !important;
    }

    /* ★ 채팅창 가독성: 배경 회색, 글자 흰색 ★ */
    [data-testid="stChatMessage"] {
        background-color: #262730 !important; /* 차분한 회색 */
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    [data-testid="stChatMessage"] p {
        color: #ffffff !important;
        font-size: 1rem;
        line-height: 1.6;
    }

    /* 채팅 입력창 위치 상향 조정 */
    .stChatInput {
        bottom: 30px !important;
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

    # 1. 상단 날짜 및 제목
    st.markdown(f'<div class="date-badge">MARKET SCAN DATA: {display_date}</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="main-title">🛡️ AI STOCK COMMANDER</h1>', unsafe_allow_html=True)

    # 2. 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "명령을 대기 중입니다. 분석할 종목을 선택하세요."}]

    # --- 3. 화면 분할 (5:5) ---
    col1, col2 = st.columns([5, 5])

    # 왼쪽 종목 리스트
    with col1:
        st.write(f"📂 포착된 종목 ({len(data)})")
        with st.container(height=650):
            for i, row in data.iterrows():
                mkt = row.get('시장', 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ')
                # 버튼 레이블 통일
                label = f"[{mkt}] {row['종목명']} ({row['종목코드']}) | {row['거래대금(억)']}억"
                if st.button(label, key=f"btn_{row['종목코드']}"):
                    brief = f"🎯 **{row['종목명']}** 종목 분석 모드를 활성화합니다.\n- 수급 집중도: {row['거래대금(억)']}억\n- 전략: AI가 실시간 모멘텀을 추적 중입니다."
                    st.session_state.messages.append({"role": "assistant", "content": brief})

    # 오른쪽 LLM 채팅창
    with col2:
        st.markdown("### 💬 AI Commander Chat")
        # 오류가 났던 부분을 안전한 방식으로 수정
        chat_box = st.container(height=580)
        with chat_box:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 채팅 입력
        if prompt := st.chat_input("질문을 입력하세요 (예: 이 종목 호재 뭐야?)"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_box:
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    st.markdown(f"'{prompt}'에 대한 깊이 있는 분석을 Gemini API를 통해 요청하겠습니다.")

else:
    st.error("데이터 파일을 로드할 수 없습니다.")