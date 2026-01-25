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

today_real_date = datetime.now().strftime('%Y-%m-%d')
warnings.filterwarnings("ignore")
logging.getLogger("lightgbm").setLevel(logging.ERROR)

def clean_foreign_languages(text):
    pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\u31f0-\u31ff]')
    return pattern.sub('', text)

# 2) [FINDA STYLE] 모던 다크 테크 디자인 적용
st.markdown(f"""
    <style>
    /* 전체 배경: 딥 다크 네이비 */
    .stApp {{ 
        background-color: #0B0E11; 
    }}
    
    /* 카드 디자인: 글래스모피즘 (유리 질감) */
    [data-testid="stHorizontalBlock"] > div {{
        background: rgba(23, 28, 36, 0.7) !important;
        backdrop-filter: blur(12px);
        border-radius: 20px !important;
        padding: 25px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
        display: flex !important; flex-direction: column !important; justify-content: flex-start !important;
    }}

    /* 섹션 헤더: 네온 그린 포인트 및 글로우 효과 */
    .section-header {{ 
        color: #00FFA3 !important; font-size: 1.2rem !important; font-weight: 800; 
        margin-bottom: 25px; border-left: 5px solid #00FFA3; padding-left: 15px; 
        text-shadow: 0 0 10px rgba(0, 255, 163, 0.3);
    }}

    /* 시장 구분 헤더 */
    .market-header {{
        background-color: rgba(13, 17, 23, 0.6); color: #8b949e; font-size: 1.0rem !important; font-weight: 800;
        text-align: center; padding: 10px; border-radius: 12px; margin-bottom: 15px; border: 1px solid rgba(255, 255, 255, 0.05);
    }}

    /* 종목 리스트 버튼: 호버 시 발광 효과 */
    .stButton > button {{
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 0.95rem !important; text-align: left !important; padding: 6px 0px !important;
        transition: all 0.3s ease;
    }}
    .stButton > button:hover {{ 
        color: #00FFA3 !important; transform: translateX(5px); 
        text-shadow: 0 0 8px rgba(0, 255, 163, 0.5);
    }}
    
    /* 채팅 메시지 디자인 */
    [data-testid="stChatMessage"] {{
        background-color: rgba(22, 27, 34, 0.8) !important; border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 15px !important; padding: 20px !important; margin-bottom: 12px !important;
    }}

    /* 투자자 표 디자인 */
    .investor-table {{ width: 100%; border-collapse: collapse; font-size: 1.0rem; text-align: center; color: #ffffff; }}
    .investor-table th {{ background-color: rgba(13, 17, 23, 0.8); color: #8b949e; padding: 10px; border-bottom: 1px solid #30363d; }}
    .investor-table td {{ padding: 10px; border-bottom: 1px solid rgba(255, 255, 255, 0.02); font-family: 'JetBrains Mono', monospace; }}
    .val-plus {{ color: #FF3366; text-shadow: 0 0 5px rgba(255, 51, 102, 0.2); }} 
    .val-minus {{ color: #00FFA3; text-shadow: 0 0 5px rgba(0, 255, 163, 0.2); }} 

    /* 리포트 박스 및 정보 라인 */
    .report-box {{ 
        background: linear-gradient(145deg, #171c24, #0b0e11);
        border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 15px; padding: 20px; margin: 20px 0; 
    }}
    .highlight-mint {{ color: #00FFA3 !important; font-weight: 800; }}
    
    /* AI 확률 박스: 네온 글로우 포인트 */
    .probability-card {{
        background: rgba(11, 14, 17, 0.6) !important;
        border: 1px solid #00FFA3 !important;
        box-shadow: 0 0 20px rgba(0, 255, 163, 0.15) !important;
        border-radius: 20px !important;
        height: 280px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;
    }}

    /* 검색창 디자인 */
    div[data-testid="stChatInput"] {{ 
        background-color: #ffffff !important; border-radius: 15px !important; padding: 5px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# 3) 기능 함수 (로직 동일)
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

@st.cache_data(ttl=3600)
def get_macro_data():
    try:
        end = datetime.now()
        start = end - timedelta(days=30)
        tickers = ["^IXIC", "^VIX", "DX-Y.NYB", "^TNX", "GC=F", "NQ=F"]
        macro = yf.download(tickers, start=start, end=end, progress=False)['Close'].ffill()
        macro.index = macro.index.tz_localize(None)
        last = macro.iloc[-1]
        n_ret = macro["^IXIC"].pct_change().iloc[-1]
        v_cls = last["^VIX"]
        d_ret = macro["DX-Y.NYB"].pct_change().iloc[-1]
        t_cls = last["^TNX"]
        g_ret = macro["GC=F"].pct_change().iloc[-1]
        nf_ret = macro["NQ=F"].pct_change().iloc[-1]
        return n_ret, v_cls, d_ret, t_cls, g_ret, nf_ret
    except: return 0.0, 15.0, 0.0, 4.0, 0.0, 0.0

def calculate_ai_probability(df, market_df):
    try:
        if not os.path.exists("stock_model.pkl"): return 50.0, "모델 파일 미발견", []
        model = joblib.load("stock_model.pkl")
        df.index = df.index.tz_localize(None)
        df['rsi'] = ta.rsi(df['Close'], length=14)
        bb = ta.bbands(df['Close'], length=20, std=2)
        l_col, u_col = [c for c in bb.columns if 'BBL' in c][0], [c for c in bb.columns if 'BBU' in c][0]
        df['bb_per'] = (df['Close'] - bb[l_col]) / (bb[u_col] - bb[l_col])
        df['ma_diff'] = (ta.sma(df['Close'], 5) - ta.sma(df['Close'], 20)) / ta.sma(df['Close'], 20)
        vol_up = (df['Volume'] > df['Volume'].shift(1)).astype(int)
        df['vol_consecutive_days'] = vol_up.groupby((vol_up != vol_up.shift()).cumsum()).cumsum()
        df['vol_spike_ratio'] = df['Volume'] / ta.sma(df['Volume'], 20)
        df['candle_body'] = (df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-9)
        m_series = market_df.squeeze()
        if isinstance(m_series, pd.DataFrame): m_series = m_series.iloc[:, 0]
        m_series.index = m_series.index.tz_localize(None)
        m_series.name = "market_close"
        df = df.join(m_series, how='left').ffill()
        df['relative_strength'] = df['Close'].pct_change(5) - df['market_close'].pct_change(5)
        df['macd_hist'] = ta.macd(df['Close'])['MACDh_12_26_9']
        df['mfi'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        df['atr_ratio'] = ta.atr(df['High'], df['Low'], df['Close'], length=14) / df['Close']
        df['stoch_k'] = ta.stoch(df['High'], df['Low'], df['Close'])['STOCHk_14_3_3']
        df['disparity_60'] = (df['Close'] / ta.sma(df['Close'], 60)) * 100
        df['price_range'] = (df['High'] - df['Low']) / df['Close']
        df['vol_roc'] = ta.roc(df['Volume'], length=5)
        df['range_roc'] = ta.roc(df['price_range'], length=5) 
        df['day_of_week'] = df.index.dayofweek
        n_ret, v_cls, d_ret, t_cls, g_ret, nf_ret = get_macro_data()
        df['nasdaq_return'], df['vix_close'], df['dxy_return'] = n_ret, v_cls, d_ret
        df['tnx_close'], df['gold_return'], df['nasdaq_f_return'] = t_cls, g_ret, nf_ret
        feature_cols = [
            'rsi', 'bb_per', 'ma_diff', 'vol_consecutive_days', 'vol_spike_ratio', 
            'candle_body', 'relative_strength', 'macd_hist', 'mfi', 'atr_ratio',
            'stoch_k', 'disparity_60', 'price_range', 'vol_roc', 'range_roc',
            'day_of_week', 'nasdaq_return', 'vix_close', 'dxy_return', 'tnx_close', 
            'gold_return', 'nasdaq_f_return'
        ]
        last_features = df[feature_cols].tail(1).fillna(0)
        prob = model.predict_proba(last_features)[0][1] * 100
        last = df.iloc[-1]
        reasons = [
            {"label": "나스닥 선물", "val": f"{nf_ret*100:.2f}%", "desc": "호조" if nf_ret > 0 else "불안"},
            {"label": "상대강도 (RS)", "val": f"{round(float(last['relative_strength'])*100, 1)}%", "desc": "시장 주도" if last['relative_strength'] > 0 else "하회"},
            {"label": "에너지 가속도", "val": f"{round(float(last['range_roc']), 1)}%", "desc": "가속화" if last['range_roc'] > 0 else "수렴"},
            {"label": "VIX 공포지수", "val": f"{v_cls:.1f}", "desc": "안정" if v_cls < 18 else "주의"}
        ]
        return round(prob, 1), "v1.7 분석 엔진 정상 작동 중", reasons
    except Exception as e: return 50.0, f"분석 대기 중 ({str(e)})", []

def draw_finance_chart(dates, values, unit, is_debt=False):
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    color = "#00FFA3" if not is_debt else "#FF3366"
    fig.add_trace(go.Scatter(x=dates, y=values, mode='lines+markers+text', text=[f"{v:,.0f}{unit}" for v in values], textposition="top center", line=dict(color=color, width=3), marker=dict(size=10, color=color, line=dict(width=2, color='white'))))
    fig.update_layout(template="plotly_dark", height=200, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"))
    return fig

# 4) 메인 실행
data, data_date = load_data()
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()
client = Groq(api_key=groq_api_key) if groq_api_key and len(groq_api_key) > 10 else None

if data is not None:
    if st.session_state.selected_stock is None:
        st.session_state.selected_stock = data.iloc[0].to_dict()

    col_list, col_main, col_chat = st.columns([2.2, 5, 2.8])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 리스트</div>', unsafe_allow_html=True)
        with st.container(height=800):
            for m_name in ["KOSPI", "KOSDAQ"]:
                m_df = data[data["시장"] == m_name]
                st.markdown(f'<div class="market-header">{m_name} ({len(m_df)}개)</div>', unsafe_allow_html=True)
                for i, row in m_df.iterrows():
                    is_sel = st.session_state.selected_stock['종목명'] == row['종목명']
                    label = f"● {row['종목명']}" if is_sel else f"  {row['종목명']}"
                    if st.button(label, key=f"btn_{m_name}_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.rerun()

    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📈 {stock["종목명"]} ({stock["종목코드"]})</div>', unsafe_allow_html=True)
        ticker_sym = stock['종목코드'] + (".KS" if stock['시장'] == "KOSPI" else ".KQ")
        market_idx = "^KS11" if stock['시장'] == "KOSPI" else "^KQ11"
        tk = yf.Ticker(ticker_sym)
        
        c1, c2 = st.columns([7, 3])
        with c1:
            try:
                hist = tk.history(period="6mo")
                if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
                m_hist = yf.download(market_idx, period="6mo", progress=False)['Close']
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], increasing_line_color='#FF3366', decreasing_line_color='#00FFA3')])
                fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_rangeslider_visible=False, xaxis=dict(tickformat='%m.%d', gridcolor='rgba(255,255,255,0.05)'), yaxis=dict(tickformat=',d', gridcolor='rgba(255,255,255,0.05)'))
                st.plotly_chart(fig, use_container_width=True)
            except: st.error("데이터 로드 실패")
        
        with c2:
            inv = get_investor_trend(stock['종목코드'])
            if inv is not None:
                html = '<table class="investor-table"><tr><th>날짜</th><th>외인</th><th>기관</th></tr>'
                for _, r in inv.iterrows():
                    f_cls, i_cls = ("val-plus" if r['외인'] > 0 else "val-minus"), ("val-plus" if r['기관'] > 0 else "val-minus")
                    html += f'<tr><td>{r["날짜"]}</td><td class="{f_cls}">{r["외인"]:,}</td><td class="{i_cls}">{r["기관"]:,}</td></tr>'
                st.markdown(html + '</table>', unsafe_allow_html=True)

        st.markdown(f'<div class="report-box"><div class="info-line"><span class="highlight-mint">분석 대상:</span> {stock["종목명"]} | <span class="highlight-mint">당일 거래대금:</span> {stock.get("최근거래일거래대금(억)", 0):,}억</div></div>', unsafe_allow_html=True)

        f1, f2 = st.columns(2)
        try:
            income = tk.financials.loc['Operating Income'].sort_index() / 1e8
            debt = (tk.balance_sheet.loc['Total Debt'] / tk.balance_sheet.loc['Stockholders Equity'] * 100).sort_index()
            with f1:
                st.markdown('<div class="market-header">💰 연간 영업이익 (억원)</div>', unsafe_allow_html=True)
                st.plotly_chart(draw_finance_chart(income.index.year, income.values, "억"), use_container_width=True)
            with f2:
                st.markdown('<div class="market-header">📉 분기 부채비율 (%)</div>', unsafe_allow_html=True)
                st.plotly_chart(draw_finance_chart(debt.index.year, debt.values, "%", is_debt=True), use_container_width=True)
        except: pass

        # AI 예측 섹션
        prob, msg, reasons = calculate_ai_probability(hist, m_hist)
        st.markdown('<div class="section-header" style="margin-top:35px;">🚀 AI PREDICTIVE STRATEGY</div>', unsafe_allow_html=True)
        prob_col, reason_col = st.columns([4.5, 5.5])
        with prob_col:
            st.markdown(f"""
                <div class="probability-card">
                    <span style="color:#00FFA3; font-size:1.1rem; font-weight:800; margin-bottom:15px;">익일 상승 모멘텀</span>
                    <div style="color:#ffffff; font-size:4rem; font-weight:900; text-shadow: 0 0 20px rgba(0, 255, 163, 0.4);">{prob}%</div>
                    <div style="color:#8b949e; font-size:0.85rem; margin-top:15px;">{msg}</div>
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
        st.markdown('<div class="section-header">🤖 AI STRATEGY AGENT</div>', unsafe_allow_html=True)
        chat_container = st.container(height=800)
        with chat_container:
            if not st.session_state.messages and client:
                with st.spinner("전문가 분석 엔진 가동 중..."):
                    auto_prompt = f"전문가로서 {today_real_date} 기준 {stock['종목명']}의 투자 전략을 상세히 설명해줘. 한자 사용 금지."
                    try:
                        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": auto_prompt}])
                        ans = clean_foreign_languages(res.choices[0].message.content)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                    except: pass
            for m in st.session_state.messages:
                with st.chat_message(m["role"], avatar="🤖" if m["role"] == "assistant" else None):
                    st.markdown(m["content"], unsafe_allow_html=True)
        if prompt := st.chat_input("질문을 입력하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()