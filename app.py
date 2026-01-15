# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from groq import Groq
from datetime import datetime

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (임찬희님의 시그니처 블랙 & 민트 디자인)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 25px; border: 1px solid #30363d;
    }
    .section-header { 
        color: #00e5ff !important; font-size: 1.4rem !important; font-weight: 800; 
        margin-bottom: 20px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }
    .market-header {
        background-color: #0d1117; color: #8b949e; font-size: 0.85rem; font-weight: 800;
        text-align: center; padding: 6px; border-radius: 8px; margin-bottom: 12px;
        border: 1px solid #30363d; letter-spacing: 0.5px;
    }
    .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 0.95rem !important; font-weight: 500 !important;
        text-align: left !important; padding: 5px 0px !important; transition: 0.2s;
    }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(4px); }
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 25px; margin-bottom: 20px; }
    .report-text { color: #e0e6ed !important; font-size: 1.15rem !important; line-height: 1.8; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 15px !important; padding: 10px !important; }
    div[data-testid="stChatInput"] textarea { color: #000000 !important; font-size: 1.15rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드 로직
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, None
    latest_file = sorted(files)[-1]
    
    try:
        raw_date = latest_file.split('_')[-1].replace('.csv', '')
        date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    except:
        date_str = datetime.now().strftime('%Y-%m-%d')
        
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "시장" in df.columns:
        df["시장"] = df["시장"].astype(str).str.strip().str.upper()
    if "종목코드" in df.columns: 
        df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df, date_str

data, data_date = load_data()

# 세션 상태 관리
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

def get_groq_client():
    key = st.secrets.get("GROQ_API_KEY")
    return Groq(api_key=key) if key else None

client = get_groq_client()

# 4) 메인 레이아웃 구성
if data is not None:
    # 시장별 데이터 필터링
    df_kospi = data[data["시장"] == "KOSPI"].copy()
    df_kosdaq = data[data["시장"] == "KOSDAQ"].copy()

    # 핵심 변경 포인트: 사이드바 영역을 2.5로 축소
    col_list, col_chat = st.columns([2.5, 7.5])

    # 왼쪽 종목 리스트 섹션
    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착</div>', unsafe_allow_html=True)
        with st.container(height=800):
            m_col1, m_col2 = st.columns(2)
            
            with m_col1:
                st.markdown('<div class="market-header">KOSPI</div>', unsafe_allow_html=True)
                for i, row in df_kospi.iterrows():
                    is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                    label = f"● {row['종목명']}" if is_selected else f"  {row['종목명']}"
                    if st.button(label, key=f"kpi_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.rerun()
            
            with m_col2:
                st.markdown('<div class="market-header">KOSDAQ</div>', unsafe_allow_html=True)
                for i, row in df_kosdaq.iterrows():
                    is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                    label = f"● {row['종목명']}" if is_selected else f"  {row['종목명']}"
                    if st.button(label, key=f"kdq_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.rerun()

    # 오른쪽 채팅 섹션
    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} AI 정밀 리포트</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="report-box"><div class="report-text">
            <span class="highlight-mint">● 분석 대상:</span> {stock["종목명"]} ({stock.get('종목코드', '000000')})<br>
            <span class="highlight-mint">● AI 엔진:</span> Llama-3.3-70B (Versatile Mode)<br>
            <span class="highlight-mint">● 시장구분:</span> {stock.get('시장', 'N/A')}
        </div></div>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=650)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        if prompt := st.chat_input(f"{stock['종목명']}의 전망을 물어보세요!"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{prompt}</div>", unsafe_allow_html=True)
            
            if client:
                with st.status("분석 중...", expanded=True) as status:
                    try:
                        history = [{"role": "system", "content": f"당신은 {stock['종목명']} 전문 주식 분석가입니다. 한국어로 답변하세요. 일본어 금지."}]
                        for m in st.session_state.messages[-10:]:
                            history.append({"role": m["role"], "content": m["content"]})
                        
                        completion = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=history,
                            temperature=0.7, 
                        )
                        ans = completion.choices[0].message.content
                        status.update(label="✅ 완료", state="complete", expanded=False)
                        with chat_container:
                            with st.chat_message("assistant"):
                                st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{ans}</div>", unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                    except Exception as e:
                        st.error(f"오류: {str(e)}")
            st.rerun()