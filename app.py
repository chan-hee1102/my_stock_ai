import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. Gemini AI 엔진 연결 (Secrets에서 키 가져오기)
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 대화형 모델 설정
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.error("API 키를 찾을 수 없습니다. Streamlit Cloud의 Settings나 secrets.toml을 확인하세요.")
except Exception as e:
    st.error(f"AI 연결 중 오류 발생: {e}")

# --- CSS 디자인 (가독성 개선 버전) ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 12px; }
    .terminal-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; height: 700px; overflow-y: auto; }
    
    /* 채팅 메시지 스타일 */
    [data-testid="stChatMessage"] { background-color: #2d333b !important; border-radius: 10px; margin-bottom: 10px; }
    [data-testid="stChatMessage"] p { color: #ffffff !important; font-size: 1rem !important; }
    
    /* 종목 버튼 */
    .stButton > button { width: 100%; background-color: #323940; color: #ffffff; border: 1px solid #444c56; border-radius: 6px; padding: 10px; margin-bottom: 5px; text-align: left; }
    .stButton > button:hover { border-color: #00e5ff; }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 함수
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
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "chat_history" not in st.session_state:
        # 첫 인사말 추가
        st.session_state.chat_history = [{"role": "assistant", "content": "명령을 대기 중입니다. 분석할 종목을 선택하거나 궁금한 점을 물어보세요."}]

    # 4. 레이아웃 (2.2 : 4.5 : 3.3)
    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    with col1:
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=680):
            for i, row in data.iterrows():
                mkt = 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ'
                if st.button(f"[{mkt}] {row['종목명']} | {row['거래대금(억)']}억", key=f"list_{row['종목코드']}"):
                    st.session_state.selected_stock = row.to_dict()

    with col2:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 실시간 분석</div>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="terminal-box">
                <h2 style="color:#00e5ff; margin-top:0;">{stock['종목명']} <span style="font-size:1rem; color:#8b949e;">({stock['종목코드']})</span></h2>
                <p style="color:#ffffff;">• 당일 거래대금: <span style="color:#00e5ff;">{stock['거래대금(억)']}억</span></p>
                <hr style="border-color:#333;">
                <div style="background:#0d1117; padding:15px; border-left:4px solid #00e5ff; border-radius:5px;">
                    <p style="color:#ffffff;"><b>기본 분석 결과:</b><br>현재 거래량이 급증하며 수급 상위에 포착되었습니다. 추가 재무/뉴스 분석이 필요합니다.</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="section-header">💬 AI Commander Chat</div>', unsafe_allow_html=True)
        with st.container(height=620):
            # 대화 기록 표시
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        # 5. 진짜 채팅 입력 로직
        if prompt := st.chat_input("종목 질문을 입력하세요..."):
            # 사용자 메시지 표시
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            # AI 답변 생성
            try:
                stock = st.session_state.selected_stock
                # AI에게 '너는 누구고 무엇을 보고 있는지' 배경 설명(페르소나) 부여
                context = f"""
                너는 주식 전문가 'AI 커맨더'야. 
                사용자는 현재 {stock['종목명']}(코드:{stock['종목코드']}) 종목을 보고 있어. 
                오늘 거래대금은 {stock['거래대금(억)']}억이야. 
                이 정보를 바탕으로 사용자에게 친절하고 전문적으로 답변해줘.
                """
                
                response = model.generate_content(f"{context}\n\n사용자 질문: {prompt}")
                ai_answer = response.text
                
                st.session_state.chat_history.append({"role": "assistant", "content": ai_answer})
            except Exception as e:
                st.session_state.chat_history.append({"role": "assistant", "content": f"오류 발생: {e}"})
            
            st.rerun() # 답변 즉시 반영을 위해 페이지 새로고침

else:
    st.error("데이터 로드 실패")