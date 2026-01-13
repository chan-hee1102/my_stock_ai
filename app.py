import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. Gemini AI 설정 (블로그 및 Google 가이드 반영)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 404 에러 방지를 위한 정확한 모델명 지정
        model = genai.GenerativeModel('models/gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 초기화 실패: {e}")
        model = None
else:
    st.error("Secrets에 API 키가 없습니다.")
    model = None

# 3. 강력한 디자인 CSS (검은색 테마 및 노란 박스 영역 배경색 수정)
st.markdown("""
    <style>
    /* 전체 배경색 */
    .stApp { background-color: #05070a; }
    
    /* 섹션 헤더 */
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    
    /* 중앙 상세 분석 박스 */
    .terminal-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 25px; height: 700px; overflow-y: auto; color: white; }
    
    /* 왼쪽 종목 버튼 스타일 */
    .stButton > button { 
        width: 100%; background-color: #1c2128; color: #ffffff; 
        border: 1px solid #30363d; margin-bottom: 8px; text-align: left; padding: 12px;
    }
    
    /* [요청] 오른쪽 채팅 전체 영역(노란 박스 부분) 배경색 강제 지정 */
    [data-testid="stChatMessageContainerArea"] {
        background-color: #1c2128 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        padding: 10px !important;
    }

    /* 채팅 말풍선 색상 구분 */
    [data-testid="stChatMessage"] { background-color: #2d333b !important; border-radius: 10px; }
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

# 5. 세션 상태 관리 (답변 사라짐 방지 핵심)
if "messages" not in st.session_state:
    st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# 6. 화면 구성
if data is not None:
    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    with col1: # 왼쪽: 종목 리스트 (번호 추가)
        st.markdown('<div class="section-header">📂 포착 종목</div>', unsafe_allow_html=True)
        with st.container(height=700):
            for i, (idx, row) in enumerate(data.iterrows()):
                if st.button(f"{i+1}. {row['종목명']} | {row['거래대금(억)']}억", key=f"s_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2: # 중앙: 상세 분석 창
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 분석</div>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="terminal-box">
                <h1 style="color:#00e5ff; margin-top:0;">{stock['종목명']}</h1>
                <p style="color:#8b949e;">코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억</p>
                <hr style="border-color:#333;">
                <p>차트 흐름과 수급을 분석 중입니다. 궁금한 점은 우측 AI에게 물어보세요.</p>
            </div>
        """, unsafe_allow_html=True)

    with col3: # 오른쪽: AI 채팅 (디자인 및 답변 유지 적용)
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        
        # 채팅 메시지가 표시될 컨테이너
        chat_container = st.container(height=600)
        
        # [중요] 저장된 대화 내용을 먼저 화면에 그림 (사라짐 방지)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        # 사용자 입력 처리
        if prompt := st.chat_input("질문을 입력하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
            
            if model:
                try:
                    with chat_container:
                        with st.chat_message("assistant"):
                            with st.spinner("분석 중..."):
                                cur = st.session_state.selected_stock
                                full_query = f"종목: {cur['종목명']}, 질문: {prompt}"
                                response = model.generate_content(full_query)
                                answer = response.text
                                st.markdown(answer)
                                # 답변을 세션에 즉시 저장
                                st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"AI 오류: {e}")
            
            # 상태 확정 및 화면 갱신을 위해 리런
            st.rerun()
else:
    st.error("데이터 파일이 없습니다.")