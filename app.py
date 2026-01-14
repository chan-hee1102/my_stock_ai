# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from google import genai
from datetime import datetime

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 박스 영역 배경색 */
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 25px; border: 1px solid #30363d;
    }

    /* 섹션 헤더 */
    .section-header { 
        color: #00e5ff !important; font-size: 1.5rem !important; font-weight: 800; 
        margin-bottom: 25px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }

    /* 좌측 종목 리스트: 글씨 크기 확대 및 하얀색 유지 */
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button {
        width: 100% !important;
        background-color: transparent !important;
        color: #ffffff !important; /* 기본 글씨 하얀색 */
        border: none !important;
        font-size: 2.2rem !important; 
        font-weight: 800 !important;
        text-align: left !important;
        padding: 12px 0px !important;
        transition: 0.3s;
    }
    
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button:hover {
        color: #00e5ff !important;
        transform: translateX(8px);
    }

    /* 리포트 박스 */
    .report-box {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px;
        padding: 25px; margin-bottom: 20px;
    }
    .report-text { color: #e0e6ed !important; font-size: 1.2rem !important; line-height: 1.8; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }

    /* 채팅 입력창 */
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 15px !important; padding: 10px !important; }
    div[data-testid="stChatInput"] textarea { color: #000000 !important; font-size: 1.15rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드 및 날짜 형식 수정
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, None
    latest_file = sorted(files)[-1]
    
    # 파일명에서 날짜 추출 및 포맷팅 (20260112 -> 2026-01-12)
    try:
        raw_date = latest_file.split('_')[-1].replace('.csv', '')
        # 숫자로만 되어 있을 경우 하이픈 추가
        if len(raw_date) == 8:
            date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
        else:
            date_str = raw_date
    except:
        date_str = datetime.now().strftime('%Y-%m-%d')
        
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "종목코드" in df.columns: df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df, date_str

data, data_date = load_data()

# 세션 초기화
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# Gemini 클라이언트
def get_client():
    if "GEMINI_API_KEY" not in st.secrets: return None
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

client = get_client()

# 4) 메인 레이아웃 (2:8 비율)
if data is not None:
    col_list, col_chat = st.columns([2, 8])

    with col_list:
        # 헤더 문구 수정: 2026-01-12 포착 종목
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 종목</div>', unsafe_allow_html=True)
        
        with st.container(height=850):
            for i, (idx, row) in enumerate(data.iterrows()):
                is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                
                # 선택된 종목은 양옆 기호 추가, 색상은 하얀색 유지
                if is_selected:
                    display_name = f"▶ {row['종목명']} ◀"
                    # 선택 시에도 하얀색이 강제 적용되도록 CSS 주입
                    st.markdown(f"""
                        <style>
                        div[data-testid="stColumn"]:nth-of-type(1) div[data-testid="stVerticalBlock"] div:nth-child({(i*2)+2}) button {{
                            color: #ffffff !important;
                        }}
                        </style>
                    """, unsafe_allow_html=True)
                else:
                    display_name = f"  {row['종목명']}"
                
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
            <div class="report-box">
                <div class="report-text">
                    <span class="highlight-mint">● 시장 관심도:</span> 당일 거래대금 <span class="highlight-mint">{stock.get('거래대금(억)', 'N/A')}억</span> 포착<br>
                    <span class="highlight-mint">● 분석 상태:</span> AI 커맨더가 {stock['종목명']}의 기술적/기본적 분석 결과를 생성했습니다.
                </div>
            </div>
            """, unsafe_allow_html=True)

            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        if prompt := st.chat_input(f"{stock['종목명']}에 대해 질문하세요"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            if client:
                response = client.models.generate_content(
                    model="gemini-flash-latest", 
                    contents=f"당신은 주식 전문가입니다. 종목명: {stock['종목명']}. 질문: {prompt}. 명확하고 전문적으로 답변하세요."
                )
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun()