import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# 1. 페이지 초기 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. [블로그 학습] Gemini AI 설정 (models/ 경로 명시)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 블로그 해결책대로 모델명을 정확히 지정합니다.
        model = genai.GenerativeModel('models/gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 초기화 실패: {e}")
        model = None
else:
    st.error("Secrets에 GEMINI_API_KEY가 없습니다.")
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

# --- 세션 상태 유지 (답변 사라짐 방지 핵심) ---
if "messages" not in st.session_state:
    st.session_state.messages = []  # 대화 기록 저장소
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# 4. 화면 레이아웃 구성
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📂 포착 종목")
    if data is not None:
        # 번호 리스트 구현 (i+1)
        for i, (idx, row) in enumerate(data.iterrows()):
            if st.button(f"{i+1}. {row['종목명']} | {row['거래대금(억)']}억", key=f"btn_{i}"):
                st.session_state.selected_stock = row.to_dict()
                st.rerun()

with col2:
    stock = st.session_state.selected_stock
    st.title(f"📊 {stock['종목명']} 분석")
    st.info(f"종목코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억")
    
    st.divider()
    
    # --- AI 채팅 영역 ---
    st.subheader("💬 AI Commander 상담")

    # [중요] 저장된 모든 대화 내용을 먼저 화면에 그립니다 (이게 있어야 안 사라짐)
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 사용자 입력 처리
    if prompt := st.chat_input("종목에 대해 궁금한 점을 입력하세요"):
        # 1. 사용자 질문 기록 및 표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. AI 답변 생성 및 기록
        if model:
            try:
                with st.chat_message("assistant"):
                    with st.spinner("분석 중..."):
                        # 블로그 지침에 따라 문맥과 함께 질문 전달
                        context = f"당신은 주식 전문가입니다. {stock['종목명']}에 대해 답하세요."
                        full_query = f"{context}\n\n질문: {prompt}"
                        
                        response = model.generate_content(full_query)
                        answer = response.text
                        
                        st.markdown(answer)
                        # 답변을 세션에 저장 (다음 리런 때 사라지지 않게 함)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"AI 응답 중 에러: {e}")
        
        # 마지막에 리런을 호출하여 상태를 확정시킵니다.
        st.rerun()