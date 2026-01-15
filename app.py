# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from groq import Groq
from datetime import datetime

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (임찬희님의 블랙 & 민트 디자인 최적화)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 25px; border: 1px solid #30363d;
    }
    /* 사이드바 헤더 디자인 */
    .section-header { 
        color: #00e5ff !important; font-size: 1.4rem !important; font-weight: 800; 
        margin-bottom: 20px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }
    /* 시장 구분 타이틀 (KOSPI / KOSDAQ) */
    .market-title {
        color: #8b949e; font-size: 1.1rem; font-weight: 700; text-align: center;
        margin-bottom: 15px; padding-bottom: 5px; border-bottom: 1px solid #30363d;
    }
    /* 종목 버튼 디자인 (글자 크기 살짝 조정하여 2열 배치 최적화) */
    .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 1.1rem !important; font-weight: 600 !important;
        text-align: left !important; padding: 8px 0px !important; transition: 0.3s;
    }
    .stButton > button:hover { color: #00e5ff !important; transform: translateX(5px); }
    
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
    # 시장별 데이터 분류 (컬럼명이 '시장' 또는 '시장구분'이라고 가정)
    market_col = "시장구분" if "시장구분" in data.columns else ("시장" if "시장" in data.columns else None)
    
    if market_col:
        df_kospi = data[data[market_col].str.contains("KOSPI|코스피", na=False)]
        df_kosdaq = data[data[market_col].str.contains("KOSDAQ|코스닥", na=False)]
    else:
        # 시장 구분 컬럼이 없을 경우 반반 나눔 (임시방편)
        mid = len(data) // 2
        df_kospi = data.iloc[:mid]
        df_kosdaq = data.iloc[mid:]

    col_list, col_chat = st.columns([3, 7]) # 사이드바 비중을 살짝 높임

    # 왼쪽 종목 리스트 섹션 (KOSPI | KOSDAQ 분할)
    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착</div>', unsafe_allow_html=True)
        
        with st.container(height=800):
            m_col1, m_col2 = st.columns(2)
            
            # KOSPI 리스트
            with m_col1:
                st.markdown('<div class="market-title">KOSPI</div>', unsafe_allow_html=True)
                for i, (idx, row) in enumerate(df_kospi.iterrows()):
                    is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                    label = f"● {row['종목명']}" if is_selected else f"  {row['종목명']}"
                    if st.button(label, key=f"kospi_{i}"):
                        st.session_state.selected_stock = row.to_dict()
                        st.session_state.messages = []
                        st.rerun()
            
            # KOSDAQ 리스트
            with m_col2:
                st.markdown('<div class="market-title">KOSDAQ</div>', unsafe_allow_html=True)
                for i, (idx, row) in enumerate(df_kosdaq.iterrows()):
                    is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                    label = f"● {row['종목명']}" if is_selected else f"  {row['종목명']}"
                    if st.button(label, key=f"kosdaq_{i}"):
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
            <span class="highlight-mint">● AI 엔진:</span> Llama-3.3-70B (Versatile Mode)
        </div></div>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=650)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        if prompt := st.chat_input(f"{stock['종목명']}의 전망을 분석해드릴까요?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{prompt}</div>", unsafe_allow_html=True)
            
            if client:
                with st.status("전략가 분석 중...", expanded=True) as status:
                    try:
                        history = [{"role": "system", "content": f"당신은 {stock['종목명']} 전문 주식 분석가입니다. 전문 용어는 영어로, 답변은 한국어로 하세요. 일본어 사용 금지."}]
                        for m in st.session_state.messages[-10:]:
                            history.append({"role": m["role"], "content": m["content"]})
                        
                        completion = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=history,
                            temperature=0.7, 
                            max_tokens=2048
                        )
                        ans = completion.choices[0].message.content
                        status.update(label="✅ 분석 완료", state="complete", expanded=False)
                        with chat_container:
                            with st.chat_message("assistant"):
                                st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{ans}</div>", unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                    except Exception as e:
                        st.error(f"오류: {str(e)}")
            st.rerun()