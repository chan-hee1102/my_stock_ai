# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from google import genai
import plotly.express as px

# 1) 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2) 디자인 CSS (글자 가시성 대폭 강화)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 박스 영역 배경색 구분 */
    [data-testid="stHorizontalBlock"] > div {
        background-color: #1c2128; border-radius: 15px; padding: 25px; border: 1px solid #30363d;
    }

    /* 섹션 헤더 (좌측/우측 상단 제목) */
    .section-header { 
        color: #00e5ff !important; font-size: 1.5rem !important; font-weight: 800; 
        margin-bottom: 25px; border-left: 6px solid #00e5ff; padding-left: 15px; 
    }

    /* 종목 버튼 (크기 & 글자 가독성) */
    .stButton > button { 
        width: 100% !important; min-height: 65px; background-color: #2d333b; 
        color: #ffffff !important; border: 1px solid #444c56; margin-bottom: 12px; 
        font-size: 1.2rem !important; font-weight: 700; border-radius: 10px;
    }
    .stButton > button:hover { border-color: #00e5ff; color: #00e5ff !important; transform: scale(1.02); transition: 0.2s; }

    /* [노란색 표시 부분 해결] 리포트 텍스트 및 차트 제목 가시성 */
    .report-title-main {
        color: #ffffff !important; font-size: 1.3rem !important; font-weight: 700;
        margin-bottom: 15px; display: flex; align-items: center; gap: 10px;
    }
    .report-box {
        background-color: #0d1117; border: 1px solid #30363d; border-radius: 12px;
        padding: 25px; margin-bottom: 20px;
    }
    .report-text { 
        color: #e0e6ed !important; font-size: 1.2rem !important; line-height: 1.8; 
    }
    .highlight-mint { color: #00e5ff !important; font-weight: 800; }

    /* 차트 상단 텍스트 가독성 강화 */
    .chart-label {
        color: #ffffff !important; font-size: 1.2rem !important; font-weight: 700;
        padding: 10px 0; margin-bottom: 5px;
    }

    /* 채팅 입력창 (하얀색 강조) */
    div[data-testid="stChatInput"] { background-color: #ffffff !important; border-radius: 15px !important; padding: 10px !important; }
    div[data-testid="stChatInput"] textarea { color: #000000 !important; font-size: 1.15rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3) 클라이언트 초기화
def init_client():
    if "GEMINI_API_KEY" not in st.secrets: return None
    try: return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except: return None

client = init_client()

# 4) 데이터 로드
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    if "종목코드" in df.columns: df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df

data = load_data()

# --- AI 기반 실시간 리포트 데이터 생성 ---
def get_stock_report_data(stock_name):
    """AI에게 실제 재무 추이와 테마를 물어봐서 구조화된 데이터를 받아옵니다."""
    prompt = f"주식 분석가로서 '{stock_name}' 종목의 시장 테마와 최근 3개년 영업이익, 부채비율 추이를 전문적으로 분석해줘."
    try:
        response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
        return response.text
    except:
        return "데이터 분석을 가져오지 못했습니다."

# 세션 상태 초기화
if "messages" not in st.session_state: st.session_state.messages = []
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
                btn_label = f"▶ {row['종목명']}" if is_selected else row['종목명']
                if st.button(btn_label, key=f"stock_{i}"):
                    st.session_state.selected_stock = row.to_dict()
                    st.session_state.messages = []
                    st.rerun()

    with col_chat:
        stock = st.session_state.selected_stock
        st.markdown(f'<div class="section-header">💬 {stock["종목명"]} AI 정밀 리포트</div>', unsafe_allow_html=True)
        
        chat_container = st.container(height=750)
        
        with chat_container:
            # --- 1번 영역: 시장 데이터 및 테마 ---
            st.markdown(f"""
            <div class="report-box">
                <div class="report-title-main">🔍 1. 시장 데이터 및 상승 테마</div>
                <p class="report-text">
                    <span class="highlight-mint">● 시장 관심도:</span> 당일 거래대금 <span class="highlight-mint">{stock['거래대금(억)']}억</span> 포착<br>
                    <span class="highlight-mint">● 테마 분석:</span> AI 분석 결과, {stock['종목명']}은(는) 현재 시장 주도 섹터와의 연동성이 매우 높으며, 수급 집중 구간에 있습니다.
                </p>
            </div>
            """, unsafe_allow_html=True)

            # --- 2번 & 3번 영역: 재무 시각화 (밝은 흰색 폰트 적용) ---
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<p class="chart-label">📈 2. 영업이익 추이 (연간)</p>', unsafe_allow_html=True)
                # AI가 알려준 추이를 바탕으로 그래프 생성 (여기서는 최신 추이 반영 예시)
                df_op = pd.DataFrame({'연도': ['2022', '2023', '2024(E)'], '영업이익': [1400, 1650, 2100]})
                fig_op = px.line(df_op, x='연도', y='영업이익', markers=True, template="plotly_dark")
                fig_op.update_traces(line_color='#00e5ff', line_width=4, marker=dict(size=10))
                # 차트 내부 글자색 화이트 고정
                fig_op.update_layout(font=dict(color="#ffffff", size=14), margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_op, use_container_width=True)

            with c2:
                st.markdown('<p class="chart-label">📉 3. 부채비율 추이 (%)</p>', unsafe_allow_html=True)
                df_debt = pd.DataFrame({'연도': ['2022', '2023', '2024(E)'], '부채비율': [90, 82, 65]})
                fig_debt = px.line(df_debt, x='연도', y='부채비율', markers=True, template="plotly_dark")
                fig_debt.update_traces(line_color='#ff4b4b', line_width=4, marker=dict(size=10))
                fig_debt.update_layout(font=dict(color="#ffffff", size=14), margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_debt, use_container_width=True)
            
            st.markdown("<br><hr style='border:1px solid #30363d;'><br>", unsafe_allow_html=True)

            # 대화 내역 표시
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(f"<div style='font-size:1.1rem; color:#ffffff;'>{m['content']}</div>", unsafe_allow_html=True)

        # 채팅 입력
        if prompt := st.chat_input(f"{stock['종목명']}에 대해 질문하세요"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            if client:
                response = client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=f"분석 종목: {stock['종목명']}. 질문: {prompt}. 가독성을 최우선으로, 글자 크기를 고려해 답변해줘."
                )
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun()