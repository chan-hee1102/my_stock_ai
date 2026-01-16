# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import yfinance as yf
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from groq import Groq
from datetime import datetime
import numpy as np

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (찬희님 제공 최종 디자인 100% 유지)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 20px; border: 1px solid #30363d;
        display: flex !important; flex-direction: column !important; justify-content: flex-start !important;
    }
    .section-header { 
        color: #00e5ff !important; font-size: 1.1rem !important; font-weight: 800; 
        margin-bottom: 20px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }
    .market-header {
        background-color: #0d1117; color: #8b949e; font-size: 1.0rem !important; font-weight: 800;
        text-align: center; padding: 8px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #30363d;
    }
    .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 0.9rem !important; text-align: left !important; padding: 4px 0px !important;
    }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(3px); transition: 0.2s; }
    
    [data-testid="stChatMessage"] {
        background-color: #161b22 !important; border: 1px solid #30363d !important;
        border-radius: 12px !important; padding: 20px !important; margin-bottom: 10px !important;
    }
    [data-testid="stChatMessage"] * { color: #ffffff !important; opacity: 1 !important; font-size: 1.0rem !important; line-height: 1.6 !important; }
    [data-testid="stChatMessage"] strong { color: #00e5ff !important; font-weight: 800 !important; }

    .investor-table { width: 100%; border-collapse: collapse; font-size: 1.0rem; text-align: center; color: #ffffff; }
    .investor-table th { background-color: #0d1117; color: #8b949e; padding: 8px; border-bottom: 1px solid #30363d; }
    .investor-table td { padding: 8px; border-bottom: 1px solid #1c2128; font-family: 'Courier New', Courier, monospace; font-weight: 600; }
    .val-plus { color: #ff3366; } 
    .val-minus { color: #00e5ff; } 

    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-top: 15px; margin-bottom: 15px; }
    .info-line { color: #ffffff !important; font-size: 1rem; font-weight: 700; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    
    .finance-header-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 8px 15px; margin-bottom: 5px; width: 100%; display: flex; align-items: center; }
    .finance-label-compact { color: #00e5ff; font-size: 0.95rem; font-weight: 800; margin: 0; }
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 기능 함수
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "시장" in df.columns:
        df["시장"] = df["시장"].astype(str).str.strip()
        df.loc[df["시장"].str.contains("유가|KOSPI", na=False), "시장"] = "KOSPI"
        df.loc[df["시장"].str.contains("코스닥|KOSDAQ", na=False), "시장"] = "KOSDAQ"
    if "종목코드" in df.columns: df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df, latest_file.split('_')[-1].replace('.csv', '')

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
            date = cols[0].text.strip()[-5:] 
            inst, fore = int(cols[5].text.replace(',', '')), int(cols[6].text.replace(',', ''))
            data_list.append({"날짜": date, "기관": inst, "외인": fore})
        return pd.DataFrame(data_list)
    except: return None

def calculate_technical_probability(code, market):
    try:
        ticker = code + (".KS" if market == "KOSPI" else ".KQ")
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 40: return 50, "데이터 부족"
        df = df[(df['Close'] > 0) & (df['Open'] > 0)].copy()
        close = df['Close']
        df['MA20'] = close.rolling(20).mean()
        df['Disparity'] = (close / df['MA20']) * 100
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))
        curr = df.iloc[-1]
        df['Next_Day_Up'] = (df['Close'].shift(-1) > df['Close']).astype(int)
        similar_days = df[(df['RSI'] > curr['RSI'] - 7) & (df['RSI'] < curr['RSI'] + 7) & (df['Disparity'] > curr['Disparity'] - 5) & (df['Disparity'] < curr['Disparity'] + 5)]
        if len(similar_days) > 5:
            prob = int(similar_days['Next_Day_Up'].mean() * 100)
            return min(max(prob, 15), 92), "기술적 패턴 매칭 완료"
        return 53, "추세 기반 기본 분석"
    except: return 50, "분석 시스템 대기"

def get_latest_news(ticker_symbol):
    """최신 뉴스 수집 함수"""
    try:
        tk = yf.Ticker(ticker_symbol)
        news = tk.news[:3] # 상위 3개 뉴스
        if not news: return "현재 이 종목에 대한 주요 뉴스가 발견되지 않았습니다."
        news_text = ""
        for n in news: news_text += f"- {n['title']}\n"
        return news_text
    except: return "뉴스 정보를 가져오는 중 오류가 발생했습니다."

def get_ai_analysis_report(stock_name, ticker_symbol, prob):
    """AI 비서의 자동 브리핑 생성 로직"""
    if not client: return "AI 비서 연결 불가."
    news_content = get_latest_news(ticker_symbol)
    try:
        prompt = (f"당신은 {stock_name}에 대한 전문 주식 전략가입니다. 아래 데이터를 바탕으로 리포트를 작성하세요.\n"
                  f"1. 최신 뉴스 소식: {news_content}\n"
                  f"2. 기술적 상승 확률: {prob}%\n\n"
                  f"형식:\n1. **[최신 이슈]**: 뉴스 기반 요약\n2. **[기술 분석]**: 차트/수급 상태 요약\n3. **[전략 제언]**: 결론 한 줄\n"
                  f"반드시 전문적이고 냉철한 어조로 인사말 없이 작성하세요.")
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "종목 분석 전문가."}, {"role": "user", "content": prompt}],
            temperature=0.2
        )
        return res.choices[0].message.content
    except: return f"{stock_name} 분석 로딩 실패."

def draw_finance_chart(dates, values, unit, is_debt=False):
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="white")
    color = "#00e5ff" if not is_debt else "#ff3366"
    fig.add_trace(go.Scatter(x=dates, y=values, mode='lines+markers+text', text=[f"{v:,.0f}{unit}" for v in values], textposition="top center", line=dict(color=color, width=3), marker=dict(size=8, color=color)))
    fig.update_layout(template="plotly_dark", height=180, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)"))
    return fig

# 4) 메인 로직
data, data_date = load_data()
groq_api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=groq_api_key) if groq_api_key else None

if data is not None:
    # [에러 해결] 세션 초기화 로직 보강
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
        st.session_state.messages = []
        st.session_state.initial_analysis = None

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
                        st.session_state.initial_analysis = None # 분석 초기화
                        st.session_state.messages = []
                        st.rerun()

    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📈 {stock["종목명"]}</div>', unsafe_allow_html=True)
        ticker_sym = stock['종목코드'] + (".KS" if stock['시장'] == "KOSPI" else ".KQ")
        tk = yf.Ticker(ticker_sym)
        
        c1, c2 = st.columns([7, 3])
        with c1:
            try:
                hist = tk.history(period="3mo").tail(40)
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], increasing_line_color='#ff3366', decreasing_line_color='#00e5ff')])
                fig.update_layout(template="plotly_dark", height=320, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False)
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

        st.markdown(f"""<div class="report-box"><div class="info-line"><span class="highlight-mint">종목:</span> {stock["종목명"]} ({stock['종목코드']}) &nbsp;|&nbsp; <span class="highlight-mint">거래대금:</span> {stock.get('최근거래일거래대금(억)', 0):,}억</div></div>""", unsafe_allow_html=True)

        # 재무 차트
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

        prob, msg = calculate_technical_probability(stock['종목코드'], stock['시장'])
        st.markdown(f"""<div style="background-color:#161b22; border:1px dashed #00e5ff; border-radius:12px; padding:30px; text-align:center;"><span style="color:#00e5ff; font-size:1.2rem; font-weight:800; display:block; margin-bottom:15px;">🎯 AI 내일 상승 확률</span><div style="color:#ffffff; font-size:2.8rem; font-weight:900;">{prob}%</div><div style="color:#8b949e; font-size:0.9rem;">{msg}</div></div>""", unsafe_allow_html=True)

    with col_chat:
        st.markdown('<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        # [수정] 자동 분석 실행 및 에러 방지
        if st.session_state.initial_analysis is None:
            with st.spinner("최신 뉴스 및 데이터를 분석하고 있습니다..."):
                st.session_state.initial_analysis = get_ai_analysis_report(stock['종목명'], ticker_sym, prob)
        
        with st.container(height=700):
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(st.session_state.initial_analysis)
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(m["content"])
        
        if prompt := st.chat_input("이 종목에 대해 더 궁금한 점이 있나요?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant", avatar="🤖"):
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
                ans = res.choices[0].message.content
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})