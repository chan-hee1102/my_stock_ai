import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. Gemini AI 설정 (가장 안전한 초기화 방식)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 모델 객체를 생성할 때 에러가 나지 않도록 예외 처리 강화
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        model = None
else:
    model = None

# 3. 디자인 CSS (채팅창 배경을 강제로 꽉 채우는 설정)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    
    /* 중앙 상세 분석 박스 */
    .terminal-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 25px; height: 700px; }
    
    /* 왼쪽 버튼 스타일 */
    .stButton > button { 
        width: 100%; background-color: #1c2128; color: #ffffff; 
        border: 1px solid #30363d; margin-bottom: 8px; text-align: left; padding: 12px;
    }
    
    /* [핵심] 노란 박스 영역을 통째로 회색 상자로 만드는 설정 */
    /* Streamlit 컨테이너 자체에 배경색과 높이를 강제로 부여합니다. */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stChatMessage"]) {
        background-color: #1c2128 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        padding: 20px !important;
        min-height: 600px !important;
    }
    
    /* 채팅 말풍선 (구분을 위해 더 밝게) */
    [data-testid="stChatMessage"] { 
        background-color: #2d333b !important; 
        border: 1px solid #444c56 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 4. 데이터 로드 함수
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

if data is not None:
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "messages" not in st.session_state:
        st.session_state.messages = []

    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    with col1: # 왼쪽: 종목 리스트 (번호 추가 완료)
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=700):
            # enumerate를 써서 1부터 번호를 매깁니다.
            for i, (idx, row) in enumerate(data.iterrows()):
                label = f"{i+1}. {row['종목명']} | {row['거래대금(억)']}억"
                if st.button(label, key=f"stock_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2: # 중앙: 상세 분석
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 분석</div>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="terminal-box">
                <h1 style="color:#00e5ff; margin-top:0;">{stock['종목명']}</h1>
                <p style="color:#8b949e;">코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억</p>
                <hr style="border-color:#333;">
                <p style="color:#ced4da;">현재 차트 위치와 수급 상황을 기반으로 분석 중입니다.<br>구체적인 대응 전략은 AI에게 물어보세요.</p>
            </div>
        """, unsafe_allow_html=True)

    with col3: # 오른쪽: AI 채팅 (배경색 꽉 채우기)
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        
        # 채팅 메시지 표시 영역
        chat_placeholder = st.container(height=550)
        with chat_placeholder:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        # 질문 입력 및 AI 로직
        if prompt := st.chat_input("질문을 입력하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            if model:
                try:
                    # AI 응답 생성
                    cur = st.session_state.selected_stock
                    context = f"당신은 주식 전문가입니다. {cur['종목명']}(코드:{cur['종목코드']}) 종목에 대해 분석해주세요."
                    response = model.generate_content(f"{context}\n\n질문: {prompt}")
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.session_state.messages.append({"role": "assistant", "content": f"죄송합니다. 오류가 발생했습니다: {str(e)}"})
            
            st.rerun()
else:
    st.error("데이터가 없습니다.")