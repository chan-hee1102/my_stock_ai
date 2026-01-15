# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import yfinance as yf # 주가 데이터를 가져오기 위해 추가
from groq import Groq
from datetime import datetime, timedelta

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (블랙 & 민트 테마 유지)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 25px; border: 1px solid #30363d;
    }
    .section-header { 
        color: #00e5ff !important; font-size: 1.5rem !important; font-weight: 800; 
        margin-bottom: 25px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }
    .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 1.8rem !important; font-weight: 800 !important;
        text-align: left !important; padding: 10px 0px !important; transition: 0.3s;
    }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(5px); }
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 25px; margin-bottom: 20px; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드 및 종목 리스트 구성
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

if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

def get_groq_client():
    key = st.secrets.get("GROQ_API_KEY")
    return Groq(api_key=key) if key else None

client = get_groq_client()

# 4) 메인 레이아웃
if data is not None:
    col_list, col_chat = st.columns([2, 8])

    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 종목</div>', unsafe_allow_html=True)
        with st.container(height=850):
            for i, (idx, row) in enumerate(data.iterrows()):
                is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                if st.button(f"▶ {row['종목명']}" if is_selected else f"  {row['종목명']}", key=f"nav_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.session_state.messages = []
                    st.rerun()

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} AI 정밀 리포트</div>', unsafe_allow_html=True)
        
        # --- 시각화 한계를 넘는 차트 섹션 추가 ---
        with st.expander("📊 실시간 주가 차트 보기 (3개월)", expanded=True):
            try:
                # 한국 종목은 .KS(코스피) 또는 .KQ(코스닥)를 붙여야 합니다. 
                # 여기서는 편의상 코스피(.KS)를 기본으로 예시를 듭니다.
                ticker = stock.get('종목코드', '005930') + ".KS"
                df_chart = yf.download(ticker, start=(datetime.now() - timedelta(days=90)), end=datetime.now())
                if not df_chart.empty:
                    # 찬희님의 민트색(#00e5ff)을 차트에 반영하기 위한 설정
                    st.line_chart(df_chart['Close'], color="#00e5ff")
                else:
                    st.info("차트 데이터를 불러올 수 없습니다. (해외 주식인 경우 코드를 확인해 주세요)")
            except Exception as e:
                st.write("차트 로딩 오류")

        # 채팅 출력
        chat_container = st.container(height=500)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.1rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        if prompt := st.chat_input(f"{stock['종목명']} 분석 의뢰..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"): st.write(prompt)

            if client:
                with st.status("🚀 분석 리포트 생성 중...", expanded=True) as status:
                    try:
                        history = [{"role": "system", "content": "당신은 주식 전문가입니다. 한국어로 답변하되 주식 용어는 영어로 적절히 섞으세요. 답변 시 텍스트로 차트를 그리지 말고 설명에 집중하세요."}]
                        for m in st.session_state.messages[-5:]:
                            history.append({"role": m["role"], "content": m["content"]})
                        
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=history,
                            temperature=0.6,
                        )
                        ans = response.choices[0].message.content
                        with chat_container:
                            with st.chat_message("assistant"): st.write(ans)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                        status.update(label="✅ 분석 완료", state="complete")
                    except Exception as e:
                        st.error(f"오류: {str(e)}")
            st.rerun()