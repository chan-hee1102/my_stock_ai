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
import pandas_ta as ta  # AI 모델 지표 계산용 추가
import joblib           # 모델 로드용 추가

# 1) 페이지 설정 및 세션 초기화
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# 실제 시스템 오늘 날짜 (기본값)
today_real_date = datetime.now().strftime('%Y-%m-%d')

# 2) 디자인 CSS (찬희님 디자인 유지 및 분석 근거 레이아웃만 추가)
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
    
    /* 분석 근거 배지 스타일 추가 */
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
    
    # [변경] 노란 동그라미 해결: 파일명에서 실제 날짜 추출
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

# [업그레이드] AI 모델 예측 및 근거 생성 함수
def calculate_ai_probability(df):
    try:
        if not os.path.exists("stock_model.pkl"):
            return 50, "학습 모델(.pkl) 없음", []
        
        model = joblib.load("stock_model.pkl")
        
        # 지표 계산
        df['rsi'] = ta.rsi(df['Close'], length=14)
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None:
            l_col = [c for c in bb.columns if 'BBL' in c][0]
            u_col = [c for c in bb.columns if 'BBU' in c][0]
            df['bb_per'] = (df['Close'] - bb[l_col]) / (bb[u_col] - bb[l_col])
        
        ma5, ma20 = ta.sma(df['Close'], length=5), ta.sma(df['Close'], length=20)
        df['ma_diff'] = (ma5 - ma20) / ma20
        df['vol_ratio'] = df['Volume'] / df['Volume'].shift(1)
        
        last = df.iloc[-1]
        last_features = df[['rsi', 'bb_per', 'ma_diff', 'vol_ratio']].tail(1)
        
        if last_features.isnull().values.any():
            return 50, "분석 데이터 준비 중", []
            
        prob = model.predict_proba(last_features)[0][1] * 100
        
        # [변경] 빨간 동그라미 해결: 분석 근거 데이터 생성
        reasons = [
            {"label": "심리 지표 (RSI)", "val": f"{round(float(last['rsi']), 1)}", "desc": "바닥권" if last['rsi'] < 35 else "과열" if last['rsi'] > 65 else "안정"},
            {"label": "가격 위치 (BB %B)", "val": f"{round(float(last['bb_per']), 2)}", "desc": "지지선" if last['bb_per'] < 0.2 else "상단돌파" if last['bb_per'] > 0.8 else "안정"},
            {"label": "이평 이격 (MA)", "val": f"{round(float(last['ma_diff'])*100, 1)}%", "desc": "정배열" if last['ma_diff'] > 0 else "역배열"},
            {"label": "수급 변화 (VOL)", "val": f"{round(float(last['vol_ratio']), 1)}배", "desc": "거래폭발" if last['vol_ratio'] > 2 else "유입중"}
        ]
        
        return round(prob, 1), "타겟 종목 특화 분석 완료", reasons
    except Exception as e:
        return 50, f"분석 대기 ({str(e)})", []

def draw_finance_chart(dates, values, unit, is_debt=False):
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="white")
    color = "#00e5ff" if not is_debt else "#ff3366"
    fig.add_trace(go.Scatter(x=dates, y=values, mode='lines+markers+text', text=[f"{v:,.0f}{unit}" for v in values], textposition="top center", line=dict(color=color, width=3), marker=dict(size=8, color=color)))
    fig.update_layout(template="plotly_dark", height=180, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"))
    return fig

# 4) 메인 로직 실행
data, data_date = load_data() # [변경] 파일 날짜 변수 추가
groq_api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=groq_api_key) if groq_api_key else None

if data is not None:
    if st.session_state.selected_stock is None:
        st.session_state.selected_stock = data.iloc[0].to_dict()

    col_list, col_main, col_chat = st.columns([2, 5, 3])

    with col_list:
        # [변경] 노란 동그라미 해결: 파일 날짜로 제목 변경
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
        tk = yf.Ticker(ticker_sym)
        
        c1, c2 = st.columns([7, 3])
        with c1:
            try:
                hist = tk.history(period="3mo").tail(60)
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], increasing_line_color='#ff3366', decreasing_line_color='#00e5ff')])
                fig.update_layout(template="plotly_dark", height=320, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis_rangeslider_visible=False)
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

        # 🎯 [변경 핵심] 빨간 동그라미 해결: 확률과 분석 근거 병렬 배치
        prob, msg, reasons = calculate_ai_probability(hist)
        
        st.markdown('<div class="section-header" style="margin-top:30px;">🎯 AI 정밀 분석 리포트</div>', unsafe_allow_html=True)
        prob_col, reason_col = st.columns([4, 6])
        
        with prob_col:
            st.markdown(f"""
                <div style="background-color:#161b22; border:1px dashed #00e5ff; border-radius:12px; height:280px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
                    <span style="color:#00e5ff; font-size:1.1rem; font-weight:800; margin-bottom:10px;">상승 확률</span>
                    <div style="color:#ffffff; font-size:3.5rem; font-weight:900;">{prob}%</div>
                    <div style="color:#8b949e; font-size:0.8rem; margin-top:10px;">{msg}</div>
                </div>
            """, unsafe_allow_html=True)
            
        with reason_col:
            for r in reasons:
                st.markdown(f"""
                    <div class="reason-badge">
                        <div>
                            <div class="reason-label">{r['label']}</div>
                            <div class="reason-value">{r['val']}</div>
                        </div>
                        <div class="reason-desc">{r['desc']}</div>
                    </div>
                """, unsafe_allow_html=True)

    with col_chat:
        st.markdown('<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        chat_container = st.container(height=800) 
        
        with chat_container:
            with st.chat_message("assistant", avatar="🤖"):
                st.write(f"오늘 날짜는 **{data_date}**입니다. **{stock['종목명']}** 종목에 대해 궁금한 점이 있으신가요?")
            
            for m in st.session_state.messages:
                with st.chat_message(m["role"], avatar="🤖" if m["role"] == "assistant" else None):
                    st.markdown(m["content"])
        
        if prompt := st.chat_input("질문하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"): st.markdown(prompt)
                with st.chat_message("assistant", avatar="🤖"):
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile", 
                        messages=[
                            {"role": "system", "content": f"""당신은 한국의 주식 전문가입니다.
                            현재 날짜는 {data_date}입니다. 한글로만 답변하십시오."""},
                            {"role": "user", "content": f"{stock['종목명']} 관련 질문: {prompt}"}
                        ]
                    )
                    ans = res.choices[0].message.content
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})