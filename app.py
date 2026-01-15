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

# 2) 디자인 CSS (재무 차트 상단 밀착 및 신규 분석 영역 디자인)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 3분할 카드 디자인: 상단 정렬 강제 */
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 20px; border: 1px solid #30363d;
        display: flex; flex-direction: column; justify-content: flex-start;
    }
    
    .section-header { 
        color: #00e5ff !important; font-size: 1.3rem !important; font-weight: 800; 
        margin-bottom: 20px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }
    
    .market-header {
        background-color: #0d1117; color: #8b949e; font-size: 0.8rem; font-weight: 800;
        text-align: center; padding: 6px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #30363d;
    }
    
    .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 0.9rem !important; text-align: left !important; padding: 4px 0px !important;
    }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(3px); transition: 0.2s; }
    
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-top: 15px; }
    .info-line { color: #ffffff !important; font-size: 1rem; font-weight: 700; }
    .theme-line { color: #ffffff !important; font-size: 1rem; font-weight: 700; border-top: 1px solid #30363d; padding-top: 12px; margin-top: 12px; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    
    /* [신규] 분석 결과 영역 스타일 (찬희님이 요청한 빨간 박스 자리) */
    .analysis-placeholder {
        background-color: #161b22; border: 1px dashed #30363d; border-radius: 10px;
        padding: 20px; margin-bottom: 15px; min-height: 120px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        text-align: center;
    }
    .analysis-text { color: #8b949e; font-size: 0.9rem; font-weight: 600; }
    .probability-badge {
        background-color: rgba(0, 229, 255, 0.1); color: #00e5ff;
        padding: 5px 15px; border-radius: 20px; font-weight: 800; margin-top: 10px;
    }
    
    /* 재무 카드 영역 고정 */
    .finance-card-fixed {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px;
        padding: 15px; margin-top: 10px; min-height: 520px;
        display: flex; flex-direction: column; justify-content: flex-start;
    }
    .finance-label-fixed { color: #00e5ff; font-size: 1.1rem; font-weight: 800; margin-bottom: 15px; }

    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 12px !important; }
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
client = Groq(api_key=st.secrets.get("GROQ_API_KEY")) if st.secrets.get("GROQ_API_KEY") else None

# AI 분석 함수
def get_stock_brief(stock_name):
    if not client: return "AI 분석 대기 중..."
    try:
        prompt = (f"당신은 주식 전문가입니다. {stock_name}의 최근 이슈를 '최근 [이슈]로 인한 [테마] 테마에 속해서 상승 중입니다' 형식으로 답변하세요.")
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return res.choices[0].message.content
    except: return "분석 업데이트 중..."

# 재무 차트 그리기 (상단 여백 최소화)
def draw_pro_finance_chart(dates, values, unit, is_debt=False):
    display_values = values / 100000000 if "억" in unit else values
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=1)
    
    line_color = "#00e5ff" if (not is_debt and display_values[-1] > 0) or (is_debt and display_values[-1] < display_values[0]) else "#ff3366"
    
    fig.add_trace(go.Scatter(
        x=dates, y=display_values, mode='lines+markers+text',
        text=[f"{v:,.0f}{unit}" for v in display_values],
        textposition="top center", textfont=dict(color="white", size=10),
        line=dict(color=line_color, width=3.5), marker=dict(size=9, color=line_color)
    ))
    fig.update_layout(
        template="plotly_dark", height=260, 
        margin=dict(l=10, r=10, t=10, b=10), # 상단 마진 10px 고정
        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#30363d", zeroline=False),
        showlegend=False
    )
    return fig

# 4) 세션 관리 및 레이아웃
if data is not None:
    if "messages" not in st.session_state: st.session_state.messages = []
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
        st.session_state.current_brief = get_stock_brief(data.iloc[0]['종목명'])

    col_list, col_main, col_chat = st.columns([2, 5, 3])

    # [1] 왼쪽 리스트
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
                            with st.spinner("데이터 동기화 중..."):
                                st.session_state.current_brief = get_stock_brief(row['종목명'])
                            st.rerun()

    # [2] 가운데 메인 분석 보드
    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📉 {stock["종목명"]} 전략 분석실</div>', unsafe_allow_html=True)
        
        ticker_symbol = stock['종목코드'] + (".KS" if "KOSPI" in stock['시장'] else ".KQ")
        try:
            ticker_data = yf.Ticker(ticker_symbol)
            chart_df = ticker_data.history(period="3mo")
            fig_candle = go.Figure(data=[go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], increasing_line_color='#00e5ff', decreasing_line_color='#ff3366')])
            fig_candle.update_layout(template="plotly_dark", height=320, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_candle, use_container_width=True)
            
            income = ticker_data.financials.loc['Operating Income'].sort_index() if 'Operating Income' in ticker_data.financials.index else None
            debt = (ticker_data.balance_sheet.loc['Total Debt'] / ticker_data.balance_sheet.loc['Stockholders Equity'] * 100).sort_index() if 'Total Debt' in ticker_data.balance_sheet.index else None
        except: income, debt = None, None

        # 테마 브리핑
        st.markdown(f"""
        <div class="report-box">
            <div class="info-line">
                <span class="highlight-mint">종목:</span> {stock["종목명"]} ({stock['종목코드']}) &nbsp;|&nbsp; 
                <span class="highlight-mint">시장:</span> {stock['시장']} &nbsp;|&nbsp; 
                <span class="highlight-mint">거래대금:</span> {stock.get('거래대금(억)', 0):,}억
            </div>
            <div class="theme-line">
                <span class="highlight-mint">🤖 AI 비서 테마 브리핑:</span> {st.session_state.get('current_brief', '분석 중...')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 재무 및 상세 분석 섹션
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.markdown('<div class="finance-card-fixed"><div class="finance-label-fixed">💰 연간 영업이익 추이</div>', unsafe_allow_html=True)
            # [찬희님 요청 영역] 내일 오를 확률 및 AI 분석 결과 자리
            st.markdown(f"""
            <div class="analysis-placeholder">
                <span class="analysis-text">📉 {stock['종목명']} 전략 시뮬레이션</span>
                <span class="probability-badge">상승 확률 분석 대기 중</span>
            </div>
            """, unsafe_allow_html=True)
            if income is not None: st.plotly_chart(draw_pro_finance_chart(income.index.strftime('%Y'), income.values, "억"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with f_col2:
            st.markdown('<div class="finance-card-fixed"><div class="finance-label-fixed">📉 연간 부채비율 추이</div>', unsafe_allow_html=True)
            # [찬희님 요청 영역] 동일한 비율 유지를 위한 placeholder
            st.markdown(f"""
            <div class="analysis-placeholder">
                <span class="analysis-text">🔍 재무 안정성 정밀 진단</span>
                <span class="probability-badge">데이터 로딩 완료</span>
            </div>
            """, unsafe_allow_html=True)
            if debt is not None: st.plotly_chart(draw_pro_finance_chart(debt.index.strftime('%Y'), debt.values, "%", is_debt=True), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # [3] 오른쪽 AI 비서
    with col_chat:
        st.markdown(f'<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        chat_container = st.container(height=720)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(f"<div style='font-size:1.1rem; color:white;'>{m['content']}</div>", unsafe_allow_html=True)
        
        if prompt := st.chat_input("AI 비서에게 전략을 질문하세요."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"): st.write(prompt)
            if client:
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": f"당신은 {stock['종목명']} 전문 AI 비서입니다."}] + st.session_state.messages[-5:])
                ans = res.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": ans})
            st.rerun()