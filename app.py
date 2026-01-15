# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from google import genai
from google.genai import types
from datetime import datetime

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (블랙 & 민트 유지)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 25px; border: 1px solid #30363d;
    }
    .section-header { 
        color: #00e5ff !important; font-size: 1.5rem !important; font-weight: 800; 
        margin-bottom: 25px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 2.2rem !important; font-weight: 800 !important;
        text-align: left !important; padding: 12px 0px !important; transition: 0.3s;
    }
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button:hover { color: #00e5ff !important; transform: translateX(8px); }
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 25px; margin-bottom: 20px; }
    .report-text { color: #e0e6ed !important; font-size: 1.2rem !important; line-height: 1.8; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 15px !important; padding: 10px !important; }
    div[data-testid="stChatInput"] textarea { color: #000000 !important; font-size: 1.15rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "종목코드" in df.columns: df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df, latest_file.split('_')[-1].replace('.csv', '')

data, data_date = load_data()

# 세션 상태 초기화
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# Gemini 클라이언트
def get_client():
    key = st.secrets.get("GEMINI_API_KEY")
    return genai.Client(api_key=key) if key else None

client = get_client()

# 4) 메인 화면 구성
if data is not None:
    col_list, col_chat = st.columns([2, 8])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 종목</div>', unsafe_allow_html=True)
        with st.container(height=850):
            for i, (idx, row) in enumerate(data.iterrows()):
                is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                if st.button(f"▶ {row['종목명']}" if is_selected else f"  {row['종목명']}", key=f"s_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.session_state.messages = []
                    st.rerun()

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} AI 전략 사령부</div>', unsafe_allow_html=True)
        
        # --- [고정] 상단 리포트 요약 박스 ---
        st.markdown(f"""
        <div class="report-box"><div class="report-text">
            <span class="highlight-mint">● 타겟:</span> {stock["종목명"]} ({stock.get('종목코드', 'N/A')})<br>
            <span class="highlight-mint">● 엔진:</span> Gemini 2.0 Flash (심층 분석 모드)<br>
            <span class="highlight-mint">● 업데이트:</span> {datetime.now().strftime('%Y-%m-%d %H:%M')} 실시간 데이터 적용
        </div></div>
        """, unsafe_allow_html=True)

        # 채팅 내역 표시 컨테이너
        chat_container = st.container(height=600)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.1rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        # 채팅 입력 및 처리
        if prompt := st.chat_input(f"{stock['종목명']}에 대한 실시간 분석을 요청하세요."):
            # 1. 사용자 메시지 추가 및 표시
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(f"<div style='font-size:1.1rem; color:#ffffff;'>{prompt}</div>", unsafe_allow_html=True)

            # 2. AI 응답 생성
            if client:
                with st.status("🚀 분석관이 데이터 트래킹 중...", expanded=True) as status:
                    try:
                        # 대화 맥락 포함
                        history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
                        
                        response = client.models.generate_content(
                            model="gemini-2.0-flash", 
                            contents=f"당신은 금융 전문가입니다. {stock['종목명']}에 대한 질문에 답변하세요: {prompt}\n\n맥락:\n{history}",
                            config=types.GenerateContentConfig(
                                tools=[types.Tool(google_search=types.GoogleSearch())]
                            )
                        )
                        
                        # 응답 텍스트 추출
                        res_text = ""
                        if hasattr(response, 'text') and response.text:
                            res_text = response.text
                        elif response.candidates:
                            for part in response.candidates[0].content.parts:
                                if part.text: res_text += part.text
                        
                        if not res_text:
                            res_text = "⚠️ 검색 결과를 요약하는 과정에서 지연이 발생했습니다. 다시 한번 질문해 주세요."

                        # 3. 답변 표시 및 저장
                        with chat_container:
                            with st.chat_message("assistant"):
                                st.markdown(f"<div style='font-size:1.1rem; color:#ffffff;'>{res_text}</div>", unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": res_text})
                        status.update(label="✅ 분석 완료", state="complete", expanded=False)
                        
                    except Exception as e:
                        status.update(label="❌ 오류 발생", state="error")
                        st.error(f"원인: {str(e)}")
            
            # 마지막에 rerun을 하지 않고 자연스럽게 상태 유지