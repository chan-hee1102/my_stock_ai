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
        
        chat_container = st.container(height=700)
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

        # --- 통합 AI 채팅 로직 (상태 표시 및 답변 보장) ---
        if prompt := st.chat_input(f"{stock['종목명']}에 대해 자유롭게 대화해보세요!"):
            # 1. 사용자 메시지 추가
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{prompt}</div>", unsafe_allow_html=True)
            
            if client:
                # 2. 생각 중... 상태 표시 시작
                with st.status("AI 커맨더가 생각 중입니다...", expanded=True) as status:
                    try:
                        st.write("🔍 최신 데이터 검색 중...")
                        history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
                        
                        instruction = (
                            f"당신은 {stock['종목명']}의 주식 전문가입니다. 오늘 날짜는 {datetime.now().strftime('%Y-%m-%d')}입니다.\n"
                            f"지침:\n"
                            f"1. 반드시 '구글 검색' 도구를 사용하여 실시간 정보를 확인하세요.\n"
                            f"2. 그래프 시각화나 웹 크롤링 코드를 직접 실행할 수는 없음을 명확히 알리세요.\n"
                            f"3. 대신 필요한 데이터 수치나 재무제표 내용은 텍스트나 표 형식으로 정리해서 답변하세요.\n"
                            f"4. 답변을 생성할 수 없는 경우, 그 이유를 구체적으로 설명하세요.\n\n"
                            f"대화 내역:\n{history_context}"
                        )
                        
                        google_search_tool = types.Tool(google_search=types.GoogleSearch())

                        st.write("🧠 답변 구성 중...")
                        response = client.models.generate_content(
                            model="gemini-1.5-flash", 
                            contents=f"{instruction}\n\n사용자 질문: {prompt}",
                            config=types.GenerateContentConfig(tools=[google_search_tool])
                        )
                        
                        # 3. 응답 텍스트 추출 (가장 안전한 방식)
                        response_text = ""
                        if response.candidates:
                            for part in response.candidates[0].content.parts:
                                if part.text:
                                    response_text += part.text
                        
                        if not response_text:
                            response_text = "⚠️ 요청하신 작업(시각화/크롤링 등)을 현재 직접 수행할 수 없습니다. 관련 수치 데이터나 뉴스 내용을 텍스트로 정리해 드릴까요?"

                        # 4. 상태 표시 완료 및 답변 출력
                        status.update(label="✅ 답변 생성 완료!", state="complete", expanded=False)
                        with st.chat_message("assistant"):
                            st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{response_text}</div>", unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    
                    except Exception as e:
                        status.update(label="❌ 오류 발생", state="error", expanded=True)
                        st.error(f"상세 오류: {str(e)}")
                        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ 죄송합니다. 답변 생성 중 오류가 발생했습니다. (사유: {str(e)})"})
            
            st.rerun()