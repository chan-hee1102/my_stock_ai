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

# 세션 관리
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

def get_client():
    key = st.secrets.get("GEMINI_API_KEY")
    return genai.Client(api_key=key) if key else None

client = get_client()

# 4) 레이아웃
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
        
        chat_container = st.container(height=650)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.1rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        if prompt := st.chat_input(f"{stock['종목명']} 심층 분석 요청..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun() # 사용자의 질문을 즉시 화면에 띄우기 위해 재실행

# 5) AI 응답 처리 (재실행 후 메시지가 유저 것으로 끝날 때 실행)
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    user_prompt = st.session_state.messages[-1]["content"]
    
    with st.chat_message("assistant"):
        with st.status("🚀 AI 분석관이 실시간 정보를 추적 중...", expanded=True) as status:
            try:
                # 2.0-flash 모델 고정 (가장 안정적)
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"종목 {stock['종목명']}에 대해 다음을 분석하라: {user_prompt}",
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                
                # 답변 추출 (무응답 원천 차단 로직)
                res_text = ""
                if hasattr(response, 'text') and response.text:
                    res_text = response.text
                elif response.candidates:
                    for part in response.candidates[0].content.parts:
                        if part.text: res_text += part.text
                
                if not res_text:
                    res_text = "⚠️ 검색 결과는 확인했으나 분석을 정리하는 과정에서 지연이 발생했습니다. 질문을 조금 더 구체적으로(예: '오늘 뉴스 알려줘') 해주세요."

                st.markdown(f"<div style='font-size:1.1rem; color:#ffffff;'>{res_text}</div>", unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": res_text})
                status.update(label="✅ 분석 완료", state="complete")
                
            except Exception as e:
                status.update(label="❌ 오류 발생", state="error")
                st.error(f"원인: {str(e)}")