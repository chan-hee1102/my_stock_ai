# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
from groq import Groq
from datetime import datetime, timedelta

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (임찬희님 시그니처 디자인 + 확률 박스 고도화)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 20px; border: 1px solid #30363d;
        display: flex !important; flex-direction: column !important; justify-content: flex-start !important;
    }
    .section-header { color: #00e5ff !important; font-size: 1.3rem !important; font-weight: 800; margin-bottom: 20px; border-left: 6px solid #00e5ff; padding-left: 15px; }
    .market-header { background-color: #0d1117; color: #8b949e; font-size: 0.8rem; font-weight: 800; text-align: center; padding: 6px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #30363d; }
    .stButton > button { width: 100% !important; background-color: transparent !important; color: #ffffff !important; border: none !important; font-size: 0.9rem !important; text-align: left !important; padding: 4px 0px !important; }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(3px); transition: 0.2s; }
    
    /* 테마 및 분석 박스 스타일 */
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-top: 15px; margin-bottom: 15px; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    
    /* 통합 분석 영역 (가운데 웅장한 확률 박스) */
    .wide-analysis-box {
        background-color: #161b22; border: 1px dashed #00e5ff; border-radius: 12px;
        padding: 30px; margin-bottom: 20px; text-align: center; min-height: 260px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }
    .prob-value { font-size: 4rem; font-weight: 900; color: #00e5ff; text-shadow: 0 0 30px rgba(0,229,255,0.5); margin: 5px 0; }
    .prob-desc { color: #ffffff; font-size: 1.1rem; font-weight: 600; line-height: 1.5; margin-top: 10px; }

    /* 재무제표 헤더 박스 */
    .finance-header-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px 15px; margin-bottom: 5px; width: 100%; display: flex; align-items: center; }
    .finance-label-compact { color: #00e5ff; font-size: 0.95rem; font-weight: 800; margin: 0; }
    .finance-card-compact { background-color: transparent; padding: 0px; margin-top: 5px; min-height: auto !important; display: flex !important; flex-direction: column !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 정밀 백테스팅 & AI 확률 계산 엔진
def get_rise_probability_ai(ticker_symbol, stock_name):
    try:
        # 1. 과거 2년 데이터 수집
        df = yf.download(ticker_symbol, period="2y", interval="1d", progress=False)
        if len(df) < 50: return 50, "데이터 부족으로 기본 분석 수행"

        # 2. 기술적 지표 계산 (간단한 AI 피처 엔지니어링)
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['Price_Change'] = df['Close'].pct_change()
        df['Vol_MA'] = df['Volume'].rolling(window=20).mean()
        
        # 3. 찬희님 로직(급등 포착) 시뮬레이션: 거래량 2배 이상 & 주가 상승일
        signals = df[(df['Volume'] > df['Vol_MA'] * 2) & (df['Price_Change'] > 0.02)]
        
        success_count = 0
        for i in range(len(signals)):
            try:
                current_idx = df.index.get_loc(signals.index[i])
                if current_idx + 1 < len(df):
                    next_day_change = df.iloc[current_idx + 1]['Close'] - df.iloc[current_idx]['Close']
                    if next_day_change > 0: success_count += 1
            except: continue
        
        hit_rate = (success_count / len(signals) * 100) if len(signals) > 0 else 50
        
        # 4. 최종 확률을 AI(Groq)에게 판단 요청 (하이브리드 방식)
        if client:
            current_price = df['Close'].iloc[-1]
            last_change = df['Price_Change'].iloc[-1] * 100
            prompt = (f"종목: {stock_name}\n"
                      f"과거 2년간 동일 조건 포착 횟수: {len(signals)}회\n"
                      f"포착 후 익일 상승 적중 횟수: {success_count}회\n"
                      f"현재가: {current_price:,.0f}원 (전일 대비 {last_change:.2f}%)\n"
                      f"위 통계 데이터를 바탕으로 내일 주가가 상승할 확률(%)을 숫자만 먼저 대답하고, "
                      f"한 줄의 핵심 근거를 한국어로 덧붙이세요.")
            
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "주식 데이터 분석 전문가입니다. 반드시 한국어로만 답변하세요."},
                          {"role": "user", "content": prompt}],
                temperature=0.1
            )
            ai_ans = res.choices[0].message.content
            # 확률 숫자 추출 및 설명 분리
            prob_val = "".join(filter(str.isdigit, ai_ans.split('\n')[0]))[:2]
            prob_val = int(prob_val) if prob_val else int(hit_rate)
            desc = ai_ans.split('\n')[-1]
            return prob_val, desc
        
        return int(hit_rate), f"과거 {len(signals)}회 포착 중 {success_count}회 적중"
    except:
        return 50, "차트 모멘텀 분석 중"

# 4) 데이터 로드 및 앱 레이아웃
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

if data is not None:
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
        st.session_state.messages = []
        with st.spinner("AI 사령부 초기화 중..."):
            ticker = st.session_state.selected_stock['종목코드'] + (".KS" if "KOSPI" in st.session_state.selected_stock['시장'] else ".KQ")
            prob, desc = get_rise_probability_ai(ticker, st.session_state.selected_stock['종목명'])
            st.session_state.prob, st.session_state.prob_desc = prob, desc

    col_list, col_main, col_chat = st.columns([2, 5, 3])

    # [1] 왼쪽 리스트
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
                            with st.spinner("예측 엔진 계산 중..."):
                                ticker = row['종목코드'] + (".KS" if "KOSPI" in row['시장'] else ".KQ")
                                prob, desc = get_rise_probability_ai(ticker, row['종목명'])
                                st.session_state.prob, st.session_state.prob_desc = prob, desc
                            st.rerun()

    # [2] 가운데 분석실
    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📈 {stock["종목명"]} 전략 사령부</div>', unsafe_allow_html=True)
        
        # 캔들 차트
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

        # [핵심] 통합 분석 영역: AI 백테스팅 확률 표시
        st.markdown(f"""
        <div class="wide-analysis-box">
            <span class="analysis-title">🎯 AI 익일 상승 확률 분석 리포트</span>
            <div class="prob-value">{st.session_state.prob}%</div>
            <div class="prob-desc">
                {st.session_state.prob_desc}<br>
                <span style="color: #8b949e; font-size: 0.85rem;">※ 과거 2년 데이터 기반 기술적 패턴 및 AI 추론 결과</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 재무제표 (헤더 박스 디자인)
        f_col1, f_col2 = st.columns(2)
        for col, title, d_s, unit, is_d in [(f_col1, "💰 연간 영업이익 추이", income, "억", False), (f_col2, "📉 연간 부채비율 추이", debt, "%", True)]:
            with col:
                st.markdown(f'<div class="finance-card-compact"><div class="finance-header-box"><span class="finance-label-compact">{title}</span></div>', unsafe_allow_html=True)
                if d_s is not None:
                    vals = d_s.values / 100000000 if unit == "억" else d_s.values
                    fig = go.Figure()
                    fig.add_hline(y=0, line_dash="dash", line_color="white")
                    color = "#00e5ff" if (not is_d and vals[-1] > 0) or (is_d and vals[-1] < vals[0]) else "#ff3366"
                    fig.add_trace(go.Scatter(x=d_s.index.strftime('%Y'), y=vals, mode='lines+markers+text', text=[f"{v:,.0f}{unit}" for v in vals], textposition="top center", line=dict(color=color, width=3), marker=dict(size=8, color=color)))
                    fig.update_layout(template="plotly_dark", height=200, margin=dict(l=10, r=10, t=0, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#30363d", zeroline=False), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # [3] 오른쪽 AI 비서
    with col_chat:
        st.markdown('<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        chat_container = st.container(height=720)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(f"<div style='font-size:1.1rem; color:white;'>{m['content']}</div>", unsafe_allow_html=True)
        if prompt := st.chat_input("위 분석 확률의 근거를 물어보세요."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container: st.chat_message("user").write(prompt)
            if client:
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": "한국 주식 전문가입니다. 반드시 한국어로만 자연스럽게 답변하세요."}] + st.session_state.messages[-5:])
                st.session_state.messages.append({"role": "assistant", "content": res.choices[0].message.content})
            st.rerun()