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

# 2) 디자인 CSS (시인성 극대화)
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
        text-align: center; padding: 6px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #30363d;
    }
    .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 0.95rem !important; text-align: left !important; padding: 5px 0px !important;
    }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(4px); transition: 0.2s; }
    
    /* 리포트 박스 텍스트 강조 - 배경과 대비를 줌 */
    .report-box { 
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; 
        padding: 20px; margin-bottom: 20px;
    }
    .info-label { color: #00e5ff !important; font-weight: 800; font-size: 1.1rem; }
    .info-value { color: #ffffff !important; font-weight: 700; font-size: 1.1rem; margin-right: 15px; }
    .price-large { color: #00e5ff !important; font-size: 1.8rem !important; font-weight: 900; }
    
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 15px !important; padding: 10px !important; }
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
    if "시장" in df.columns:
        df["시장"] = df["시장"].astype(str).str.strip().str.upper()
    if "종목코드" in df.columns: 
        df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df, latest_file.split('_')[-1].replace('.csv', '')

data, data_date = load_data()

# 세션 상태 관리
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# 4) 메인 레이아웃 (2.5:7.5 비율 유지)
if data is not None:
    df_kospi = data[data["시장"].str.contains("KOSPI", na=False)].copy()
    df_kosdaq = data[data["시장"].str.contains("KOSDAQ", na=False)].copy()

    col_list, col_chat = st.columns([2.5, 7.5])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착</div>', unsafe_allow_html=True)
        with st.container(height=850):
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

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} 전략 분석실</div>', unsafe_allow_html=True)
        
        # --- [안정화된 차트 로직] ---
        # Ticker 설정 (.KS / .KQ)
        suffix = ".KS" if "KOSPI" in stock['시장'] else ".KQ"
        # 단, 시장구분이 뭉쳐있는 경우(KOSPI/KOSDAQ) 코드 첫자리가 0이면 코스피로 간주
        if "/" in stock['시장']:
            suffix = ".KS" if stock['종목코드'].startswith('0') else ".KQ"
        
        ticker_symbol = stock['종목코드'] + suffix

        try:
            # yf.download 대신 Ticker().history()를 써야 단일 종목 데이터가 훨씬 잘 잡힙니다.
            ticker_data = yf.Ticker(ticker_symbol)
            chart_df = ticker_data.history(period="3mo") # 최근 3개월 데이터
            
            if not chart_df.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_df.index,
                    open=chart_df['Open'], high=chart_df['High'],
                    low=chart_df['Low'], close=chart_df['Close'],
                    increasing_line_color='#00e5ff', decreasing_line_color='#ff3366'
                )])
                fig.update_layout(
                    template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="#1c2128", plot_bgcolor="#1c2128",
                    xaxis_rangeslider_visible=False,
                    yaxis=dict(gridcolor='#30363d'), xaxis=dict(gridcolor='#30363d')
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"'{stock['종목명']}'의 차트 데이터를 불러오는 중입니다... (Ticker: {ticker_symbol})")
        except Exception as e:
            st.error(f"차트 로드 실패: {ticker_symbol}")

        # --- [정보 요약 박스 디자인 개선] ---
        st.markdown(f"""
        <div class="report-box">
            <span class="info-label">대상:</span> <span class="info-value">{stock["종목명"]} ({stock['종목코드']})</span>
            <span class="info-label">시장:</span> <span class="info-value">{stock['시장']}</span> <br>
            <span class="info-label">현재 분석가:</span> <span class="info-value">Llama-3.3-70B Agent</span> <br>
            <hr style="border: 0.5px solid #30363d; margin: 15px 0;">
            <div style="text-align: right;">
                <span class="info-label" style="font-size: 1.2rem;">현재가:</span> 
                <span class="price-large">{stock.get('현재가', 0):,}원</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=450)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])

        if prompt := st.chat_input("이 종목의 차트 패턴이나 향후 대응 전략을 분석해드릴까요?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()