import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# 1. 페이지 설정 및 레이아웃
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. Gemini AI 엔진 설정
# API 키가 없을 경우를 대비해 안전하게 try-except로 감쌉니다.
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 가장 최신이면서 안정적인 모델명 사용
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다. Streamlit Secrets 설정을 확인하세요.")
        model = None
except Exception as e:
    st.error(f"❌ AI 엔진 초기화 오류: {e}")
    model = None

# 3. 디자인 CSS 설정
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    .terminal-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 25px; height: 700px; overflow-y: auto; }
    
    /* 채팅 메시지 디자인 */
    [data-testid="stChatMessage"] { background-color: #2d333b !important; border-radius: 10px; margin-bottom: 12px; border: 1px solid #444c56; }
    [data-testid="stChatMessage"] p { color: #ffffff !important; font-size: 0.95rem !important; }
    
    /* 종목 리스트 버튼 스타일 */
    .stButton > button { 
        width: 100%; background-color: #161b22; color: #ffffff; 
        border: 1px solid #30363d; border-radius: 6px; padding: 12px; 
        margin-bottom: 8px; text-align: left; transition: 0.3s;
    }
    .stButton > button:hover { border-color: #00e5ff; background-color: #1c2128; }
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드 함수
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None
    # 최신 분석 결과 파일 찾기
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    return df

data = load_data()

if data is not None:
    # 세션 상태 초기화 (현재 선택된 종목 및 채팅 기록)
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{"role": "assistant", "content": "명령을 대기 중입니다. 분석할 종목을 선택하거나 궁금한 점을 말씀해 주십시오."}]

    # 5. 화면 레이아웃 구성 (좌:종목리스트, 중:상세분석, 우:AI채팅)
    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    with col1: # [왼쪽] 종목 리스트
        st.markdown('<div class="section-header">📂 포착된 급등 후보</div>', unsafe_allow_html=True)
        with st.container(height=700):
            for i, row in data.iterrows():
                # 버튼 클릭 시 해당 종목을 세션에 저장
                if st.button(f"{row['종목명']} | {row['거래대금(억)']}억", key=f"stock_{row['종목코드']}"):
                    st.session_state.selected_stock = row.to_dict()

    with col2: # [가운데] 상세 정보
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 정밀 분석</div>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="terminal-box">
                <h1 style="color:#00e5ff; margin-bottom:5px;">{stock['종목명']}</h1>
                <p style="color:#8b949e; font-size:1.1rem;">종목코드: {stock['종목코드']}</p>
                <div style="margin:25px 0; padding:20px; background:#0d1117; border-radius:10px; border:1px solid #30363d;">
                    <p style="color:#ffffff; font-size:1.2rem;">당일 거래대금: <span style="color:#00e5ff;">{stock['거래대금(억)']}억</span></p>
                </div>
                <hr style="border-color:#333; margin:30px 0;">
                <h4 style="color:#ffffff;">💡 AI 가이드라인</h4>
                <p style="color:#e6edf3; line-height:1.8;">
                    현재 거래대금 유입이 확인되었습니다. 우측 AI 커맨더에게 현재 차트 위치나 뉴스 호재 여부를 물어보시면 더욱 정밀한 대응 전략을 제공합니다.
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col3: # [오른쪽] 실시간 AI 채팅
        st.markdown('<div class="section-header">💬 AI Commander Chat</div>', unsafe_allow_html=True)
        
        # 채팅창 인터페이스
        chat_container = st.container(height=600)
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 채팅 입력창
        if prompt := st.chat_input("종목 질문을 입력하세요..."):
            # 유저 메시지 기록
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

            # AI 답변 생성 (모델이 설정되어 있을 때만 실행)
            if model:
                with chat_container:
                    with st.chat_message("assistant"):
                        try:
                            cur = st.session_state.selected_stock
                            # AI에게 줄 배경 정보 (페르소나)
                            context = f"너는 주식 전문가 'AI 커맨더'야. 현재 사용자는 {cur['종목명']}({cur['종목코드']}) 종목을 보고 있어. 거래대금은 {cur['거래대금(억)']}억이야."
                            
                            response = model.generate_content(f"{context}\n\n사용자 질문: {prompt}")
                            ai_answer = response.text
                            st.markdown(ai_answer)
                            st.session_state.chat_history.append({"role": "assistant", "content": ai_answer})
                        except Exception as e:
                            st.error(f"답변 생성 중 오류: {e}")
            
            st.rerun() # 즉시 화면 갱신
else:
    st.error("데이터 파일을 찾을 수 없습니다. scanner.py를 먼저 실행해 주세요.")