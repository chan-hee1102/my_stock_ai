# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from groq import Groq
from datetime import datetime

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (사용자님의 블랙 & 민트 디자인 유지)
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
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button {
        width: 100% !important; background-color: transparent !important; color: #ffffff !important;
        border: none !important; font-size: 2.2rem !important; font-weight: 800 !important;
        text-align: left !important; padding: 12px 0px !important; transition: 0.3s;
    }
    div[data-testid="stColumn"]:nth-of-type(1) .stButton > button:hover { color: #00e5ff !important; transform: translateX(8px); }
    .report-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 25px; margin-bottom: 20px; }
    .report-text { color: #e0e6ed !important; font-size: 1.2rem !important; line-height: 1.8; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 15px !important; padding: 10px !important; }
    div[data-testid="stChatInput"] textarea { color: #000000 !important; font-size: 1.15rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 데이터 로드 (outputs 폴더의 CSV 파일 자동 탐색)
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None, None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None, None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "종목코드" in df.columns: df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    # 날짜 추출
    raw_date = latest_file.split('_')[-1].replace('.csv', '')
    return df, f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"

data, data_date = load_data()

# 세션 상태 초기화 (대화 내역 및 선택 종목)
if "messages" not in st.session_state: st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# Groq 클라이언트 설정 (secrets.toml에서 가져오기)
def get_groq_client():
    key = st.secrets.get("GROQ_API_KEY")
    if not key:
        st.error("⚠️ GROQ_API_KEY가 secrets.toml에 없습니다!")
        return None
    return Groq(api_key=key)

client = get_groq_client()

# 4) 메인 레이아웃 구성
if data is not None:
    col_list, col_chat = st.columns([2, 8])

    # 왼쪽 종목 리스트
    with col_list:
        st.markdown(f'<div class="section-header">📂 {data_date} 포착 종목</div>', unsafe_allow_html=True)
        with st.container(height=850):
            for i, (idx, row) in enumerate(data.iterrows()):
                is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                display_name = f"▶ {row['종목명']} ◀" if is_selected else f"  {row['종목명']}"
                if st.button(display_name, key=f"btn_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.session_state.messages = [] # 종목 변경 시 대화 초기화
                    st.rerun()
                st.markdown("<hr style='margin:5px 0; border:0.5px solid #30363d; opacity:0.3;'>", unsafe_allow_html=True)

    # 오른쪽 채팅 섹션
    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} AI 전략 사령부 (Groq Engine)</div>', unsafe_allow_html=True)
        
        # 고정 리포트 요약 박스
        st.markdown(f"""
        <div class="report-box"><div class="report-text">
            <span class="highlight-mint">● 분석 대상:</span> {stock["종목명"]} ({stock.get('종목코드', 'N/A')})<br>
            <span class="highlight-mint">● AI 엔진:</span> Llama 3 70B (High-Speed Inference)<br>
            <span class="highlight-mint">● 상태:</span> Groq 초고속 추론 엔진 활성화됨
        </div></div>
        """, unsafe_allow_html=True)

        # 채팅 로그 출력 컨테이너
        chat_container = st.container(height=650)
        with chat_container:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        # 채팅 입력 및 처리
        if prompt := st.chat_input(f"{stock['종목명']}에 대한 심층 분석을 요청하세요."):
            # 1. 사용자 메시지 추가
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{prompt}</div>", unsafe_allow_html=True)

            # 2. Groq AI 응답 생성
            if client:
                with st.status("🚀 Groq 엔진 분석 중...", expanded=True) as status:
                    try:
                        # 최근 5개 대화 내역 맥락 구성
                        history = [{"role": "system", "content": f"당신은 {stock['종목명']} 주식 전문가입니다. 한국어로 답변하세요."}]
                        for m in st.session_state.messages[-5:]:
                            history.append({"role": m["role"], "content": m["content"]})
                        
                        # API 호출
                        completion = client.chat.completions.create(
                            model="llama3-70b-8192",
                            messages=history,
                            temperature=0.7,
                            max_tokens=2048
                        )
                        
                        ans = completion.choices[0].message.content
                        
                        # 3. 답변 표시 및 저장
                        with chat_container:
                            with st.chat_message("assistant"):
                                st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{ans}</div>", unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                        status.update(label="✅ 초고속 분석 완료", state="complete", expanded=False)
                        
                    except Exception as e:
                        st.error(f"❌ Groq API 에러: {str(e)}")
                        status.update(label="❌ 오류 발생", state="error")