# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from google import genai
from google.genai import types
from datetime import datetime

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (사용자님의 블랙 & 민트 디자인 유지)
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
    try:
        raw_date = latest_file.split('_')[-1].replace('.csv', '')
        date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else raw_date
    except:
        date_str = datetime.now().strftime('%Y-%m-%d')
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "종목코드" in df.columns: df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df, date_str

data, data_date = load_data()

# 세션 상태 초기화
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# Gemini 클라이언트 (Secrets 사용)
def get_client():
    key = st.secrets.get("GEMINI_API_KEY")
    if not key: return None
    return genai.Client(api_key=key)

client = get_client()

# 4) 메인 레이아웃
if data is not None:
    col_list, col_chat = st.columns([2, 8])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 종목</div>', unsafe_allow_html=True)
        with st.container(height=850):
            for i, (idx, row) in enumerate(data.iterrows()):
                is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                display_name = f"▶ {row['종목명']} ◀" if is_selected else f"  {row['종목명']}"
                if st.button(display_name, key=f"stock_btn_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.session_state.messages = []
                    st.rerun()
                st.markdown("<hr style='margin:5px 0; border:0.5px solid #30363d; opacity:0.3;'>", unsafe_allow_html=True)

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} AI 정밀 리포트</div>', unsafe_allow_html=True)
        
        chat_container = st.container(height=800)
        with chat_container:
            st.markdown(f"""
            <div class="report-box"><div class="report-text">
                <span class="highlight-mint">● 현재 시점:</span> {datetime.now().strftime('%Y-%m-%d')} 기준 분석<br>
                <span class="highlight-mint">● 검색 모드:</span> 최신 구글 검색 및 대화 내역 반영 중
            </div></div>
            """, unsafe_allow_html=True)

            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        # --- 통합 AI 채팅 로직 (기억 + 검색 + 오류 방지) ---
        if prompt := st.chat_input(f"{stock['종목명']}에 대해 자유롭게 대화해보세요!"):
            # 1. 사용자 메시지 즉시 추가
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            if client:
                try:
                    # 대화 문맥 유지
                    history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
                    
                    # AI 지침: 시각화 불가 안내 포함
                    instruction = (
                        f"당신은 {stock['종목명']}의 주식 전문가입니다. 오늘 날짜는 {datetime.now().strftime('%Y-%m-%d')}입니다.\n"
                        f"반드시 '구글 검색' 도구를 사용하여 최신 정보를 확인하세요.\n"
                        f"중요: 당신은 텍스트로만 답변할 수 있습니다. 그래프를 그려달라는 요청에는 '이미지를 직접 그릴 수는 없지만, 관련 수치 데이터를 표나 텍스트로 정리해드리겠습니다'라고 답하고 데이터를 제공하세요.\n\n"
                        f"대화 내역:\n{history_context}"
                    )
                    
                    google_search_tool = types.Tool(google_search=types.GoogleSearch())

                    # 2. AI 호출 (스피너 표시)
                    with st.spinner("AI가 최신 정보를 검색하며 답변을 생성 중입니다..."):
                        response = client.models.generate_content(
                            model="gemini-1.5-flash", 
                            contents=f"{instruction}\n\n사용자 질문: {prompt}",
                            config=types.GenerateContentConfig(tools=[google_search_tool])
                        )
                    
                    # 3. 응답 텍스트 추출 및 저장 (안전 처리)
                    response_text = ""
                    if hasattr(response, 'text') and response.text:
                        response_text = response.text
                    elif response.candidates:
                        # 텍스트가 직접 안 보일 경우 첫 번째 후보의 파트 확인
                        for part in response.candidates[0].content.parts:
                            if part.text:
                                response_text += part.text
                    
                    if response_text:
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    else:
                        st.session_state.messages.append({"role": "assistant", "content": "⚠️ 죄송합니다. 정보를 찾았으나 답변을 구성하는 데 실패했습니다. 다시 질문해 주세요."})
                
                except Exception as e:
                    st.error(f"⚠️ 오류 발생: {str(e)}")
            
            # 4. 화면 갱신
            st.rerun()