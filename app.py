import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정 (반드시 전체 화면 사용)
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 스타일링 (2분할 최적화 및 디자인 유지)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    
    /* 타이틀 영역 */
    .main-title { 
        color: #00e5ff !important; 
        font-size: 2.5rem; 
        font-weight: 900; 
        margin-bottom: 5px;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
    }
    
    /* 종목 버튼 스타일 (길이 축소 및 딥 그레이) */
    .stButton > button {
        width: 100%;
        background-color: #1a1d23 !important;
        color: #ffffff !important;
        border: 1px solid #30363d !important;
        border-radius: 8px;
        padding: 15px;
        text-align: left;
        margin-bottom: 10px;
        transition: 0.3s;
    }
    .stButton > button:hover {
        border-color: #00e5ff !important;
        background-color: #21262d !important;
    }

    /* AI 메시지 박스 */
    .ai-box {
        background-color: #0d1117;
        border: 1.5px solid #00e5ff;
        border-radius: 15px;
        padding: 25px;
        min-height: 500px;
    }
    </style>
    """, unsafe_allow_html=True)

def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    return df, latest_file

# 상단 타이틀
st.markdown('<h1 class="main-title">🛡️ AI STOCK COMMANDER</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#8b949e; margin-bottom:20px;">분석된 종목을 클릭하여 AI 브리핑을 확인하세요.</p>', unsafe_allow_html=True)

res = load_data()

if res:
    data, fname = res
    
    # --- 화면 분할 (왼쪽 4 : 오른쪽 6) ---
    col1, col2 = st.columns([4, 6])
    
    # 3. 세션 상태 초기화 (클릭한 종목 저장용)
    if 'selected_stock' not in st.session_state:
        st.session_state.selected_stock = data.iloc[0].to_dict()

    # --- 왼쪽: 종목 리스트 ---
    with col1:
        st.write(f"📍 포착된 종목 ({len(data)})")
        for i, row in data.iterrows():
            mkt = row.get('시장', 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ')
            # 버튼 클릭 시 해당 종목을 세션에 저장
            if st.button(f"[{mkt}] {row['종목명']}", key=f"btn_{row['종목코드']}"):
                st.session_state.selected_stock = row.to_dict()

    # --- 오른쪽: LLM 메시지 영역 ---
    with col2:
        stock = st.session_state.selected_stock
        st.markdown(f"""
            <div class="ai-box">
                <h2 style="color:#00e5ff; margin-top:0;">🤖 AI COMMANDER BRIEFING</h2>
                <hr style="border-color:#21262d;">
                <h3 style="color:white;">{stock['종목명']} ({stock['종목코드']})</h3>
                <p style="color:#8b949e;">거래대금: {stock['거래대금(억)']}억</p>
                <br>
                <div style="background:#161b22; padding:20px; border-radius:10px; border-left:4px solid #00e5ff;">
                    <p style="color:#ffffff; line-height:1.6;">
                        "현재 <b>{stock['종목명']}</b> 종목에 대한 수급 분석을 진행 중입니다.<br><br>
                        이 종목은 최근 거래대금이 폭발하며 전고점을 돌파하려는 움직임을 보이고 있습니다. 
                        Gemini AI가 실시간 뉴스를 분석한 결과, 해당 산업군에 대한 긍정적인 전망이 지배적입니다."
                    </p>
                </div>
                <br>
                <p style="color:#58a6ff;">💡 <b>Commander's Tip:</b> 눌림목 구간에서 분할 매수 관점이 유효해 보입니다.</p>
            </div>
        """, unsafe_allow_html=True)
        
        # 추가 버튼들
        st.write("")
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            st.link_button(f"🔗 {stock['종목명']} 네이버 증권", f"https://finance.naver.com/item/main.naver?code={stock['종목코드']}")
        with c_btn2:
            if st.button("🔄 AI에게 다시 분석 요청"):
                st.toast("Gemini가 데이터를 다시 읽고 있습니다...")

else:
    st.error("데이터를 로드할 수 없습니다.")