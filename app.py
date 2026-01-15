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

# 2) 디자인 CSS (임찬희님 시그니처 디자인 완벽 유지)
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
        background-color: #0d1117; color: #8b949e; font-size: 0.95rem !important; font-weight: 800;
        text-align: center; padding: 8px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #30363d;
    }
    .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 0.9rem !important; text-align: left !important; padding: 4px 0px !important;
    }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(3px); transition: 0.2s; }
    
    /* 채팅창 선명도 및 가독성 고정 */
    [data-testid="stChatMessage"] {
        background-color: #161b22 !important; 
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        padding: 15px !important;
        margin-bottom: 10px !important;
    }
    [data-testid="stChatMessage"] * { color: #ffffff !important; opacity: 1 !important; font-size: 1.0rem !important; }
    [data-testid="stChatMessage"] strong { color: #00e5ff !important; }

    /* 뉴스 박스 전용 디자인 */
    .news-card {
        background-color: #0d1117; border-left: 4px solid #00e5ff;
        padding: 15px; margin-bottom: 10px; border-radius: 4px;
    }
    .news-title { color: #ffffff; font-weight: 700; font-size: 0.95rem; margin-bottom: 5px; }
    .news-reason { color: #00e5ff; font-weight: 800; font-size: 0.85rem; }

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

def get_official_news_analysis(stock_name, code):
    """AI가 노이즈를 제거하고 핵심 오피셜 뉴스만 추출"""
    if not client: return []
    try:
        # 네이버 금융 뉴스 헤드라인 수집
        url = f"https://finance.naver.com/item/news_news.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        titles = [t.text.strip() for t in soup.select('.title a')[:15]]
        
        # AI에게 중복 제거 및 필터링 요청
        prompt = (f"{stock_name} 종목의 최근 뉴스 헤드라인 목록입니다: {titles}\n\n"
                  f"위 뉴스 중 다음 조건에 맞는 핵심 뉴스 3개만 엄선하세요:\n"
                  f"1. '10% 상승', '급등' 같은 단순 시세 뉴스는 무조건 제외할 것.\n"
                  f"2. 계약, 수주, 합병, 인수, 신제품, 실적 등 기업의 '실질적 이슈'만 포함할 것.\n"
                  f"3. 중복된 내용은 최신 오피셜 정보 1개로 통합할 것.\n"
                  f"4. 각 뉴스마다 '결론적으로 이 이슈 때문에 움직인다'는 [핵심 원인]을 한 문장으로 작성할 것.\n"
                  f"형식: 뉴스제목 | 핵심원인")
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "사족 없이 뉴스제목 | 핵심원인 형식으로만 3개 답변하세요."}],
            prompt=prompt, temperature=0.1
        )
        lines = res_ai.choices[0].message.content.strip().split('\n')
        final_news = []
        for line in lines:
            if '|' in line:
                t, r = line.split('|')
                final_news.append({"title": t.strip(), "reason": r.strip()})
        return final_news
    except: return []

def get_ai_expert_analysis(stock_name):
    if not client: return "AI 비서 연결 불가."
    try:
        prompt = (f"{stock_name} 종목에 대해 불필요한 사족(조심해라 등) 없이 [차트], [수급], [이슈] 핵심만 요약 보고하세요.")
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "팩트 위주 요약 보고 전문가. 인사말/경고문 생략."}],
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
                hist = tk.history(period="3mo").tail(40)
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

        # 1. 재무 차트 상단 배치
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

        # 2. [신규] 핵심 뉴스 리포트 하단 배치 (상승확률 대체) [cite: 2026-01-16]
        st.markdown('<div class="section-header">🗞️ AI 실전 핵심 뉴스 리포트</div>', unsafe_allow_html=True)
        news_list = get_official_news_analysis(stock['종목명'], stock['종목코드'])
        if news_list:
            for n in news_list:
                st.markdown(f"""
                <div class="news-card">
                    <div class="news-title">📍 {n['title']}</div>
                    <div class="news-reason">💡 핵심 요약: {n['reason']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("현재 분석할 만한 중대한 기업 공시 및 뉴스가 없습니다.")

    with col_chat:
        st.markdown('<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        with st.container(height=720):
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(m["content"])
        if prompt := st.chat_input("질문하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": "주식 전문가. 핵심 요약 위주 대답."}] + st.session_state.messages)
                full_res = res.choices[0].message.content
                st.markdown(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})