# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from google import genai
from google.genai import types
from datetime import datetime

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (블랙 & 민트 디자인 유지)
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

# 3) 데이터 로드 로직
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

if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

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
                <span class="highlight-mint">● 분석 대상:</span> {stock["종목명"]}<br>
                <span class="highlight-mint">● 엔진:</span> Gemini 2.0 Flash (최신 고성능)<br>
                <span class="highlight-mint">● 기능:</span> 실시간 구글 검색 및 심층 추론 리포트 작성
            </div></div>
            """, unsafe_allow_html=True)

            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        if prompt := st.chat_input(f"{stock['종목명']}에 대해 궁금한 점을 물어보세요!"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{prompt}</div>", unsafe_allow_html=True)
            
            if client:
                with st.status("AI 커맨더가 분석 중입니다...", expanded=True) as status:
                    try:
                        st.write("🔍 실시간 데이터 검색 및 분석 중...")
                        history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
                        
                        # 지침 강화
                        instruction = (
                            f"당신은 주식 분석 전문가입니다. 종목명: {stock['종목명']}\n"
                            f"지침: 구글 검색을 통해 최신 정보를 확인하고, 구체적인 수치와 함께 투자 전략을 제안하세요.\n"
                            f"답변은 반드시 한국어로 작성하며 가독성 좋게 출력하세요."
                        )
                        
                        # 모델명을 gemini-2.0-flash로 변경 (가장 안정적)
                        response = client.models.generate_content(
                            model="gemini-2.0-flash", 
                            contents=f"{instruction}\n\n사용자 질문: {prompt}",
                            config=types.GenerateContentConfig(
                                tools=[types.Tool(google_search=types.GoogleSearch())]
                            )
                        )
                        
                        # 응답 추출 로직 강화
                        response_text = ""
                        try:
                            if response.text:
                                response_text = response.text
                            else:
                                for part in response.candidates[0].content.parts:
                                    if part.text: response_text += part.text
                        except:
                            response_text = "⚠️ 검색 결과를 정리하는 중 오류가 발생했습니다. 다시 질문해 주시겠습니까?"

                        status.update(label="✅ 분석 완료!", state="complete", expanded=False)
                        with st.chat_message("assistant"):
                            st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{response_text}</div>", unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    
                    except Exception as e:
                        status.update(label="❌ 오류 발생", state="error", expanded=True)
                        st.error(f"상세 오류: {str(e)}")
            
            st.rerun()