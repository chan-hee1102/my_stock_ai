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

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (임찬희님 시그니처 디자인 보존)
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
        border-radius: 12px !important; padding: 15px !important; margin-bottom: 10px !important;
    }
    [data-testid="stChatMessage"] * {
        color: #ffffff !important; opacity: 1 !important; font-size: 1.0rem !important; line-height: 1.6 !important;
    }
    [data-testid="stChatMessage"] strong { color: #00e5ff !important; font-weight: 800 !important; }

    .investor-table {
        width: 100%; border-collapse: collapse; font-size: 1.0rem; text-align: center; color: #ffffff;
    }
    .investor-table th { background-color: #0d1117; color: #8b949e; padding: 8px; border-bottom: 1px solid #30363d; }
    .investor-table td { padding: 8px; border-bottom: 1px solid #1c2128; font-family: 'Courier New', Courier, monospace; font-weight: 600; }
    .val-plus { color: #ff3366; } 
    .val-minus { color: #00e5ff; } 

    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-top: 15px; margin-bottom: 15px; }
    .info-line { color: #ffffff !important; font-size: 1rem; font-weight: 700; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    
    .finance-header-box {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px;
        padding: 8px 15px; margin-bottom: 5px; width: 100%;
        display: flex; align-items: center;
    }
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
    if "종목코드" in df.columns:
        df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
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
            inst = int(cols[5].text.replace(',', '').strip())
            fore = int(cols[6].text.replace(',', '').strip())
            data_list.append({"날짜": date, "기관": inst, "외인": fore})
        return pd.DataFrame(data_list) if data_list else None
    except Exception: return None

def get_ai_expert_analysis(stock_name):
    if not client: return "AI 분석 대기 중."
    try:
        prompt = (f"당신은 주식 시장 전략가입니다. {stock_name} 종목에 대해 불필요한 인사말이나 투자 경고 없이 "
                  f"[차트 흐름], [수급 상태]를 중심으로 핵심만 전문가답게 요약 보고하세요.")
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "팩트 중심 요약 보고 모드."}],
            prompt=prompt, temperature=0.2
        )
        return res.choices[0].message.content
    except: return f"{stock_name} 분석 오류."

def draw_finance_chart(dates, values, unit, is_debt=False):
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="white")
    color = "#00e5ff" if not is_debt else "#ff3366"
    fig.add_trace(go.Scatter(x=dates, y=values, mode='lines+markers+text',
                             text=[f"{v:,.0f}{unit}" for v in values], textposition="top center",
                             line=dict(color=color, width=3), marker=dict(size=8, color=color, symbol='circle')))
    fig.update_layout(template="plotly_dark", height=200, margin=dict(l=10, r=10, t=30, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(showgrid=False, dtick=1), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)"))
    return fig

# 4) 메인 로직
data, data_date = load_data()
groq_api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=groq_api_key) if groq_api_key else None

if data is not None:
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
        st.session_state.messages = [{"role": "assistant", "content": get_ai_expert_analysis(data.iloc[0]['종목명'])}]
    
    col_list, col_main, col_chat = st.columns([2, 5, 3])

    with col_list:
        d_obj = datetime.strptime(data_date, "%Y%m%d")
        week_days = ["월", "화", "수", "목", "금", "토", "일"]
        sidebar_title = f"📂 {d_obj.strftime('%Y-%m-%d')} ({week_days[d_obj.weekday()]}) 포착 리스트"
        st.markdown(f'<div class="section-header">{sidebar_title}</div>', unsafe_allow_html=True)
        with st.container(height=800):
            for m_name in ["KOSPI", "KOSDAQ"]:
                m_df = data[data["시장"] == m_name]
                st.markdown(f'<div class="market-header">{m_name} ({len(m_df)}개)</div>', unsafe_allow_html=True)
                for i, row in m_df.iterrows():
                    is_sel = st.session_state.selected_stock['종목명'] == row['종목명']
                    if st.button(f"● {row['종목명']}" if is_sel else f"  {row['종목명']}", key=f"{m_name}_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = [{"role": "assistant", "content": get_ai_expert_analysis(row['종목명'])}]
                        st.rerun()

    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📈 {stock["종목명"]}</div>', unsafe_allow_html=True)
        
        chart_col, supply_col = st.columns([7, 3])
        with chart_col:
            ticker = stock['종목코드'] + (".KS" if stock['시장'] == "KOSPI" else ".KQ")
            try:
                tk = yf.Ticker(ticker)
                hist_raw = tk.history(period="3mo")
                # [오류 해결] 종가가 0인 불완전한 데이터 필터링
                hist = hist_raw[hist_raw['Close'] > 0].tail(40)
                
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], 
                                                     increasing_line_color='#ff3366', decreasing_line_color='#00e5ff')])
                fig.update_layout(template="plotly_dark", height=320, margin=dict(l=0, r=0, t=0, b=0), 
                                  paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis_rangeslider_visible=False,
                                  yaxis=dict(tickformat=",d", tickfont=dict(size=13, color='#ffffff', family="Arial"), gridcolor='rgba(255,255,255,0.07)'),
                                  xaxis=dict(tickformat="%m.%d", tickfont=dict(size=13, color='#ffffff', family="Arial"), gridcolor='rgba(255,255,255,0.07)'))
                st.plotly_chart(fig, use_container_width=True)
            except: st.error("차트 로드 실패")

        with supply_col:
            invest_df = get_investor_trend(stock['종목코드'])
            if invest_df is not None and not invest_df.empty:
                html_code = '<table class="investor-table"><tr><th>날짜</th><th>외인</th><th>기관</th></tr>'
                for _, r in invest_df.iterrows():
                    f_cls = "val-plus" if r['외인'] > 0 else "val-minus"
                    i_cls = "val-plus" if r['기관'] > 0 else "val-minus"
                    html_code += f'<tr><td>{r["날짜"]}</td><td class="{f_cls}">{r["외인"]:,}</td><td class="{i_cls}">{r["기관"]:,}</td></tr>'
                html_code += "</table>"
                st.markdown(html_code, unsafe_allow_html=True)

        st.markdown(f"""<div class="report-box"><div class="info-line"><span class="highlight-mint">종목:</span> {stock["종목명"]} ({stock['종목코드']}) &nbsp;|&nbsp; <span class="highlight-mint">시장:</span> {stock['시장']} &nbsp;|&nbsp; <span class="highlight-mint">거래대금:</span> {stock.get('최근거래일거래대금(억)', 0):,}억</div></div>""", unsafe_allow_html=True)

        # 재무 차트 상단 배치 유지
        f_col1, f_col2 = st.columns(2)
        try:
            income = tk.financials.loc['Operating Income'].sort_index() / 1e8
            debt = (tk.balance_sheet.loc['Total Debt'] / tk.balance_sheet.loc['Stockholders Equity'] * 100).sort_index()
            with f_col1:
                st.markdown('<div class="finance-header-box"><span class="finance-label-compact">💰 연간 영업이익 (억)</span></div>', unsafe_allow_html=True)
                if income is not None: st.plotly_chart(draw_finance_chart(income.index.year, income.values, "억"), use_container_width=True)
            with f_col2:
                st.markdown('<div class="finance-header-box"><span class="finance-label-compact">📉 연간 부채비율 (%)</span></div>', unsafe_allow_html=True)
                if debt is not None: st.plotly_chart(draw_finance_chart(debt.index.year, debt.values, "%", is_debt=True), use_container_width=True)
        except: pass

        # 상승 확률 박스 하단 배치 (뉴스 취소 반영)
        st.markdown('<div style="background-color:#161b22; border:1px dashed #00e5ff; border-radius:12px; padding:30px; margin-bottom:20px; text-align:center;"><span style="color:#00e5ff; font-size:1.2rem; font-weight:800; margin-bottom:15px; display:block;">🎯 AI 내일 상승 확률</span><div style="color:#ffffff; font-size:1.1rem; font-weight:600;">데이터 산출 시스템 대기 중...</div></div>', unsafe_allow_html=True)

    with col_chat:
        st.markdown('<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        with st.container(height=720):
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(m["content"])
        if prompt := st.chat_input("질문하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": "핵심만 요약 보고."}] + st.session_state.messages)
                full_res = res.choices[0].message.content
                st.markdown(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})