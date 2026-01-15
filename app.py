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

# 2) 디자인 CSS (임찬희님의 시그니처 디자인 + 확장된 재무 카드)
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
    
    /* [개선] 더 커진 재무 카드 디자인 */
    .finance-card-large {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 15px;
        padding: 20px; margin-bottom: 20px;
    }
    .finance-label-large { color: #00e5ff; font-size: 1.1rem; font-weight: 800; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }
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

# Groq 및 테마 분석
client = Groq(api_key=st.secrets.get("GROQ_API_KEY")) if st.secrets.get("GROQ_API_KEY") else None
def get_stock_brief(stock_name):
    if not client: return "AI 연결 필요"
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "한국 주식 전문가로서 상승 테마를 한 문장으로 브리핑하세요. 팩트 중심 답변."}],
            temperature=0.3
        )
        return res.choices[0].message.content
    except: return "분석 지연 중"

# [개선] 고도화된 재무 차트 그리기 함수
def draw_detailed_finance_chart(dates, values, unit, is_debt=False):
    # 단위 변환 (영업이익의 경우 '억' 단위로 표시하기 위해 조정)
    display_values = values / 100000000 if "억" in unit else values
    
    fig = go.Figure()
    
    # 0 기준선 추가
    fig.add_hline(y=0, line_dash="dash", line_color="#8b949e", line_width=1)
    
    # 메인 데이터 선
    color = "#00e5ff" # 기본 민트색
    if not is_debt: # 영업이익: 마지막 값이 0보다 작으면 빨간색 계열
        line_color = "#00e5ff" if display_values[-1] > 0 else "#ff3366"
    else: # 부채비율: 마지막 값이 전년보다 낮아지면 민트(좋음)
        line_color = "#00e5ff" if display_values[-1] < display_values[-2] else "#ff3366" if len(display_values) > 1 else "#00e5ff"

    fig.add_trace(go.Scatter(
        x=dates, y=display_values,
        mode='lines+markers+text',
        text=[f"{v:,.1f}{unit}" for v in display_values],
        textposition="top center",
        textfont=dict(color="white", size=11),
        line=dict(color=line_color, width=3),
        marker=dict(size=8, color=line_color, line=dict(color='white', width=1)),
        hoverinfo="x+y"
    ))

    fig.update_layout(
        template="plotly_dark", height=250, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(color="#8b949e")),
        yaxis=dict(showgrid=True, gridcolor="#30363d", tickfont=dict(color="#8b949e"), zeroline=False),
    )
    return fig

# 세션 관리
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
            for m_df, m_name, m_key in [(df_kospi, "KOSPI", "k"), (df_kosdaq, "KOSDAQ", "q")]:
                with (m_col1 if m_name=="KOSPI" else m_col2):
                    st.markdown(f'<div class="market-header">{m_name}</div>', unsafe_allow_html=True)
                    for i, row in m_df.iterrows():
                        is_sel = st.session_state.selected_stock['종목명'] == row['종목명']
                        if st.button(f"● {row['종목명']}" if is_sel else f"  {row['종목명']}", key=f"{m_key}_{i}"):
                            st.session_state.selected_stock = row.to_dict()
                            st.session_state.messages = []
                            with st.spinner("분석 중..."): st.session_state.current_brief = get_stock_brief(row['종목명'])
                            st.rerun()

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} 전략 분석실</div>', unsafe_allow_html=True)
        
        # 캔들 차트
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
            
            # 재무 데이터 추출 (연간)
            income_statement = ticker_data.financials
            balance_sheet = ticker_data.balance_sheet
            
            op_income = income_statement.loc['Operating Income'].sort_index() if 'Operating Income' in income_statement.index else None
            
            debt_ratio_series = None
            if 'Total Debt' in balance_sheet.index and 'Stockholders Equity' in balance_sheet.index:
                debt_ratio_series = (balance_sheet.loc['Total Debt'] / balance_sheet.loc['Stockholders Equity'] * 100).sort_index()
        except: op_income, debt_ratio_series = None, None

        # 정보 및 테마 박스
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

        # --- [개선] 대형 재무 차트 섹션 (빨간 박스 크기 반영) ---
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        f_col1, f_col2 = st.columns(2)
        
        with f_col1:
            st.markdown('<div class="finance-card-large"><div class="finance-label-large">💰 연간 영업이익 추이 (Earnings)</div>', unsafe_allow_html=True)
            if op_income is not None:
                dates = op_income.index.strftime('%Y')
                st.plotly_chart(draw_detailed_finance_chart(dates, op_income.values, "억"), use_container_width=True)
            else: st.info("영업이익 데이터를 불러올 수 없습니다.")
            st.markdown('</div>', unsafe_allow_html=True)

        with f_col2:
            st.markdown('<div class="finance-card-large"><div class="finance-label-large">📉 연간 부채비율 추이 (Debt Ratio)</div>', unsafe_allow_html=True)
            if debt_ratio_series is not None:
                dates = debt_ratio_series.index.strftime('%Y')
                st.plotly_chart(draw_detailed_finance_chart(dates, debt_ratio_series.values, "%", is_debt=True), use_container_width=True)
            else: st.info("부채비율 데이터를 불러올 수 없습니다.")
            st.markdown('</div>', unsafe_allow_html=True)

        # 채팅 섹션
        chat_container = st.container(height=350)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])
        if prompt := st.chat_input("재무 상태를 바탕으로 장기 투자 전망을 물어보세요."):
            st.session_state.messages.append({"role": "user", "content": prompt}); st.rerun()