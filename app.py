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

# 1) 페이지 설정 및 시그니처 디자인 유지 [cite: 2026-01-13]
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 20px; border: 1px solid #30363d;
        display: flex !important; flex-direction: column !important; justify-content: flex-start !important;
    }
    .section-header { 
        color: #00e5ff !important; font-size: 1.3rem !important; font-weight: 800; 
        margin-bottom: 20px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }
    .market-header {
        background-color: #0d1117; color: #8b949e; font-size: 0.8rem; font-weight: 800;
        text-align: center; padding: 6px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #30363d;
    }
    
    /* 수급 표 디자인 전용 CSS */
    .investor-table {
        width: 100%; border-collapse: collapse; font-size: 0.85rem; text-align: center; color: #ffffff;
    }
    .investor-table th { background-color: #0d1117; color: #8b949e; padding: 8px; border-bottom: 1px solid #30363d; }
    .investor-table td { padding: 8px; border-bottom: 1px solid #1c2128; font-weight: 600; }
    .val-plus { color: #ff3366; } /* 매수는 빨간색 (한국 기준) */
    .val-minus { color: #00e5ff; } /* 매도는 파란색 */

    .tactical-box { background-color: #161b22; border: 1px dashed #00e5ff; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    .grid-container { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; text-align: center; }
    .grid-item { background: #0d1117; padding: 10px; border-radius: 8px; border: 1px solid #30363d; }
    .item-label { color: #8b949e; font-size: 0.75rem; margin-bottom: 5px; }
    .item-value { color: #ffffff; font-size: 1.1rem; font-weight: 800; }
    
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# 2) 데이터 로직 및 수급 데이터 크롤링 [cite: 2026-01-15]
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

@st.cache_data(ttl=3600)
def get_investor_trend(code):
    """네이버 금융에서 투자자별 매매동향 크롤링"""
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table', {'class': 'type2'})
        
        rows = table.find_all('tr', {'onmouseover': 'mouseOver(this)'})
        data = []
        for row in rows[:6]:  # 최근 6일치
            cols = row.find_all('td')
            date = cols[0].text.strip()[5:]  # MM.DD 형식
            # 외국인/기관 순매매량 (숫자만 추출)
            foreigner = int(cols[6].text.replace(',', '').strip())
            institution = int(cols[5].text.replace(',', '').strip())
            data.append({"날짜": date, "외국인": foreigner, "기관": institution})
        return pd.DataFrame(data)
    except:
        return pd.DataFrame(columns=["날짜", "외국인", "기관"])

data, data_date = load_data()
groq_api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=groq_api_key) if groq_api_key else None

# 3) 메인 레이아웃 (3분할 사령부)
if data is not None:
    if "selected_stock" not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()
    if "messages" not in st.session_state: st.session_state.messages = []

    col_list, col_main, col_chat = st.columns([2, 5, 3])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착</div>', unsafe_allow_html=True)
        with st.container(height=800):
            for m_name in ["KOSPI", "KOSDAQ"]:
                m_df = data[data["시장"] == m_name]
                st.markdown(f'<div class="market-header">{m_name} ({len(m_df)}개)</div>', unsafe_allow_html=True)
                for i, row in m_df.iterrows():
                    is_sel = st.session_state.selected_stock['종목명'] == row['종목명']
                    if st.button(f"● {row['종목명']}" if is_sel else f"  {row['종목명']}", key=f"{m_name}_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.rerun()

    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📈 {stock["종목명"]} 전략 사령부</div>', unsafe_allow_html=True)
        
        # [신규] 차트와 수급 표를 가로로 배치
        chart_col, supply_col = st.columns([7, 3])
        
        with chart_col:
            ticker_sym = stock['종목코드'] + (".KS" if stock['시장'] == "KOSPI" else ".KQ")
            try:
                tk = yf.Ticker(ticker_sym)
                hist = tk.history(period="3mo")
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], 
                                                     increasing_line_color='#00e5ff', decreasing_line_color='#ff3366')])
                fig.update_layout(template="plotly_dark", height=320, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="#1c2128", plot_bgcolor="#1c2128", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            except: st.error("차트 로딩 실패")

        with supply_col:
            # [신규] 수급 데이터 표 시각화 (찬희님 그림 반영)
            invest_df = get_investor_trend(stock['종목코드'])
            if not invest_df.empty:
                table_html = '<table class="investor-table"><tr><th>날짜</th><th>외국인</th><th>기관</th></tr>'
                for _, row in invest_df.iterrows():
                    f_cls = "val-plus" if row['외국인'] > 0 else "val-minus"
                    i_cls = "val-plus" if row['기관'] > 0 else "val-minus"
                    table_html += f"""
                    <tr>
                        <td>{row['날짜']}</td>
                        <td class="{f_cls}">{row['외국인']:,}</td>
                        <td class="{i_cls}">{row['기관']:,}</td>
                    </tr>
                    """
                table_html += "</table>"
                st.markdown(table_html, unsafe_allow_html=True)
            else:
                st.write("수급 데이터 없음")

        # 전술 및 백테스팅 영역 (설계 기반) [cite: 2026-01-15]
        st.markdown(f"""
        <div class="tactical-box">
            <div class="section-header" style="border:none; text-align:center; font-size:1.1rem;">🛠️ AI 전략 사령부: {stock['종목명']} 판독</div>
            <div class="grid-container">
                <div class="grid-item"><div class="item-label">시장 수급</div><div class="item-value">분석중</div></div>
                <div class="grid-item"><div class="item-label">패턴 신뢰도</div><div class="item-value signal-mint">85%</div></div>
                <div class="grid-item"><div class="item-label">익일 예상</div><div class="item-value">준비완료</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 재무 차트 등 하단부 생략(기존 유지)

    with col_chat:
        st.markdown('<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        # 채팅 로직 생략(기존 유지)