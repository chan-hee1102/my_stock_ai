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
import pandas_ta as ta
import joblib

# 1) 페이지 설정 및 세션 초기화
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2) 디자인 CSS (찬희님 디자인 100% 유지 및 분석 배지 추가)
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
    
    /* 분석 근거 배지 스타일 */
    .reason-badge {{
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 10px;
        padding: 12px 18px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;
    }}
    .reason-label {{ color: #8b949e; font-size: 0.9rem; font-weight: 600; }}
    .reason-value {{ color: #ffffff; font-size: 1.0rem; font-weight: 700; }}
    .reason-desc {{ color: #00e5ff; font-size: 0.85rem; font-weight: 700; }}

    div[data-testid="stChatInput"] {{ background-color: #ffffff !important; border-radius: 12px !important; margin-top: 10px !important; }}
    footer {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)

# 3) 기능 함수
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, "날짜 미정"
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, "날짜 미정"
    latest_file = sorted(files)[-1]
    
    # 파일명에서 날짜 추출 (final_result_20260116.csv -> 2026-01-16)
    date_part = latest_file.split("_")[-1].replace(".csv", "")
    formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
    
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "시장" in df.columns:
        df["시장"] = df["시장"].astype(str).str.strip()
        df.loc[df["시장"].str.contains("유가|KOSPI", na=False), "시장"] = "KOSPI"
        df.loc[df["시장"].str.contains("코스닥|KOSDAQ", na=False), "시장"] = "KOSDAQ"
    if "종목코드" in df.columns: df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df, formatted_date

# AI 분석 근거 생성 함수
def analyze_with_reasons(df):
    try:
        if not os.path.exists("stock_model.pkl"): return 50, "분석 중", []
        model = joblib.load("stock_model.pkl")
        
        # 지표 계산
        df['rsi'] = ta.rsi(df['Close'], length=14)
        bb = ta.bbands(df['Close'], length=20, std=2)
        l_col = [c for c in bb.columns if 'BBL' in c][0]
        u_col = [c for c in bb.columns if 'BBU' in c][0]
        df['bb_per'] = (df['Close'] - bb[l_col]) / (bb[u_col] - bb[l_col])
        ma5, ma20 = ta.sma(df['Close'], length=5), ta.sma(df['Close'], length=20)
        df['ma_diff'] = (ma5 - ma20) / ma20
        df['vol_ratio'] = df['Volume'] / df['Volume'].shift(1)
        
        last = df.iloc[-1]
        prob = model.predict_proba(df[['rsi', 'bb_per', 'ma_diff', 'vol_ratio']].tail(1))[0][1] * 100
        
        reasons = [
            {"label": "심리 지표 (RSI)", "val": f"{round(float(last['rsi']), 1)}", "desc": "과열" if last['rsi'] > 70 else "바닥권" if last['rsi'] < 30 else "안정"},
            {"label": "가격 위치 (BB %B)", "val": f"{round(float(last['bb_per']), 2)}", "desc": "상단 돌파" if last['bb_per'] > 0.8 else "하단 지지" if last['bb_per'] < 0.2 else "안정"},
            {"label": "이평 이격 (MA)", "val": f"{round(float(last['ma_diff'])*100, 1)}%", "desc": "상승 추세" if last['ma_diff'] > 0 else "하락 추세"},
            {"label": "수급 변화 (VOL)", "val": f"{round(float(last['vol_ratio']), 1)}배", "desc": "거래량 폭발" if last['vol_ratio'] > 2 else "평이"}
        ]
        return round(prob, 1), "분석 완료", reasons
    except: return 50, "대기", []

# 4) 메인 대시보드
data, data_date = load_data()
if data is not None:
    if st.session_state.selected_stock is None: st.session_state.selected_stock = data.iloc[0].to_dict()

    col_list, col_main, col_chat = st.columns([2, 5, 3])

    with col_list:
        # [변경] 동적 날짜 표시 반영
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 리스트</div>', unsafe_allow_html=True)
        with st.container(height=800):
            for m_name in ["KOSPI", "KOSDAQ"]:
                m_df = data[data["시장"] == m_name]
                st.markdown(f'<div class="market-header">{m_name} ({len(m_df)}개)</div>', unsafe_allow_html=True)
                for i, row in m_df.iterrows():
                    if st.button(f"● {row['종목명']}" if st.session_state.selected_stock['종목명'] == row['종목명'] else f"  {row['종목명']}", key=f"btn_{m_name}_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.rerun()

    with col_main:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">📈 {stock["종목명"]}</div>', unsafe_allow_html=True)
        
        # 차트 영역
        ticker = stock['종목코드'] + (".KS" if stock['시장'] == "KOSPI" else ".KQ")
        hist = yf.download(ticker, period="3mo", interval="1d", progress=False)
        fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], increasing_line_color='#ff3366', decreasing_line_color='#00e5ff')])
        fig.update_layout(template="plotly_dark", height=320, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # [변경] 확률 및 분석 근거 시각화
        prob, status, reasons = analyze_with_reasons(hist)
        st.markdown('<div class="section-header" style="margin-top:30px;">🎯 AI 정밀 분석 리포트</div>', unsafe_allow_html=True)
        
        p_col, r_col = st.columns([4, 6])
        with p_col:
            st.markdown(f"""
                <div style="background-color:#161b22; border:1px dashed #00e5ff; border-radius:12px; height:310px; display:flex; flex-direction:column; justify-content:center; align-items:center;">
                    <span style="color:#00e5ff; font-size:1.1rem; font-weight:800;">내일 상승 확률</span>
                    <div style="color:#ffffff; font-size:3.8rem; font-weight:900;">{prob}%</div>
                    <div style="color:#8b949e; font-size:0.8rem; margin-top:10px;">{status}</div>
                </div>
            """, unsafe_allow_html=True)
        with r_col:
            for r in reasons:
                st.markdown(f"""
                    <div class="reason-badge">
                        <div><div class="reason-label">{r['label']}</div><div class="reason-value">{r['val']}</div></div>
                        <div class="reason-desc">{r['desc']}</div>
                    </div>
                """, unsafe_allow_html=True)

    with col_chat:
        st.markdown('<div class="section-header">🤖 AI 비서</div>', unsafe_allow_html=True)
        # 기존 채팅 로직 유지
        st.info(f"**{data_date}** 데이터 기준으로 컨설팅합니다.")