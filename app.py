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

# 2) 디자인 CSS (버그 수정 및 가독성 극대화)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 카드 디자인 공통 */
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 20px; border: 1px solid #30363d;
    }
    
    .section-header { 
        color: #00e5ff !important; font-size: 1.4rem !important; font-weight: 800; 
        margin-bottom: 20px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }
    
    .market-header {
        background-color: #0d1117; color: #8b949e; font-size: 0.85rem; font-weight: 800;
        text-align: center; padding: 6px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #30363d;
    }
    
    /* 리스트 버튼 스타일 */
    .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 0.95rem !important; text-align: left !important; padding: 5px 0px !important;
    }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(4px); transition: 0.2s; }
    
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; }
    .info-line { color: #ffffff !important; font-size: 1.1rem; font-weight: 700; }
    .theme-line { color: #ffffff !important; font-size: 1.1rem; font-weight: 700; border-top: 1px solid #30363d; padding-top: 12px; margin-top: 12px; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    
    /* [수정] 재무 카드 위치 고정 */
    .finance-card-pro {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 15px;
        padding: 20px; margin-bottom: 20px; min-height: 380px;
    }
    .finance-label-pro { color: #00e5ff; font-size: 1.2rem; font-weight: 800; margin-bottom: 5px; }

    /* [핵심] 플로팅 버튼 위치 강제 고정 (화면 어디서든 보임) */
    div.stButton > button[key="fab_toggle"] {
        position: fixed !important;
        bottom: 40px !important;
        right: 40px !important;
        width: 70px !important;
        height: 70px !important;
        border-radius: 50% !important;
        background-color: #00e5ff !important;
        color: #000000 !important;
        font-size: 2rem !important;
        font-weight: bold !important;
        z-index: 999999 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 0 25px rgba(0, 229, 255, 0.6) !important;
        border: none !important;
    }
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

# AI 분석 함수
client = Groq(api_key=st.secrets.get("GROQ_API_KEY")) if st.secrets.get("GROQ_API_KEY") else None
def get_stock_brief(stock_name):
    if not client: return "AI 연결 실패"
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "한국 주식 전문가입니다. 기업 본업 테마를 '최근 ~테마에 속해서 ~중입니다' 형식으로 한 문장만 답변하세요."}],
            temperature=0.3
        )
        return res.choices[0].message.content
    except: return "분석 지연 중"

# 재무 차트 함수 (여백 버그 수정)
def draw_pro_finance_chart(dates, values, unit, is_debt=False):
    display_values = values / 100000000 if "억" in unit else values
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=1.5)
    
    line_color = "#00e5ff" if (not is_debt and display_values[-1] > 0) or (is_debt and display_values[-1] < display_values[0]) else "#ff3366"
    
    fig.add_trace(go.Scatter(
        x=dates, y=display_values, mode='lines+markers+text',
        text=[f"{v:,.0f}{unit}" for v in display_values],
        textposition="top center", textfont=dict(color="white", size=12),
        line=dict(color=line_color, width=4), marker=dict(size=10, color=line_color)
    ))
    fig.update_layout(
        template="plotly_dark", height=300, margin=dict(l=10, r=10, t=10, b=10), # 상단 마진 축소
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#30363d", zeroline=False)
    )
    return fig

# 세션 관리
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_active" not in st.session_state: st.session_state.chat_active = False
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()
    st.session_state.current_brief = get_stock_brief(data.iloc[0]['종목명'])

# 4) 메인 레이아웃
if data is not None:
    # 플로팅 버튼 (강제 고정)
    if st.button("💬", key="fab_toggle"):
        st.session_state.chat_active = not st.session_state.chat_active
        st.rerun()

    # 채팅창 상태에 따른 화면 구성
    if st.session_state.chat_active:
        col_list, col_main, col_chat = st.columns([2, 4.8, 3.2])
    else:
        col_list, col_main = st.columns([2.5, 7.5])
        col_chat = None

    # 왼쪽 종목 리스트 (기존 유지)
    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착</div>', unsafe_allow_html=True)
        with st.container(height=850):
            m_col1, m_col2 = st.columns(2)
            for m_df, m_name, m_key in [(data[data["시장"].str.contains("KOSPI", na=False)], "KOSPI", "k"), 
                                        (data[data["시장"].str.contains("KOSDAQ", na=False)], "KOSDAQ", "q")]:
                with (m_col1 if m_name=="KOSPI" else m_col2):
                    st.markdown(f'<div class="market-header">{m_name}</div>', unsafe_allow_html=True)
                    for i, row in m_df.iterrows():
                        is_sel = st.session_state.selected_stock['종목명'] == row['종목명']
                        if st.button(f"● {row['종목명']}" if is_sel else f"  {row['종목명']}", key=f"{m_key}_{i}"):
                            st.session_state.selected_stock = row.to_dict()
                            st.session_state.messages = []
                            with st.spinner("분석 중..."): st.session_state.current_brief = get_stock_brief(row['종목명'])
                            st.rerun()

    # 가운데 메인 분석 보드
    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📈 {stock["종목명"]} 전략 분석실</div>', unsafe_allow_html=True)
        
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
            
            income = ticker_data.financials.loc['Operating Income'].sort_index() if 'Operating Income' in ticker_data.financials.index else None
            debt_ratio = (ticker_data.balance_sheet.loc['Total Debt'] / ticker_data.balance_sheet.loc['Stockholders Equity'] * 100).sort_index() if 'Total Debt' in ticker_data.balance_sheet.index else None
        except: income, debt_ratio = None, None

        # 테마 브리핑
        st.markdown(f"""
        <div class="report-box">
            <div class="info-line">
                <span class="highlight-mint">종목:</span> {stock["종목명"]} ({stock['종목코드']}) &nbsp;|&nbsp; 
                <span class="highlight-mint">시장:</span> {stock['시장']} &nbsp;|&nbsp; 
                <span class="highlight-mint">거래대금:</span> {stock.get('거래대금(억)', 0):,}억
            </div>
            <div class="theme-line">
                <span class="highlight-mint">🤖 AI 테마 브리핑:</span> {st.session_state.get('current_brief', '데이터 분석 중...')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 재무 카드 (위치 수정 완료)
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.markdown('<div class="finance-card-pro"><div class="finance-label-pro">💰 영업이익 (Earnings)</div>', unsafe_allow_html=True)
            if income is not None: st.plotly_chart(draw_pro_finance_chart(income.index.strftime('%Y'), income.values, "억"), use_container_width=True)
            else: st.info("재무 데이터 누락")
            st.markdown('</div>', unsafe_allow_html=True)
        with f_col2:
            st.markdown('<div class="finance-card-pro"><div class="finance-label-pro">📉 부채비율 (Debt Ratio)</div>', unsafe_allow_html=True)
            if debt_ratio is not None: st.plotly_chart(draw_pro_finance_chart(debt_ratio.index.strftime('%Y'), debt_ratio.values, "%", is_debt=True), use_container_width=True)
            else: st.info("재무 데이터 누락")
            st.markdown('</div>', unsafe_allow_html=True)

    # 오른쪽 채팅 섹션
    if col_chat:
        with col_chat:
            st.markdown(f'<div class="section-header">🤖 전략 분석관</div>', unsafe_allow_html=True)
            chat_container = st.container(height=720)
            with chat_container:
                for m in st.session_state.messages:
                    with st.chat_message(m["role"]): st.markdown(f"<div style='font-size:1.1rem; color:white;'>{m['content']}</div>", unsafe_allow_html=True)
            
            if prompt := st.chat_input("AI에게 종목의 정밀 분석을 요청하세요."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with chat_container:
                    with st.chat_message("user"): st.write(prompt)
                if client:
                    history = [{"role": "system", "content": f"당신은 {stock['종목명']}의 모든 데이터를 분석하는 AI 전략관입니다."}]
                    for m in st.session_state.messages[-5:]: history.append(m)
                    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=history)
                    ans = res.choices[0].message.content
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                st.rerun()