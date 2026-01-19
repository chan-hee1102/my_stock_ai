# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from groq import Groq
from datetime import datetime, timedelta
import os
import warnings
import logging
import joblib
import re
import numpy as np

# 1) 페이지 설정 및 세션 초기화
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# 접속 시점의 실제 오늘 날짜 (2026-01-19)
today_real_date = datetime.now().strftime('%Y-%m-%d')

# 워닝 차단 및 로그 제어
warnings.filterwarnings("ignore")
logging.getLogger("lightgbm").setLevel(logging.ERROR)

# [전문가 기능] 외국어 필터
def clean_foreign_languages(text):
    pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\u31f0-\u31ff]')
    return pattern.sub('', text)

# 2) 디자인 CSS (사용자 디자인 100% 유지)
st.markdown(f"""
    <style>
    .stApp {{ background-color: #05070a; }}
    [data-testid="stHorizontalBlock"] > div {{
        background-color: #1c2128; border-radius: 15px; padding: 20px; border: 1px solid #30363d;
        display: flex !important; flex-direction: column !important; justify-content: flex-start !important;
    }}
    .section-header {{ 
        color: #00e5ff !important; font-size: 1.1rem !important; font-weight: 800; 
        margin-bottom: 20px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }}
    .market-header {{
        background-color: #0d1117; color: #8b949e; font-size: 1.0rem !important; font-weight: 800;
        text-align: center; padding: 8px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #30363d;
    }}
    .stButton > button {{
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 0.9rem !important; text-align: left !important; padding: 4px 0px !important;
    }}
    .stButton > button:hover {{ color: #00e5ff !important; transform: translateX(3px); transition: 0.2s; }}
    
    [data-testid="stChatMessage"] {{
        background-color: #161b22 !important; border: 1px solid #30363d !important;
        border-radius: 12px !important; padding: 20px !important; margin-bottom: 10px !important;
    }}
    [data-testid="stChatMessage"] * {{ color: #ffffff !important; opacity: 1 !important; font-size: 1.0rem !important; line-height: 1.6 !important; }}

    .investor-table {{ width: 100%; border-collapse: collapse; font-size: 1.0rem; text-align: center; color: #ffffff; }}
    .investor-table th {{ background-color: #0d1117; color: #8b949e; padding: 8px; border-bottom: 1px solid #30363d; }}
    .investor-table td {{ padding: 8px; border-bottom: 1px solid #1c2128; font-family: 'Courier New', Courier, monospace; font-weight: 600; }}
    .val-plus {{ color: #ff3366; }} 
    .val-minus {{ color: #00e5ff; }} 

    .report-box {{ background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-top: 15px; margin-bottom: 15px; }}
    .info-line {{ color: #ffffff !important; font-size: 1rem; font-weight: 700; }}
    .highlight-mint {{ color: #00e5ff !important; font-weight: 800; }}
    
    .finance-header-box {{ background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px 15px; margin-bottom: 5px; width: 100%; display: flex; align-items: center; }}
    .finance-label-compact {{ color: #00e5ff; font-size: 0.95rem; font-weight: 800; margin: 0; }}
    
    .reason-badge {{
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px;
        padding: 10px 15px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;
    }}
    .reason-label {{ color: #8b949e; font-size: 0.85rem; }}
    .reason-value {{ color: #ffffff; font-size: 0.9rem; font-weight: 700; }}
    .reason-desc {{ color: #00e5ff; font-size: 0.85rem; font-weight: 700; }}

    div[data-testid="stChatInput"] {{ 
        background-color: #ffffff !important; 
        border-radius: 12px !important; 
        padding: 0 !important; 
        margin-top: 10px !important;
    }}
    .block-container {{ padding-bottom: 1rem !important; }}
    footer {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)

# 3) 기능 함수 정의
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, None
    latest_file = sorted(files)[-1]
    date_str = latest_file.split("_")[-1].replace(".csv", "")
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "시장" in df.columns:
        df["시장"] = df["시장"].astype(str).str.strip()
        df.loc[df["시장"].str.contains("유가|KOSPI", na=False), "시장"] = "KOSPI"
        df.loc[df["시장"].str.contains("코스닥|KOSDAQ", na=False), "시장"] = "KOSDAQ"
    if "종목코드" in df.columns: df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df, formatted_date

@st.cache_data(ttl=1800)
def get_investor_trend(code):
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all('tr', {'onmouseover': 'mouseOver(this)'})
        data_list = []
        for row in rows[:5]:
            cols = row.find_all('td')
            if len(cols) < 9: continue
            date, inst, fore = cols[0].text.strip()[-5:], int(cols[5].text.replace(',', '')), int(cols[6].text.replace(',', ''))
            data_list.append({"날짜": date, "기관": inst, "외인": fore})
        return pd.DataFrame(data_list)
    except: return None

# [v1.7] 실시간 매크로 지표 수집 (나스닥 선물 포함)
@st.cache_data(ttl=3600)
def get_macro_data():
    try:
        end = datetime.now()
        start = end - timedelta(days=20)
        tickers = ["^IXIC", "^VIX", "DX-Y.NYB", "^TNX", "GC=F", "NQ=F"]
        macro = yf.download(tickers, start=start, end=end, progress=False)['Close'].ffill()
        
        last = macro.iloc[-1]
        n_ret = macro["^IXIC"].pct_change().iloc[-1]
        v_cls = last["^VIX"]
        d_ret = macro["DX-Y.NYB"].pct_change().iloc[-1]
        t_cls = last["^TNX"]
        g_ret = macro["GC=F"].pct_change().iloc[-1]
        nf_ret = macro["NQ=F"].pct_change().iloc[-1]
        return n_ret, v_cls, d_ret, t_cls, g_ret, nf_ret
    except: return 0.0, 15.0, 0.0, 4.0, 0.0, 0.0

# [엔진 수리] v1.7 모델 22개 피처 계산 (4개 피처 에러 해결)
def calculate_ai_probability(df, market_df):
    try:
        if not os.path.exists("stock_model.pkl"): return 50.0, "모델 파일 누락", []
        model = joblib.load("stock_model.pkl")
        
        # 1. 기술적 지표 (v1.7 훈련 데이터와 100% 동일)
        df['rsi'] = ta.rsi(df['Close'], length=14)
        bb = ta.bbands(df['Close'], length=20, std=2)
        l_col, u_col = [c for c in bb.columns if 'BBL' in c][0], [c for c in bb.columns if 'BBU' in c][0]
        df['bb_per'] = (df['Close'] - bb[l_col]) / (bb[u_col] - bb[l_col])
        df['ma_diff'] = (ta.sma(df['Close'], 5) - ta.sma(df['Close'], 20)) / ta.sma(df['Close'], 20)
        vol_up = (df['Volume'] > df['Volume'].shift(1)).astype(int)
        df['vol_consecutive_days'] = vol_up.groupby((vol_up != vol_up.shift()).cumsum()).cumsum()
        df['vol_spike_ratio'] = df['Volume'] / ta.sma(df['Volume'], 20)
        df['candle_body'] = (df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-9)
        
        df = df.join(market_df.rename("market_close"), how='left')
        df['relative_strength'] = df['Close'].pct_change(5) - df['market_close'].pct_change(5)
        
        df['macd_hist'] = ta.macd(df['Close'])['MACDh_12_26_9']
        df['mfi'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        df['atr_ratio'] = ta.atr(df['High'], df['Low'], df['Close'], length=14) / df['Close']
        df['stoch_k'] = ta.stoch(df['High'], df['Low'], df['Close'])['STOCHk_14_3_3']
        df['disparity_60'] = (df['Close'] / ta.sma(df['Close'], 60)) * 100
        df['price_range'] = (df['High'] - df['Low']) / df['Close']
        df['vol_roc'] = ta.roc(df['Volume'], length=5)
        df['range_roc'] = ta.roc(df['price_range'], length=5) # v1.7 신규
        df['day_of_week'] = df.index.dayofweek
        
        # 2. 매크로 데이터 병합
        n_ret, v_cls, d_ret, t_cls, g_ret, nf_ret = get_macro_data()
        df['nasdaq_return'], df['vix_close'], df['dxy_return'] = n_ret, v_cls, d_ret
        df['tnx_close'], df['gold_return'], df['nasdaq_f_return'] = t_cls, g_ret, nf_ret
        
        # 3. 모델 피처 정렬
        feature_cols = [
            'rsi', 'bb_per', 'ma_diff', 'vol_consecutive_days', 'vol_spike_ratio', 
            'candle_body', 'relative_strength', 'macd_hist', 'mfi', 'atr_ratio',
            'stoch_k', 'disparity_60', 'price_range', 'vol_roc', 'range_roc',
            'day_of_week', 'nasdaq_return', 'vix_close', 'dxy_return', 'tnx_close', 
            'gold_return', 'nasdaq_f_return'
        ]
        
        last_features = df[feature_cols].tail(1)
        if last_features.isnull().values.any(): return 50.0, "데이터 수집 대기", []
        
        prob = model.predict_proba(last_features)[0][1] * 100
        last = df.iloc[-1]
        
        reasons = [
            {"label": "나스닥 선물", "val": f"{nf_ret*100:.2f}%", "desc": "호조" if nf_ret > 0 else "약세"},
            {"label": "VIX 공포지수", "val": f"{v_cls:.1f}", "desc": "안정" if v_cls < 18 else "주의"},
            {"label": "상대강도 (RS)", "val": f"{round(float(last['relative_strength'])*100, 1)}%", "desc": "주도주" if last['relative_strength'] > 0 else "하회"},
            {"label": "에너지 가속도", "val": f"{round(float(last['range_roc']), 1)}%", "desc": "폭발적" if last['range_roc'] > 0 else "수렴"}
        ]
        return round(prob, 1), "v1.7 초고도화 엔진 정상 작동 중", reasons
    except Exception as e: return 50.0, f"엔진 오류 ({str(e)})", []

def draw_finance_chart(dates, values, unit, is_debt=False):
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="white")
    color = "#00e5ff" if not is_debt else "#ff3366"
    fig.add_trace(go.Scatter(x=dates, y=values, mode='lines+markers+text', text=[f"{v:,.0f}{unit}" for v in values], textposition="top center", line=dict(color=color, width=3), marker=dict(size=8, color=color)))
    fig.update_layout(template="plotly_dark", height=180, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"))
    return fig

# 4) 메인 로직 실행
data, data_date = load_data()
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()
client = Groq(api_key=groq_api_key) if groq_api_key and len(groq_api_key) > 10 else None

if data is not None:
    if st.session_state.selected_stock is None:
        st.session_state.selected_stock = data.iloc[0].to_dict()

    col_list, col_main, col_chat = st.columns([2, 5, 3])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 리스트</div>', unsafe_allow_html=True)
        with st.container(height=800):
            for m_name in ["KOSPI", "KOSDAQ"]:
                m_df = data[data["시장"] == m_name]
                st.markdown(f'<div class="market-header">{m_name} ({len(m_df)}개)</div>', unsafe_allow_html=True)
                for i, row in m_df.iterrows():
                    is_sel = st.session_state.selected_stock['종목명'] == row['종목명']
                    if st.button(f"● {row['종목명']}" if is_sel else f"  {row['종목명']}", key=f"btn_{m_name}_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.rerun()

    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📈 {stock["종목명"]}</div>', unsafe_allow_html=True)
        ticker_sym = stock['종목코드'] + (".KS" if stock['시장'] == "KOSPI" else ".KQ")
        market_idx = "^KS11" if stock['시장'] == "KOSPI" else "^KQ11"
        tk = yf.Ticker(ticker_sym)
        c1, c2 = st.columns([7, 3])
        with c1:
            try:
                hist = tk.history(period="6mo").tail(100)
                m_hist = yf.download(market_idx, period="6mo", progress=False)['Close'].tail(100)
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], increasing_line_color='#ff3366', decreasing_line_color='#00e5ff')])
                
                # [디자인 고정] 흰 선 투명도 낮게, 날짜 숫자, 가격 콤마 표시
                fig.update_layout(
                    template="plotly_dark", height=320, margin=dict(l=0, r=0, t=0, b=0), 
                    paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis_rangeslider_visible=False,
                    xaxis=dict(tickformat='%m.%d', gridcolor='rgba(255,255,255,0.05)', tickfont=dict(size=12, color='#ffffff')),
                    yaxis=dict(tickformat=',d', gridcolor='rgba(255,255,255,0.05)', tickfont=dict(size=12, color='#ffffff'))
                )
                st.plotly_chart(fig, use_container_width=True)
            except: st.error("차트 로드 실패")
        with c2:
            inv = get_investor_trend(stock['종목코드'])
            if inv is not None:
                html = '<table class="investor-table"><tr><th>날짜</th><th>외인</th><th>기관</th></tr>'
                for _, r in inv.iterrows():
                    f_cls, i_cls = ("val-plus" if r['외인'] > 0 else "val-minus"), ("val-plus" if r['기관'] > 0 else "val-minus")
                    html += f'<tr><td>{r["날짜"]}</td><td class="{f_cls}">{r["외인"]:,}</td><td class="{i_cls}">{r["기관"]:,}</td></tr>'
                st.markdown(html + '</table>', unsafe_allow_html=True)

        st.markdown(f"""<div class="report-box"><div class="info-line"><span class="highlight-mint">종목:</span> {stock["종목명"]} ({stock['종목코드']}) | <span class="highlight-mint">거래대금:</span> {stock.get('최근거래일거래대금(억)', 0):,}억</div></div>""", unsafe_allow_html=True)

        f1, f2 = st.columns(2)
        try:
            income = tk.financials.loc['Operating Income'].sort_index() / 1e8
            debt = (tk.balance_sheet.loc['Total Debt'] / tk.balance_sheet.loc['Stockholders Equity'] * 100).sort_index()
            with f1:
                st.markdown('<div class="finance-header-box"><span class="finance-label-compact">💰 영업이익 (억)</span></div>', unsafe_allow_html=True)
                st.plotly_chart(draw_finance_chart(income.index.year, income.values, "억"), use_container_width=True)
            with f2:
                st.markdown('<div class="finance-header-box"><span class="finance-label-compact">📉 부채비율 (%)</span></div>', unsafe_allow_html=True)
                st.plotly_chart(draw_finance_chart(debt.index.year, debt.values, "%", is_debt=True), use_container_width=True)
        except: pass

        # [상승 확률 연동] v1.7 65.25% 모델 적용
        prob, msg, reasons = calculate_ai_probability(hist, m_hist)
        st.markdown('<div class="section-header" style="margin-top:30px;">🚀 AI PREDICTIVE STRATEGY: 5개년 데이터 모델링 기반 익일 기대수익 확률</div>', unsafe_allow_html=True)
        prob_col, reason_col = st.columns([4, 6])
        with prob_col:
            # 60% 이상이면 주도주 빨간 테두리
            bar_border = "#ff3366" if prob > 60 else "#00e5ff"
            st.markdown(f"""
                <div style="background-color:#161b22; border:1px dashed {bar_border}; border-radius:12px; height:280px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
                    <span style="color:{bar_border}; font-size:1.1rem; font-weight:800; margin-bottom:10px;">상승 모멘텀(Momentum)</span>
                    <div style="color:#ffffff; font-size:3.5rem; font-weight:900;">{prob}%</div>
                    <div style="color:#8b949e; font-size:0.8rem; margin-top:10px;">{msg}</div>
                </div>
            """, unsafe_allow_html=True)
        with reason_col:
            for r in reasons:
                st.markdown(f"""
                    <div class="reason-badge">
                        <div><div class="reason-label">{r['label']}</div><div class="reason-value">{r['val']}</div></div>
                        <div class="reason-desc">{r['desc']}</div>
                    </div>
                """, unsafe_allow_html=True)

    with col_chat:
        st.markdown('<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        chat_container = st.container(height=800)
        with chat_container:
            if not st.session_state.messages and client:
                with st.spinner("전문가 분석 중..."):
                    auto_prompt = f"전문가로서 {today_real_date} 기준 {stock['종목명']}의 분석과 전략을 설명해줘."
                    try:
                        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": auto_prompt}])
                        ans = clean_foreign_languages(res.choices[0].message.content)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                    except: pass
            for m in st.session_state.messages:
                with st.chat_message(m["role"], avatar="🤖" if m["role"] == "assistant" else None):
                    st.markdown(m["content"], unsafe_allow_html=True)
        if prompt := st.chat_input("전략을 질문하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()