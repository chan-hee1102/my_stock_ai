# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
import re
from groq import Groq
from datetime import datetime, timedelta

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (임찬희님 시그니처 디자인 + 확률 박스 강조)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 15px; border: 1px solid #30363d;
        display: flex !important; flex-direction: column !important; justify-content: flex-start !important;
    }
    .section-header { color: #00e5ff !important; font-size: 1.3rem !important; font-weight: 800; margin-bottom: 15px; border-left: 6px solid #00e5ff; padding-left: 15px; }
    .market-header { background-color: #0d1117; color: #8b949e; font-size: 0.8rem; font-weight: 800; text-align: center; padding: 6px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #30363d; }
    .stButton > button { width: 100% !important; background-color: transparent !important; color: #ffffff !important; border: none !important; font-size: 0.9rem !important; text-align: left !important; padding: 4px 0px !important; }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(3px); transition: 0.2s; }
    
    /* 테마 및 분석 박스 */
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-top: 10px; margin-bottom: 15px; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    
    /* 통합 분석 영역 (가운데 웅장한 확률 박스) */
    .wide-analysis-box {
        background-color: #161b22; border: 1px dashed #00e5ff; border-radius: 12px;
        padding: 30px; margin-bottom: 15px; text-align: center; min-height: 280px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }
    .prob-value { font-size: 4.8rem; font-weight: 900; color: #00e5ff; text-shadow: 0 0 30px rgba(0,229,255,0.5); margin: 5px 0; }
    .prob-desc { color: #ffffff; font-size: 1.1rem; font-weight: 600; line-height: 1.5; margin-top: 10px; }

    /* 재무제표 헤더 */
    .finance-header-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px 12px; margin-bottom: 0px; width: 100%; display: flex; align-items: center; }
    .finance-label-compact { color: #00e5ff; font-size: 0.9rem; font-weight: 800; margin: 0; }
    .finance-card-compact { background-color: transparent; padding: 0px; margin-top: -15px !important; min-height: auto !important; display: flex !important; flex-direction: column !important; }

    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 확률 계산 및 AI 연동 로직
def get_robust_rise_probability(ticker_symbol, stock_name):
    try:
        # 1. 과거 데이터 수집 (백테스팅 기본값 2년)
        df = yf.download(ticker_symbol, period="2y", interval="1d", progress=False)
        if len(df) < 30: return 50, "분석 가능한 과거 데이터가 부족합니다."

        df['Vol_MA'] = df['Volume'].rolling(window=20).mean()
        df['Price_Change'] = df['Close'].pct_change()
        
        # 찬희님의 선정 기준 시뮬레이션: 거래량 급증 + 상승 마감
        signals = df[(df['Volume'] > df['Vol_MA'] * 1.8) & (df['Price_Change'] > 0.015)]
        
        success = 0
        for i in range(len(signals)):
            try:
                idx = df.index.get_loc(signals.index[i])
                if idx + 1 < len(df) and df.iloc[idx + 1]['Close'] > df.iloc[idx]['Close']: success += 1
            except: continue
        
        # 기본 통계 확률 (백테스팅 결과)
        hit_rate = int((success / len(signals) * 100)) if len(signals) > 0 else 52

        # 2. AI에게 최종 판단 요청
        if client:
            prompt = (f"종목: {stock_name}\n과거 유사패턴 포착: {len(signals)}회\n익일 상승 적중: {success}회\n"
                      f"위 통계를 바탕으로 내일 주가가 상승할 확률(%)을 정하고 '확률: [숫자]%' 형식으로 첫 줄에 답한 뒤, 이유를 한국어 한 줄로 쓰세요.")
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "주식 데이터 전문가입니다. 100% 한국어로만 답변하세요."},
                          {"role": "user", "content": prompt}], temperature=0.1
            )
            ai_ans = res.choices[0].message.content
            
            # [수정] 숫자 추출 로직 강화 (정규식 사용)
            numbers = re.findall(r'\d+', ai_ans.split('\n')[0])
            final_prob = int(numbers[0]) if numbers else hit_rate
            final_desc = ai_ans.split('\n')[-1].strip()
            return final_prob, final_desc
        
        return hit_rate, f"과거 {len(signals)}회 포착 중 {success}회 상승 적중 (통계 기반)"
    except Exception as e:
        return 55, f"데이터 분석 중: {str(e)}"

# 4) 데이터 로드 및 UI 초기화
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "종목코드" in df.columns: df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df, latest_file.split('_')[-1].replace('.csv', '')

data, data_date = load_data()
client = Groq(api_key=st.secrets.get("GROQ_API_KEY")) if st.secrets.get("GROQ_API_KEY") else None

def get_stock_brief(stock_name):
    if not client: return "AI 연결 필요"
    try:
        prompt = (f"{stock_name}의 상승 이슈를 '최근 [이슈]로 인한 [테마] 테마에 속해서 상승 중입니다' 형식으로 한국어로만 답변하세요.")
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": "한국어 전용 주식 전문가입니다."}, {"role": "user", "content": prompt}], temperature=0.1)
        return res.choices[0].message.content
    except: return "분석 로딩 중..."

# 5) 메인 레이아웃 실행
if data is not None:
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
        st.session_state.messages = []
        ticker = st.session_state.selected_stock['종목코드'] + (".KS" if "KOSPI" in st.session_state.selected_stock['시장'] else ".KQ")
        prob, desc = get_robust_rise_probability(ticker, st.session_state.selected_stock['종목명'])
        st.session_state.prob, st.session_state.prob_desc = prob, desc
        st.session_state.current_brief = get_stock_brief(data.iloc[0]['종목명'])

    col_list, col_main, col_chat = st.columns([2, 5, 3])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착</div>', unsafe_allow_html=True)
        with st.container(height=850):
            m_col1, m_col2 = st.columns(2)
            for m_df, m_name, m_key in [(data[data["시장"].str.contains("KOSPI", na=False)], "KOSPI", "k"), (data[data["시장"].str.contains("KOSDAQ", na=False)], "KOSDAQ", "q")]:
                with (m_col1 if m_name=="KOSPI" else m_col2):
                    st.markdown(f'<div class="market-header">{m_name}</div>', unsafe_allow_html=True)
                    for i, row in m_df.iterrows():
                        if st.button(f"● {row['종목명']}" if st.session_state.selected_stock['종목명'] == row['종목명'] else f"  {row['종목명']}", key=f"{m_key}_{i}"):
                            st.session_state.selected_stock = row.to_dict()
                            st.session_state.messages = []
                            with st.spinner("AI 확률 분석 중..."):
                                ticker = row['종목코드'] + (".KS" if "KOSPI" in row['시장'] else ".KQ")
                                prob, desc = get_robust_rise_probability(ticker, row['종목명'])
                                st.session_state.prob, st.session_state.prob_desc = prob, desc
                                st.session_state.current_brief = get_stock_brief(row['종목명'])
                            st.rerun()

    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📈 {stock["종목명"]} 전략 사령부</div>', unsafe_allow_html=True)
        
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
        st.markdown(f'<div class="report-box"><div class="info-line"><span class="highlight-mint">종목:</span> {stock["종목명"]} ({stock["종목코드"]}) | <span class="highlight-mint">거래대금:</span> {stock.get("거래대금(억)", 0):,}억</div>'
                    f'<div class="theme-line"><span class="highlight-mint">🤖 AI 테마 브리핑:</span> {st.session_state.current_brief}</div></div>', unsafe_allow_html=True)

        # [핵심] 통합 분석 영역: AI가 산출한 확률 숫자 표시
        st.markdown(f"""
        <div class="wide-analysis-box">
            <span class="analysis-title">🎯 AI 익일 주가 상승 확률 분석</span>
            <div class="prob-value">{st.session_state.prob}%</div>
            <div class="prob-desc">{st.session_state.prob_desc}</div>
        </div>
        """, unsafe_allow_html=True)

        # 재무제표 (타이틀 헤더 박스 적용)
        f_col1, f_col2 = st.columns(2)
        for col, title, d_s, unit, is_d in [(f_col1, "💰 연간 영업이익 추이", income, "억", False), (f_col2, "📉 연간 부채비율 추이", debt, "%", True)]:
            with col:
                st.markdown('<div class="finance-card-compact">', unsafe_allow_html=True)
                st.markdown(f'<div class="finance-header-box"><span class="finance-label-compact">{title}</span></div>', unsafe_allow_html=True)
                if d_s is not None:
                    vals = d_s.values / 100000000 if unit == "억" else d_s.values
                    fig = go.Figure()
                    fig.add_hline(y=0, line_dash="dash", line_color="white")
                    line_c = "#00e5ff" if (not is_d and vals[-1] > 0) or (is_d and vals[-1] < vals[0]) else "#ff3366"
                    fig.add_trace(go.Scatter(x=d_s.index.strftime('%Y'), y=vals, mode='lines+markers+text', text=[f"{v:,.0f}{unit}" for v in vals], textposition="top center", line=dict(color=line_c, width=3), marker=dict(size=8, color=line_c, line=dict(color='white', width=1))))
                    fig.update_layout(template="plotly_dark", height=180, margin=dict(l=10, r=10, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#30363d", zeroline=False), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

    with col_chat:
        st.markdown('<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        chat_container = st.container(height=720)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(f"<div style='font-size:1.1rem; color:white;'>{m['content']}</div>", unsafe_allow_html=True)
        if prompt := st.chat_input("위 확률의 구체적 근거를 물어보세요."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container: st.chat_message("user").write(prompt)
            if client:
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": "한국 주식 전문가입니다. 반드시 한국어로만 답변하세요."}] + st.session_state.messages[-5:], temperature=0.1)
                st.session_state.messages.append({"role": "assistant", "content": res.choices[0].message.content})
            st.rerun()