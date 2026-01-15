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

# 2) 디자인 CSS (재무 차트 수직 정렬 완벽 수정 및 3분할 최적화)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 3분할 카드 디자인 */
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 20px; border: 1px solid #30363d;
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
    
    /* 테마 설명 글씨를 흰색으로 통일 */
    .theme-line { color: #ffffff !important; font-size: 1rem; font-weight: 700; border-top: 1px solid #30363d; padding-top: 12px; margin-top: 12px; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    
    /* [긴급수정] 재무 카드 영역: 상단 패딩을 줄이고 높이를 고정하여 차트가 위로 붙게 함 */
    .finance-card-fixed {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px;
        padding: 5px 15px 0px 15px; margin-top: 10px; height: 360px; overflow: hidden;
    }
    .finance-label-fixed { color: #00e5ff; font-size: 1.1rem; font-weight: 800; margin-bottom: 0px; }

    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드 및 AI 분석 로직
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

# [대폭 강화] AI 테마 분석 프롬프트: 구체적인 이슈(엔비디아, 수주 등) 추출 유도
client = Groq(api_key=st.secrets.get("GROQ_API_KEY")) if st.secrets.get("GROQ_API_KEY") else None
def get_stock_brief(stock_name):
    if not client: return "AI 연결 실패"
    try:
        # AI에게 구체적인 협업 사례나 뉴스를 근거로 대라고 지시함
        prompt = (
            f"당신은 대한민국 최고의 주식 전략가입니다. 현재 {stock_name}의 주가 상승과 관련된 구체적인 '뉴스 이슈'나 '글로벌 협업 사례'(예: 엔비디아와 로봇 개발 협력, 테슬라 공급망 진입, 대규모 국방 수주 등)를 분석하세요.\n"
            f"분석 결과를 바탕으로 '최근 [구체적 이슈]로 인한 [구체적 테마명] 테마에 속해서 상승 중입니다' 형식으로 반드시 한 문장만 답변하세요.\n"
            f"'기술 테마', '성장주' 같은 애매한 말은 절대 쓰지 말고, {stock_name}만이 가진 구체적인 이유를 대답하세요."
        )
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "종목의 구체적인 상승 이슈를 분석하는 전문가입니다."},
                      {"role": "user", "content": prompt}],
            temperature=0.2 # 환각 방지를 위해 낮은 온도 유지
        )
        return res.choices[0].message.content
    except: return "실시간 이슈 분석 중..."

# [수정] 재무 차트 그리기 (상단 마진 최소화)
def draw_pro_finance_chart(dates, values, unit, is_debt=False):
    display_values = values / 100000000 if "억" in unit else values
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=1.5)
    
    line_color = "#00e5ff" if (not is_debt and display_values[-1] > 0) or (is_debt and display_values[-1] < display_values[0]) else "#ff3366"
    
    fig.add_trace(go.Scatter(
        x=dates, y=display_values, mode='lines+markers+text',
        text=[f"{v:,.0f}{unit}" for v in display_values],
        textposition="top center", textfont=dict(color="white", size=11, family="Arial Black"),
        line=dict(color=line_color, width=4), marker=dict(size=10, color=line_color)
    ))
    fig.update_layout(
        template="plotly_dark", height=300, 
        margin=dict(l=10, r=10, t=10, b=10), # [핵심] 상단 마진을 10px로 줄여 위로 붙임
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(color="#8b949e")),
        yaxis=dict(showgrid=True, gridcolor="#30363d", zeroline=False, tickfont=dict(color="#8b949e"))
    )
    return fig

# 세션 관리
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()
    st.session_state.current_brief = get_stock_brief(data.iloc[0]['종목명'])

# 4) 최종 3분할 레이아웃 실행 (2 : 5 : 3)
if data is not None:
    col_list, col_main, col_chat = st.columns([2, 5, 3])

    # [1] 왼쪽 종목 리스트
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
                            with st.spinner("이슈 분석 중..."): st.session_state.current_brief = get_stock_brief(row['종목명'])
                            st.rerun()

    # [2] 가운데 메인 분석 보드
    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📉 {stock["종목명"]} 전략 분석실</div>', unsafe_allow_html=True)
        
        ticker_symbol = stock['종목코드'] + (".KS" if "KOSPI" in stock['시장'] else ".KQ")
        try:
            ticker_data = yf.Ticker(ticker_symbol)
            chart_df = ticker_data.history(period="3mo")
            fig = go.Figure(data=[go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
                                                 low=chart_df['Low'], close=chart_df['Close'],
                                                 increasing_line_color='#00e5ff', decreasing_line_color='#ff3366')])
            fig.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10),
                              paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            income = ticker_data.financials.loc['Operating Income'].sort_index() if 'Operating Income' in ticker_data.financials.index else None
            debt_ratio = (ticker_data.balance_sheet.loc['Total Debt'] / ticker_data.balance_sheet.loc['Stockholders Equity'] * 100).sort_index() if 'Total Debt' in ticker_data.balance_sheet.index else None
        except: income, debt_ratio = None, None

        # 테마 브리핑 (구체적 이슈 반영)
        st.markdown(f"""
        <div class="report-box">
            <div class="info-line">
                <span class="highlight-mint">종목:</span> {stock["종목명"]} ({stock['종목코드']}) &nbsp;|&nbsp; 
                <span class="highlight-mint">시장:</span> {stock['시장']} &nbsp;|&nbsp; 
                <span class="highlight-mint">거래대금:</span> {stock.get('거래대금(억)', 0):,}억
            </div>
            <div class="theme-line">
                <span class="highlight-mint">🤖 AI 비서 테마 브리핑:</span> {st.session_state.get('current_brief', '데이터 분석 중...')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 재무 카드 (수직 정렬 최적화)
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.markdown('<div class="finance-card-fixed"><div class="finance-label-fixed">💰 연간 영업이익 (Earnings)</div>', unsafe_allow_html=True)
            if income is not None: st.plotly_chart(draw_pro_finance_chart(income.index.strftime('%Y'), income.values, "억"), use_container_width=True)
            else: st.info("재무 데이터 없음")
            st.markdown('</div>', unsafe_allow_html=True)
        with f_col2:
            st.markdown('<div class="finance-card-fixed"><div class="finance-label-fixed">📉 연간 부채비율 (Debt Ratio)</div>', unsafe_allow_html=True)
            if debt_ratio is not None: st.plotly_chart(draw_pro_finance_chart(debt_ratio.index.strftime('%Y'), debt_ratio.values, "%", is_debt=True), use_container_width=True)
            else: st.info("재무 데이터 없음")
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
                history = [{"role": "system", "content": f"당신은 {stock['종목명']}의 뉴스와 재무를 분석하는 AI 비서입니다."}]
                for m in st.session_state.messages[-5:]: history.append(m)
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=history)
                ans = res.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": ans})
            st.rerun()