import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 디자인 CSS (최소화 및 강력한 버튼 스타일만 유지)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .section-header { color: #ffffff; font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #00e5ff; padding-left: 10px; }
    
    /* 중앙 상세 분석 박스 */
    .terminal-box { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 25px; height: 700px; overflow-y: auto; }
    
    /* 왼쪽 종목 버튼 스타일 */
    .stButton > button { 
        width: 100%; background-color: #1c2128; color: #ffffff; 
        border: 1px solid #30363d; margin-bottom: 8px; text-align: left; padding: 12px;
    }
    
    /* 채팅창 배경 구분을 위한 커스텀 스타일 */
    .chat-wrapper {
        background-color: #1c2128;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 함수
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

if data is not None:
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "messages" not in st.session_state:
        st.session_state.messages = []

    col1, col2, col3 = st.columns([2.2, 4.5, 3.3])

    with col1: # 왼쪽: 종목 리스트
        st.markdown('<div class="section-header">📂 포착된 종목</div>', unsafe_allow_html=True)
        with st.container(height=700):
            for i, row in data.iterrows():
                # 번호를 강제로 텍스트 앞에 붙임
                btn_label = f"{i+1}. {row['종목명']} | {row['거래대금(억)']}억"
                if st.button(btn_label, key=f"s_{row['종목코드']}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.rerun()

    with col2: # 중앙: 상세 분석
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📊 {stock["종목명"]} 분석</div>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="terminal-box">
                <h1 style="color:#00e5ff;">{stock['종목명']}</h1>
                <p style="color:#8b949e;">종목코드: {stock['종목코드']} | 거래대금: {stock['거래대금(억)']}억</p>
                <hr style="border-color:#333;">
                <h4 style="color:white;">뉴스 정보는 AI에게 물어보세요.</h4>
            </div>
        """, unsafe_allow_html=True)

    with col3: # 오른쪽: AI 채팅 (강제 배경색 주입)
        st.markdown('<div class="section-header">💬 AI Commander</div>', unsafe_allow_html=True)
        
        # HTML div로 감싸서 배경색을 강제로 만듭니다.
        st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)
        
        chat_container = st.container(height=560) # 배경색 영역 안으로 채팅창을 넣음
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        if prompt := st.chat_input("질문을 입력하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True) # wrapper 닫기

else:
    st.error("데이터가 없습니다.")