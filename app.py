# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
from datetime import datetime, timedelta

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (임찬희님의 시그니처 블랙 & 민트 디자인)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 25px; border: 1px solid #30363d;
    }
    .section-header { 
        color: #00e5ff !important; font-size: 1.4rem !important; font-weight: 800; 
        margin-bottom: 20px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }
    .market-header {
        background-color: #0d1117; color: #8b949e; font-size: 0.85rem; font-weight: 800;
        text-align: center; padding: 6px; border-radius: 8px; margin-bottom: 12px;
        border: 1px solid #30363d; letter-spacing: 0.5px;
    }
    .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 0.95rem !important; font-weight: 500 !important;
        text-align: left !important; padding: 5px 0px !important; transition: 0.2s;
    }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(4px); }
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 15px !important; padding: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드 로직
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "시장" in df.columns: df["시장"] = df["시장"].astype(str).str.strip().str.upper()
    if "종목코드" in df.columns: df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df, latest_file.split('_')[-1].replace('.csv', '')

data, data_date = load_data()

# 세션 상태 관리
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

def get_groq_client():
    key = st.secrets.get("GROQ_API_KEY")
    return Groq(api_key=key) if key else None

client = get_groq_client()

# 4) 메인 레이아웃 (2.5:7.5 비율 유지)
if data is not None:
    df_kospi = data[data["시장"] == "KOSPI"].copy()
    df_kosdaq = data[data["시장"] == "KOSDAQ"].copy()

    col_list, col_chat = st.columns([2.5, 7.5])

    # 왼쪽 종목 리스트
    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착</div>', unsafe_allow_html=True)
        with st.container(height=800):
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.markdown('<div class="market-header">KOSPI</div>', unsafe_allow_html=True)
                for i, row in df_kospi.iterrows():
                    label = f"● {row['종목명']}" if st.session_state.selected_stock['종목명'] == row['종목명'] else f"  {row['종목명']}"
                    if st.button(label, key=f"k_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.rerun()
            with m_col2:
                st.markdown('<div class="market-header">KOSDAQ</div>', unsafe_allow_html=True)
                for i, row in df_kosdaq.iterrows():
                    label = f"● {row['종목명']}" if st.session_state.selected_stock['종목명'] == row['종목명'] else f"  {row['종목명']}"
                    if st.button(label, key=f"q_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.rerun()

    # 오른쪽 채팅 및 차트 영역
    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} 전략 분석실</div>', unsafe_allow_html=True)
        
        # --- [신규 기능] 인터랙티브 캔들스틱 차트 ---
        with st.container():
            ticker = stock['종목코드'] + (".KS" if stock['시장'] == "KOSPI" else ".KQ")
            chart_df = yf.download(ticker, start=(datetime.now() - timedelta(days=90)), end=datetime.now())
            
            if not chart_df.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_df.index,
                    open=chart_df['Open'], high=chart_df['High'],
                    low=chart_df['Low'], close=chart_df['Close'],
                    increasing_line_color='#00e5ff', decreasing_line_color='#ff3366'
                )])
                fig.update_layout(
                    template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="#1c2128", plot_bgcolor="#1c2128",
                    xaxis_rangeslider_visible=False
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        <div class="report-box">
            <span class="highlight-mint">분석 대상:</span> {stock["종목명"]} ({stock['종목코드']}) | 
            <span class="highlight-mint">현재가:</span> {stock.get('현재가', 0):,}원 |
            <span class="highlight-mint">엔진:</span> Llama-3.3-70B
        </div>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=450)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])

        if prompt := st.chat_input("이 종목의 차트 흐름과 비교해서 전망을 물어보세요."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"): st.write(prompt)
            
            if client:
                with st.status("AI 분석 중...", expanded=False):
                    history = [{"role": "system", "content": f"당신은 {stock['종목명']} 전문 분석가입니다. 상단에 실제 캔들 차트가 표시되고 있으므로 텍스트로 차트를 그리지 마세요. 한국어로 답변하세요."}]
                    for m in st.session_state.messages[-5:]: history.append(m)
                    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=history)
                    ans = res.choices[0].message.content
                    with chat_container:
                        with st.chat_message("assistant"): st.write(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})
            st.rerun()