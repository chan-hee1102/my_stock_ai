# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from google import genai
from datetime import datetime

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (글씨 하얀색 고정 및 크기 확대)
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
    /* 종목 리스트 버튼 스타일 */
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button {
        width: 100% !important;
        background-color: transparent !important;
        color: #ffffff !important; /* 하얀색 고정 */
        border: none !important;
        font-size: 2.2rem !important; 
        font-weight: 800 !important;
        text-align: left !important;
        padding: 12px 0px !important;
    }
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button:hover {
        color: #00e5ff !important;
    }
    .report-box {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px;
        padding: 25px; margin-bottom: 20px;
    }
    .report-text { color: #e0e6ed !important; font-size: 1.2rem !important; line-height: 1.8; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드 및 날짜 포맷팅 (YYYYMMDD -> YYYY-MM-DD)
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, "날짜 없음"
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, "날짜 없음"
    latest_file = sorted(files)[-1]
    
    # 날짜 추출 및 하이픈 추가 (20260114 -> 2026-01-14)
    raw_date = latest_file.split('_')[-1].replace('.csv', '')
    if len(raw_date) == 8:
        formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    else:
        formatted_date = raw_date
        
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    return df, formatted_date

data, data_date = load_data()

# 세션 관리
if "selected_stock" not in st.session_state and data is not None:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# 4) 메인 화면 구성
if data is not None:
    col_list, col_chat = st.columns([2, 8])

    with col_list:
        # 요청하신 날짜 형식: 2026-01-14 포착 종목
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 종목</div>', unsafe_allow_html=True)
        
        with st.container(height=850):
            for i, (idx, row) in enumerate(data.iterrows()):
                is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                # 기호 2개 추가
                display_name = f"▶ {row['종목명']} ◀" if is_selected else f"  {row['종목명']}"
                
                if st.button(display_name, key=f"btn_{idx}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()
                st.markdown("<hr style='margin:5px 0; border:0.5px solid #30363d; opacity:0.2;'>", unsafe_allow_html=True)

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} AI 정밀 리포트</div>', unsafe_allow_html=True)
        # (이하 리포트 및 채팅 로직 생략 - 기존과 동일)