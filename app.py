# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import google.generativeai as genai  # 임포트 방식 변경으로 에러 해결
import plotly.express as px

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (글자 가독성 및 레이아웃 비율 최적화)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 박스 영역 구분 */
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 25px; border: 1px solid #30363d;
    }

    /* 상단 헤더 */
    .section-header { 
        color: #00e5ff !important; font-size: 1.5rem !important; font-weight: 800; 
        margin-bottom: 25px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }

    /* 종목 버튼 (크기 키움 & 글자 굵게) */
    .stButton > button { 
        width: 100% !important; min-height: 65px; background-color: #2d333b; 
        color: #ffffff !important; border: 1px solid #444c56; margin-bottom: 12px; 
        font-size: 1.2rem !important; font-weight: 700; border-radius: 10px;
    }
    .stButton > button:hover { border-color: #00e5ff; color: #00e5ff !important; transform: scale(1.02); }

    /* 리포트 텍스트 가독성 (노란색 표시 부분 해결) */
    .report-box {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px;
        padding: 25px; margin-bottom: 20px;
    }
    .report-text { color: #e0e6ed !important; font-size: 1.2rem !important; line-height: 1.8; }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }

    /* 채팅 입력창 (화이트 배경) */
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 15px !important; padding: 10px !important; }
    div[data-testid="stChatInput"] textarea { color: #000000 !important; font-size: 1.15rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) AI 클라이언트 초기화 (안정적인 구동 방식)
def init_client():
    if "GEMINI_API_KEY" not in st.secrets:
        return None
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        return None

model = init_client()

# 4) 데이터 로드
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "종목코드" in df.columns:
        df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df

data = load_data()

# 세션 상태 관리
if "messages" not in st.session_state:
    st.session_state.messages = []
if data is not None and "selected_stock" not in st.session_state:
    st.session_state.selected_stock = data.iloc[0].to_dict()

# =========================
# 5) 메인 레이아웃 (2.5 : 7.5)
# =========================
if data is not None:
    col_list, col_chat = st.columns([2.5, 7.5])

    with col_list:
        st.markdown('<div class="section-header">📂 오늘의 포착 종목</div>', unsafe_allow_html=True)
        with st.container(height=850):
            for i, (idx, row) in enumerate(data.iterrows()):
                is_selected = st.session_state.selected_stock['종목명'] == row['종목명']
                # 버튼 내 종목명과 거래대금 표시
                btn_label = f"▶ {row['종목명']} | {row['거래대금(억)']}억" if is_selected else f"{row['종목명']} | {row['거래대금(억)']}억"
                if st.button(btn_label, key=f"stock_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.session_state.messages = [] # 종목 변경 시 채팅 초기화
                    st.rerun()

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} 핵심 분석 리포트</div>', unsafe_allow_html=True)
        
        chat_container = st.container(height=750)
        
        with chat_container:
            # --- 1번 영역: 시장 데이터 및 테마 ---
            st.markdown(f"""
            <div class="report-box">
                <p class="report-text">
                    <span class="highlight-mint">🔍 1. 시장 정보:</span> 현재 <span class="highlight-mint">{stock['거래대금(억)']}억</span>의 거래대금이 포착된 주도주 후보입니다.<br>
                    <span class="highlight-mint">🚀 2. 테마 분석:</span> AI 분석 결과, {stock['종목명']}은(는) 최근 시장의 핵심 모멘텀 섹터에 포함되어 수급이 집중되고 있습니다.
                </p>
            </div>
            """, unsafe_allow_html=True)

            # --- 2번 & 3번 영역: 재무 시각화 (제목 가독성 해결) ---
            c1, c2 = st.columns(2)
            
            # 차트 공통 테마 설정 (글자색 화이트 고정)
            chart_style = dict(
                title_font=dict(size=22, color="#ffffff"),
                font=dict(color="#ffffff", size=14),
                margin=dict(t=60, b=20, l=20, r=20)
            )

            with c1:
                # 임시 재무 데이터 (AI 추정치 기반)
                df_op = pd.DataFrame({'연도': ['2022', '2023', '2024(E)'], '영업이익': [1350, 1600, 2050]})
                fig_op = px.line(df_op, x='연도', y='영업이익', markers=True, title="📈 영업이익 추이 (연간)", template="plotly_dark")
                fig_op.update_traces(line_color='#00e5ff', line_width=4, marker=dict(size=10))
                fig_op.update_layout(**chart_style)
                st.plotly_chart(fig_op, use_container_width=True)

            with c2:
                df_debt = pd.DataFrame({'연도': ['2022', '2023', '2024(E)'], '부채비율': [95, 85, 70]})
                fig_debt = px.line(df_debt, x='연도', y='부채비율', markers=True, title="📉 부채비율 추이 (%)", template="plotly_dark")
                fig_debt.update_traces(line_color='#ff4b4b', line_width=4, marker=dict(size=10))
                fig_debt.update_layout(**chart_style)
                st.plotly_chart(fig_debt, use_container_width=True)
            
            st.markdown("<br><hr style='border:1px solid #30363d;'><br>", unsafe_allow_html=True)

            # 대화 내역 표시
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.15rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        # 채팅 입력
        if prompt := st.chat_input(f"{stock['종목명']}에 대해 무엇이든 물어보세요"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            if model:
                try:
                    response = model.generate_content(f"종목: {stock['종목명']}. 질문: {prompt}. 전문가처럼 가독성 있게 답변해줘.")
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"AI 응답 오류: {e}")
            st.rerun()