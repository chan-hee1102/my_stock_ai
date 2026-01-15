# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import requests
import yfinance as yf
import plotly.graph_objects as go
from bs4 import BeautifulSoup
from groq import Groq
from datetime import datetime, timedelta

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (재무 차트 상단 강제 밀착 및 3분할 통합 레이아웃)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 카드 디자인: 수직 정렬을 상단(flex-start)으로 강제 고정 */
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
    
    /* [긴급수정] 재무 카드 영역: 뉴스 유무와 상관없이 차트가 위로 붙도록 설정 */
    .finance-card-fixed {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px;
        padding: 15px 15px 5px 15px; margin-top: 10px; min-height: 500px;
        display: flex; flex-direction: column; justify-content: flex-start; /* 상단 정렬 강제 */
    }
    .finance-label-fixed { color: #00e5ff; font-size: 1.1rem; font-weight: 800; margin-bottom: 10px; }

    /* 뉴스 컨테이너 스타일 */
    .news-container { margin-bottom: 10px; padding: 10px; background: #161b22; border-radius: 8px; border-left: 3px solid #00e5ff; width: 100%; }
    .news-title { color: #ffffff !important; font-size: 0.85rem; font-weight: 600; text-decoration: none !important; display: block; line-height: 1.4; }
    .news-title:hover { color: #00e5ff !important; }

    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드 및 유틸리티
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

def get_stock_brief(stock_name):
    if not client: return "AI 분석관 연결 실패"
    try:
        prompt = (f"당신은 주식 전략가입니다. {stock_name}의 최근 상승 이슈를 분석하여 "
                  f"'최근 [구체적 이슈]로 인한 [테마명] 테마에 속해서 상승 중입니다' 형식으로 한 문장 브리핑하세요.")
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return res.choices[0].message.content
    except: return "분석 업데이트 중..."

# [강력 수정] 뉴스 스크래핑 엔진: User-Agent 보강 및 타임아웃 추가
def get_ai_news(stock_code):
    try:
        url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}"
        # 브라우저인 척 하기 위한 헤더 보강
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'https://finance.naver.com/item/main.naver?code={stock_code}'
        }
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        news_data = []
        titles = soup.select('.title a')
        for t in titles[:10]:
            title_text = t.text.strip()
            # 단순 시황 중계 뉴스 1차 필터링
            if any(x in title_text for x in ["상승", "하락", "등락", "특징주", "게시판"]): continue
            news_data.append({"title": title_text, "link": "https://finance.naver.com" + t['href']})
        
        # AI로 2차 정밀 필터링
        if news_data and client:
            titles_combined = "\n".join([f"{i}: {n['title']}" for i, n in enumerate(news_data)])
            filter_prompt = (f"다음 뉴스 중 신사업, 수주, M&A 등 핵심 기업 가치 변화와 관련된 뉴스 3개의 번호만 답하세요.\n{titles_combined}")
            filter_res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": filter_prompt}])
            indices = [int(i.strip()) for i in filter_res.choices[0].message.content.split(',') if i.strip().isdigit()]
            return [news_data[i] for i in indices if i < len(news_data)]
        return news_data[:3]
    except Exception as e:
        print(f"News error: {e}")
        return []

# [완결 수정] 여백을 완전히 제거하여 차트를 상단으로 끌어올리는 함수
def draw_pro_finance_chart(dates, values, unit, is_debt=False):
    display_values = values / 100000000 if "억" in unit else values
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=1.5)
    
    line_color = "#00e5ff" if (not is_debt and display_values[-1] > 0) or (is_debt and display_values[-1] < display_values[0]) else "#ff3366"
    
    fig.add_trace(go.Scatter(
        x=dates, y=display_values, mode='lines+markers+text',
        text=[f"{v:,.0f}{unit}" for v in display_values],
        textposition="top center", textfont=dict(color="white", size=10),
        line=dict(color=line_color, width=4), marker=dict(size=10, color=line_color)
    ))
    fig.update_layout(
        template="plotly_dark", height=280, 
        margin=dict(l=10, r=10, t=10, b=10), # [핵심] 상단 마진을 10으로 최소화
        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#30363d", zeroline=False),
        showlegend=False
    )
    return fig

# 4) 메인 레이아웃 및 세션 관리
if data is not None:
    if "messages" not in st.session_state: st.session_state.messages = []
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
        st.session_state.current_brief = get_stock_brief(data.iloc[0]['종목명'])
        st.session_state.current_news = get_ai_news(data.iloc[0]['종목코드'])

    col_list, col_main, col_chat = st.columns([2, 5, 3])

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
                            with st.spinner("분석관이 이슈 파악 중..."):
                                st.session_state.current_brief = get_stock_brief(row['종목명'])
                                st.session_state.current_news = get_ai_news(row['종목코드'])
                            st.rerun()

    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📈 {stock["종목명"]} 전략 분석실</div>', unsafe_allow_html=True)
        
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

        # 테마 브리핑 박스
        st.markdown(f"""
        <div class="report-box">
            <div class="info-line">
                <span class="highlight-mint">종목:</span> {stock["종목명"]} ({stock['종목코드']}) &nbsp;|&nbsp; 
                <span class="highlight-mint">시장:</span> {stock['시장']} &nbsp;|&nbsp; 
                <span class="highlight-mint">거래대금:</span> {stock.get('거래대금(억)', 0):,}억
            </div>
            <div class="theme-line">
                <span class="highlight-mint">🤖 AI 비서 테마 브리핑:</span> {st.session_state.get('current_brief', '뉴스 이슈 분석 중...')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # [완결 수정] 뉴스 피드를 상단에 배치하고 차트를 위로 바짝 붙임
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.markdown('<div class="finance-card-fixed"><div class="finance-label-fixed">💰 연간 영업이익 추이</div>', unsafe_allow_html=True)
            # 뉴스 피드 표시 섹션
            news_items = st.session_state.get('current_news', [])
            if news_items:
                for news in news_items:
                    st.markdown(f'<div class="news-container"><a href="{news["link"]}" target="_blank" class="news-title">● {news["title"]}</a></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="news-container" style="border-left:3px solid #ff3366;"><span style="color:#8b949e; font-size:0.8rem;">최신 핵심 뉴스가 없습니다.</span></div>', unsafe_allow_html=True)
            
            if income is not None: st.plotly_chart(draw_pro_finance_chart(income.index.strftime('%Y'), income.values, "억"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with f_col2:
            st.markdown('<div class="finance-card-fixed"><div class="finance-label-fixed">📉 연간 부채비율 추이</div>', unsafe_allow_html=True)
            if debt is not None: st.plotly_chart(draw_pro_finance_chart(debt.index.strftime('%Y'), debt.values, "%", is_debt=True), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with col_chat:
        st.markdown(f'<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        chat_container = st.container(height=720)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(f"<div style='font-size:1.1rem; color:white;'>{m['content']}</div>", unsafe_allow_html=True)
        
        if prompt := st.chat_input("AI 비서에게 구체적인 분석을 요청하세요."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"): st.write(prompt)
            if client:
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": f"당신은 {stock['종목명']} 전문 AI 비서입니다."}] + st.session_state.messages[-5:])
                ans = res.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": ans})
            st.rerun()