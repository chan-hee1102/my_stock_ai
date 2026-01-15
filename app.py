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

# 2) 디자인 CSS (사령부 스타일 강화)
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
    
    /* [개선] 정보 박스 및 테마 텍스트 디자인 */
    .report-box { 
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; 
        padding: 20px; margin-top: 15px;
    }
    .info-line { color: #ffffff !important; font-size: 1.1rem; font-weight: 700; margin-bottom: 10px; }
    .theme-line { 
        color: #00e5ff !important; font-size: 1.05rem; font-weight: 800; 
        border-top: 1px solid #30363d; padding-top: 12px; margin-top: 12px;
    }
    .highlight-mint { color: #00e5ff !important; }
    
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

# Groq 클라이언트
client = Groq(api_key=st.secrets.get("GROQ_API_KEY")) if st.secrets.get("GROQ_API_KEY") else None

# [신규] 종목 테마 분석 함수
def get_stock_brief(stock_name):
    if not client: return "AI 분석관 연결 실패"
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": f"당신은 한국 주식 전문가입니다. {stock_name}이 최근 어떤 테마에 속해있는지와 상승 사유를 한 문장으로만 브리핑하세요. '최근 ~테마에 속해서 ~중입니다' 형식을 유지하세요. 일본어 금지."}],
            max_tokens=150, temperature=0.5
        )
        return response.choices[0].message.content
    except:
        return "데이터 분석 중 오류 발생"

# 세션 상태 관리
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()
    st.session_state.current_brief = get_stock_brief(data.iloc[0]['종목명'])

# 4) 메인 레이아웃 (2.5:7.5)
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
                    is_sel = st.session_state.selected_stock['종목명'] == row['종목명']
                    if st.button(f"● {row['종목명']}" if is_sel else f"  {row['종목명']}", key=f"k_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.session_state.current_brief = get_stock_brief(row['종목명']) # 테마 실시간 분석
                        st.rerun()
            with m_col2:
                st.markdown('<div class="market-header">KOSDAQ</div>', unsafe_allow_html=True)
                for i, row in df_kosdaq.iterrows():
                    is_sel = st.session_state.selected_stock['종목명'] == row['종목명']
                    if st.button(f"● {row['종목명']}" if is_sel else f"  {row['종목명']}", key=f"q_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.session_state.current_brief = get_stock_brief(row['종목명']) # 테마 실시간 분석
                        st.rerun()

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} 전략 분석실</div>', unsafe_allow_html=True)
        
        # 차트 로직 (이전 성공 버전 유지)
        suffix = ".KS" if "KOSPI" in stock['시장'] else ".KQ"
        if "/" in stock['시장']: suffix = ".KS" if stock['종목코드'].startswith('0') else ".KQ"
        ticker_symbol = stock['종목코드'] + suffix

        try:
            ticker_data = yf.Ticker(ticker_symbol)
            chart_df = ticker_data.history(period="3mo")
            if not chart_df.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
                    low=chart_df['Low'], close=chart_df['Close'],
                    increasing_line_color='#00e5ff', decreasing_line_color='#ff3366'
                )])
                fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10),
                                  paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
        except: st.info("차트 데이터를 불러오는 중...")

        # --- [개선된 정보 박스: 거래대금 및 AI 테마 브리핑] ---
        st.markdown(f"""
        <div class="report-box">
            <div class="info-line">
                <span class="highlight-mint">종목:</span> {stock["종목명"]} ({stock['종목코드']}) &nbsp;&nbsp;|&nbsp;&nbsp; 
                <span class="highlight-mint">시장:</span> {stock['시장']} &nbsp;&nbsp;|&nbsp;&nbsp; 
                <span class="highlight-mint">거래대금:</span> {stock.get('거래대금(억)', 0):,}억
            </div>
            <div class="theme-line">
                🤖 AI 테마 브리핑: {st.session_state.get('current_brief', '분석 중...')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=450)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])

        if prompt := st.chat_input(f"{stock['종목명']}의 세부 대응 전략을 요청하세요."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()