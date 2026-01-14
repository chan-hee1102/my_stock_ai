# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from google import genai
from datetime import datetime

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (기존 유지)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stHorizontalBlock"] > div { background-color: #1c2128; border-radius: 15px; padding: 25px; border: 1px solid #30363d; }
    .section-header { color: #00e5ff !important; font-size: 1.5rem !important; font-weight: 800; margin-bottom: 25px; border-left: 6px solid #00e5ff; padding-left: 15px; }
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 25px; margin-bottom: 20px; }
    .report-text { color: #e0e6ed !important; font-size: 1.2rem !important; line-height: 1.8; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    /* 버튼 스타일 */
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 1.8rem !important; font-weight: 800 !important;
        text-align: left !important; padding: 10px 0px !important;
    }
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

# 세션 관리
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# 4) Gemini 클라이언트 (중요: 에러 체크 추가)
def get_client():
    # Secrets에 저장된 키 이름을 둘 다 확인합니다.
    key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    if not key:
        return None
    try:
        return genai.Client(api_key=key)
    except:
        return None

client = get_client()

# 5) 메인 레이아웃
if data is not None:
    col_list, col_chat = st.columns([2, 8])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 종목</div>', unsafe_allow_html=True)
        with st.container(height=800):
            for i, (idx, row) in enumerate(data.iterrows()):
                is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                display_name = f"▶ {row['종목명']} ◀" if is_selected else f"  {row['종목명']}"
                if st.button(display_name, key=f"stock_btn_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.session_state.messages = []
                    st.rerun()

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} AI 정밀 리포트</div>', unsafe_allow_html=True)
        
        chat_container = st.container(height=700)
        with chat_container:
            st.markdown(f"""
            <div class="report-box"><div class="report-text">
                <span class="highlight-mint">● 시장 관심도:</span> 당일 거래대금 <span class="highlight-mint">{stock.get('거래대금(억)', 'N/A')}억</span> 포착<br>
                <span class="highlight-mint">● 분석 상태:</span> AI 커맨더 분석 대기 중
            </div></div>
            """, unsafe_allow_html=True)

            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        # 채팅 입력창
        if prompt := st.chat_input(f"{stock['종목명']}에 대해 질문하세요"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # 1. API 키가 아예 없는 경우
            if client is None:
                st.session_state.messages.append({"role": "assistant", "content": "⚠️ 에러: Streamlit Secrets에 API 키가 설정되지 않았습니다."})
            else:
                try:
                    # 2. AI 호출 시도
                    with st.spinner("AI가 분석 중입니다..."):
                        response = client.models.generate_content(
                            model="gemini-flash-latest", 
                            contents=f"당신은 주식 전문가입니다. 종목명: {stock['종목명']}. 질문: {prompt}. 명확하고 전문적으로 답변하세요."
                        )
                        if response and response.text:
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                        else:
                            st.session_state.messages.append({"role": "assistant", "content": "⚠️ 에러: AI가 빈 응답을 보냈습니다."})
                except Exception as e:
                    # 3. 상세 에러를 채팅창에 표시
                    st.session_state.messages.append({"role": "assistant", "content": f"⚠️ AI 호출 오류 발생: {str(e)}"})
            
            st.rerun()