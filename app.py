import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# 1. 페이지 설정 (레이아웃)
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. Gemini AI 설정 (블로그 해결책 반영)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 모델명을 명확히 지정하여 404 에러를 방지합니다.
        model = genai.GenerativeModel('models/gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 초기화 실패: {e}")
        model = None
else:
    st.error("Secrets에 API 키가 설정되지 않았습니다.")
    model = None

# 3. 데이터 로드 로직
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

# --- [정석] 세션 상태 관리 (답변 유지 및 선택 종목 저장) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# 4. 디자인 CSS (다크 테마 유지 및 채팅 영역 배경 고정)
st.markdown("""
    <style>
    /* 전체 배경색 */
    .stApp { background-color: #05070a; }
    
    /* 섹션 헤더 스타일 */
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    
    /* 중앙 상세 분석 박스 */
    .content-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 25px; height: 600px; overflow-y: auto; color: white; }
    
    /* 왼쪽 리스트 버튼 스타일 */
    .stButton > button { 
        width: 100%; background-color: #1c2128; color: #ffffff; 
        border: 1px solid #30363d; margin-bottom: 8px; text-align: left; padding: 10px;
    }
    
    /* 채팅 영역 배경색 및 테두리 (회색 상자 일체화) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stChatMessage"]) {
        background-color: #1c2128 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        padding: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 5. 메인 화면 구성
if data is not None:
    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    with col1: # 왼쪽: 포착된 종목 리스트
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=650):
            for i, (idx, row) in enumerate(data.iterrows()):
                # [수정] i+1을 사용하여 순번이 확실히 보이게 함
                label = f"{i+1}. {row['종목명']} | {row['거래대금(억)']}억"
                if st.button(label, key=f"btn_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2: # 중앙: 종목 상세 분석
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 분석</div>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="content-box">
                <h1 style="color:#00e5ff; margin-top:0;">{stock['종목명']}</h1>
                <p style="color:#8b949e;">코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억</p>
                <hr style="border-color:#333;">
                <p>현재 차트 위치와 수급 상황을 기반으로 분석 중입니다.<br>구체적인 대응 전략은 AI에게 질문해 보세요.</p>
            </div>
        """, unsafe_allow_html=True)

    with col3: # 오른쪽: AI Commander 채팅
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        
        # 채팅 메시지가 표시될 박스
        chat_placeholder = st.container(height=550)
        
        # [정석] 세션에 저장된 기존 대화를 루프를 돌며 모두 출력
        with chat_placeholder:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        # 사용자 입력창
        if prompt := st.chat_input("종목에 대해 궁금한 점을 입력하세요"):
            # 1. 사용자 질문 세션에 저장
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # 2. AI 응답 생성 로직
            if model:
                try:
                    # 현재 선택된 종목 정보를 프롬프트에 포함
                    cur_stock = st.session_state.selected_stock
                    context = f"당신은 주식 전문가입니다. 현재 분석 중인 종목은 '{cur_stock['종목명']}'입니다."
                    response = model.generate_content(f"{context}\n\n질문: {prompt}")
                    
                    # 3. AI 답변을 세션에 저장 (이래야 리런 후에도 유지됨)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.session_state.messages.append({"role": "assistant", "content": f"오류 발생: {e}"})
            
            # 화면 갱신을 위해 리런
            st.rerun()
else:
    st.error("데이터가 로드되지 않았습니다.")