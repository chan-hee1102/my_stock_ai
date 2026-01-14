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
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button {
        width: 100% !important; background-color: transparent !important;
        color: #ffffff !important; border: none !important;
        font-size: 1.8rem !important; font-weight: 800 !important;
        text-align: left !important; padding: 12px 0px !important;
    }
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button:hover { color: #00e5ff !important; }
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 25px; margin-bottom: 20px; }
    .report-text { color: #e0e6ed !important; font-size: 1.2rem !important; line-height: 1.8; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드 및 날짜 포맷팅
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, "데이터 없음"
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, "데이터 없음"
    latest_file = sorted(files)[-1]
    
    raw_date = latest_file.split('_')[-1].replace('.csv', '')
    formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else raw_date
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    return df, formatted_date

data, data_date = load_data()

# AI 리포트 생성 함수
def get_ai_report(stock_info):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요."
    
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""
        당신은 주식 전문 투자 분석가입니다. 아래 종목에 대해 투자 전략을 세워주세요.
        종목명: {stock_info['종목명']}
        현재가: {stock_info['현재가']}원
        오늘의 거래대금: {stock_info['거래대금(억)']}억원

        분석 내용에는 기술적 분석 결과와 향후 대응 전략을 포함해주세요. 
        사용자가 보기 편하게 가독성 좋게 작성해주세요.
        """
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"❌ AI 분석 중 에러가 발생했습니다: {str(e)}"

# 세션 관리
if "selected_stock" not in st.session_state and data is not None:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# 4) 메인 화면 구성
if data is not None:
    col_list, col_chat = st.columns([2, 8])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 종목</div>', unsafe_allow_html=True)
        with st.container(height=850):
            for i, (idx, row) in enumerate(data.iterrows()):
                is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                display_name = f"▶ {row['종목명']} ◀" if is_selected else f"  {row['종목명']}"
                if st.button(display_name, key=f"btn_{idx}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()
                st.markdown("<hr style='margin:5px 0; border:0.5px solid #30363d; opacity:0.2;'>", unsafe_allow_html=True)

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} AI 정밀 리포트</div>', unsafe_allow_html=True)
        
        # AI 리포트 호출 및 출력
        with st.spinner(f"{stock['종목명']} 데이터를 분석 중입니다..."):
            report = get_ai_report(stock)
            st.markdown(f"""
                <div class="report-box">
                    <p class="report-text">{report.replace('\n', '<br>')}</p>
                </div>
            """, unsafe_allow_html=True)