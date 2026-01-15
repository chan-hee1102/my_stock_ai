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

# 2) 디자인 CSS (시인성 강화 버전)
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
    
    /* 리포트 박스 텍스트 색상 및 밝기 조정 */
    .report-box { 
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; 
        padding: 20px; margin-bottom: 20px; color: #ffffff !important; /* 전체 글씨 흰색으로 강조 */
    }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    .price-text { font-size: 1.3rem !important; font-weight: 700; color: #ffffff !important; }
    
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 15px !important; padding: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드 및 전처리
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

# 세션 관리
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

client = Groq(api_key=st.secrets.get("GROQ_API_KEY")) if st.secrets.get("GROQ_API_KEY") else None

# 4) 메인 레이아웃 (2.5:7.5)
if data is not None:
    # 시장 분류 필터링 ( contains 사용으로 유연하게 처리 )
    df_kospi = data[data["시장"].str.contains("KOSPI", na=False)].copy()
    df_kosdaq = data[data["시장"].str.contains("KOSDAQ", na=False)].copy()

    col_list, col_chat = st.columns([2.5, 7.5])

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

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} 전략 분석실</div>', unsafe_allow_html=True)
        
        # --- 차트 데이터 로드 및 오류 방지 로직 ---
        # 팁: yfinance는 KOSPI 종목은 .KS, KOSDAQ 종목은 .KQ를 사용함
        # 시장구분이 뭉쳐있는 경우(KOSPI/KOSDAQ)는 종목코드로 판단 시도
        if "KOSPI" in stock['시장'] and "/" not in stock['시장']:
            ticker_symbol = stock['종목코드'] + ".KS"
        elif "KOSDAQ" in stock['시장'] and "/" not in stock['시장']:
            ticker_symbol = stock['종목코드'] + ".KQ"
        else:
            # 분류가 안 된 경우 (현대차 같은 0으로 시작하는 대형주는 대개 .KS)
            ticker_symbol = stock['종목코드'] + (".KS" if stock['종목코드'].startswith('0') else ".KQ")

        try:
            chart_df = yf.download(ticker_symbol, start=(datetime.now() - timedelta(days=100)), end=datetime.now(), progress=False)
            if not chart_df.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
                    low=chart_df['Low'], close=chart_df['Close'],
                    increasing_line_color='#00e5ff', decreasing_line_color='#ff3366'
                )])
                fig.update_layout(
                    template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis_rangeslider_visible=False
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"데이터를 불러올 수 없습니다 ({ticker_symbol})")
        except:
            st.error("차트 로딩 중 오류가 발생했습니다.")

        # 정보 요약 박스 (글씨 강조)
        st.markdown(f"""
        <div class="report-box">
            <span class="highlight-mint">분석 대상:</span> {stock["종목명"]} ({stock['종목코드']}) | 
            <span class="highlight-mint">시장:</span> {stock['시장']} <br>
            <span class="highlight-mint">현재가:</span> <span class="price-text">{stock.get('현재가', 0):,}원</span>
        </div>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=500)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])

        if prompt := st.chat_input("이 종목의 차트 패턴과 전망을 분석해드릴까요?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()