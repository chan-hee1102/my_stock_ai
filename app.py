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

# 2) 디자인 CSS (임찬희님의 시그니처 디자인 + 재무 카드 스타일)
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
    
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; }
    .info-line { color: #ffffff !important; font-size: 1.1rem; font-weight: 700; margin-bottom: 10px; }
    .theme-line { 
        color: #ffffff !important; font-size: 1.1rem; font-weight: 700; 
        border-top: 1px solid #30363d; padding-top: 12px; margin-top: 12px;
    }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    
    /* 재무 카드 디자인 */
    .finance-card {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px;
        padding: 15px; text-align: center;
    }
    .finance-label { color: #8b949e; font-size: 0.9rem; font-weight: 600; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 및 재무 정보 로직
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

# Groq 및 테마 분석 함수 (기존 유지)
client = Groq(api_key=st.secrets.get("GROQ_API_KEY")) if st.secrets.get("GROQ_API_KEY") else None

def get_stock_brief(stock_name):
    if not client: return "AI 연결 실패"
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "당신은 한국 주식 전문가입니다. 본업과 관련된 테마 상승 사유를 '최근 ~테마에 속해서 ~중입니다' 형식으로 한 문장만 답변하세요. 온도 0.3으로 팩트 중심 답변하세요."}],
            max_tokens=200, temperature=0.3
        )
        return response.choices[0].message.content
    except: return "분석 지연 중"

# [신규] 재무 추이 시각화 함수
def draw_mini_chart(values, color):
    fig = go.Figure(go.Scatter(y=values, mode='lines+markers', line=dict(color=color, width=3), marker=dict(size=6)))
    fig.update_layout(
        template="plotly_dark", height=80, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False)
    )
    return fig

# 세션 관리
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()
    st.session_state.current_brief = get_stock_brief(data.iloc[0]['종목명'])

# 4) 메인 레이아웃
if data is not None:
    df_kospi = data[data["시장"].str.contains("KOSPI", na=False)].copy()
    df_kosdaq = data[data["시장"].str.contains("KOSDAQ", na=False)].copy()
    col_list, col_chat = st.columns([2.5, 7.5])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착</div>', unsafe_allow_html=True)
        with st.container(height=850):
            m_col1, m_col2 = st.columns(2)
            for m_df, m_name, m_key in [(df_kospi, "KOSPI", "k"), (df_kosdaq, "KOSDAQ", "q")]:
                with (m_col1 if m_name=="KOSPI" else m_col2):
                    st.markdown(f'<div class="market-header">{m_name}</div>', unsafe_allow_html=True)
                    for i, row in m_df.iterrows():
                        is_sel = st.session_state.selected_stock['종목명'] == row['종목명']
                        if st.button(f"● {row['종목명']}" if is_sel else f"  {row['종목명']}", key=f"{m_key}_{i}"):
                            st.session_state.selected_stock = row.to_dict()
                            st.session_state.messages = []
                            with st.spinner("AI 분석 중..."):
                                st.session_state.current_brief = get_stock_brief(row['종목명'])
                            st.rerun()

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} 전략 분석실</div>', unsafe_allow_html=True)
        
        # 차트 출력
        ticker_symbol = stock['종목코드'] + (".KS" if "KOSPI" in stock['시장'] else ".KQ")
        try:
            ticker_data = yf.Ticker(ticker_symbol)
            chart_df = ticker_data.history(period="3mo")
            fig = go.Figure(data=[go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
                                                 low=chart_df['Low'], close=chart_df['Close'],
                                                 increasing_line_color='#00e5ff', decreasing_line_color='#ff3366')])
            fig.update_layout(template="plotly_dark", height=380, margin=dict(l=10, r=10, t=10, b=10),
                              paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # --- [신규 기능] 재무 데이터 가져오기 ---
            income = ticker_data.financials.loc['Operating Income'] if 'Operating Income' in ticker_data.financials.index else None
            balance = ticker_data.balance_sheet
            debt_ratio = None
            if 'Total Debt' in balance.index and 'Stockholders Equity' in balance.index:
                debt_ratio = (balance.loc['Total Debt'] / balance.loc['Stockholders Equity']) * 100
        except: income, debt_ratio = None, None

        # 테마 브리핑 박스
        st.markdown(f"""
        <div class="report-box">
            <div class="info-line">
                <span class="highlight-mint">종목:</span> {stock["종목명"]} ({stock['종목코드']}) &nbsp;&nbsp;|&nbsp;&nbsp; 
                <span class="highlight-mint">시장:</span> {stock['시장']} &nbsp;&nbsp;|&nbsp;&nbsp; 
                <span class="highlight-mint">거래대금:</span> {stock.get('거래대금(억)', 0):,}억
            </div>
            <div class="theme-line">
                <span class="highlight-mint">🤖 AI 테마 브리핑:</span> {st.session_state.get('current_brief', '분석 중...')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- [신규] 재무 추이 카드 섹션 ---
        f_col1, f_col2, f_col3 = st.columns([1, 1, 2]) # 재무 카드 2개 + 여백
        
        with f_col1:
            st.markdown('<div class="finance-card"><div class="finance-label">💰 영업이익 추이 (연간)</div>', unsafe_allow_html=True)
            if income is not None and len(income) > 1:
                vals = income.values[::-1] # 과거->최근 순서
                color = "#00e5ff" if vals[-1] > vals[-2] else "#ff3366"
                st.plotly_chart(draw_mini_chart(vals, color), use_container_width=True)
            else: st.write("데이터 없음")
            st.markdown('</div>', unsafe_allow_html=True)

        with f_col2:
            st.markdown('<div class="finance-card"><div class="finance-label">📉 부채비율 추이 (연간)</div>', unsafe_allow_html=True)
            if debt_ratio is not None and len(debt_ratio) > 1:
                vals = debt_ratio.values[::-1]
                color = "#00e5ff" if vals[-1] < vals[-2] else "#ff3366" # 부채는 줄어들어야 민트색
                st.plotly_chart(draw_mini_chart(vals, color), use_container_width=True)
            else: st.write("데이터 없음")
            st.markdown('</div>', unsafe_allow_html=True)

        # 채팅창
        chat_container = st.container(height=350)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])
        if prompt := st.chat_input(f"{stock['종목명']} 분석 요청"):
            st.session_state.messages.append({"role": "user", "content": prompt}); st.rerun()