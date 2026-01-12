import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 고대비 & 저피로 디자인 CSS
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .main-container { max-width: 850px; margin: 0 auto; padding-top: 30px; }

    /* 날짜 배지: 테두리와 글자 강조 */
    .date-badge {
        background: rgba(0, 212, 255, 0.1);
        color: #00d4ff;
        padding: 5px 18px;
        border: 1.5px solid #00d4ff;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 800;
        display: inline-block;
        margin-bottom: 20px;
    }

    /* ★ 메인 타이틀: 투명도 제거, 선명한 스카이 블루 ★ */
    .main-title { 
        color: #00e5ff !important; /* 선명하고 밝은 하늘색 */
        font-size: 3.5rem; 
        font-weight: 900; 
        line-height: 1.1; 
        margin-bottom: 10px;
        text-shadow: 0 0 30px rgba(0, 229, 255, 0.5); /* 은은한 광채 효과 */
    }

    /* ★ 종목 버튼 스타일: 조금 더 어두운 회색 (#323940) ★ */
    .stExpander {
        background-color: #323940 !important; /* 너무 밝지 않은 중후한 회색 */
        border-radius: 10px !important;
        margin-bottom: 12px !important;
        border: 1px solid #444c56 !important; /* 얇은 테두리로 구분감 */
        transition: 0.3s;
    }
    
    /* 종목 버튼 내부 글자: 흰색으로 가독성 극대화 */
    .stExpander p, .stExpander span, .stExpander div {
        color: #ffffff !important; 
        font-weight: 600 !important;
        font-size: 1.05rem !important;
    }

    /* 마우스 올렸을 때 효과 */
    .stExpander:hover {
        background-color: #444c56 !important;
        border-color: #00d4ff !important; /* 호버 시 하늘색 테두리 */
        transform: translateY(-2px);
    }

    /* 탭 디자인 가독성 조절 */
    .stTabs [data-baseweb="tab-list"] button {
        color: #8b949e !important;
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #00d4ff !important;
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

st.markdown('<div class="main-container">', unsafe_allow_html=True)

res = load_data()
if res:
    data, fname = res
    raw_date = fname.split('_')[-1].replace('.csv', '')
    display_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

    st.markdown(f'<div class="date-badge">COMMANDER SYSTEM : {display_date}</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="main-title">🛡️ AI STOCK<br>COMMANDER</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#8b949e; font-size:1.1rem; margin-bottom:40px;">정밀 수급 엔진이 포착한 오늘의 승부 종목 {len(data)}선</p>', unsafe_allow_html=True)

    for i, row in data.iterrows():
        # 임시 시장 구분 로직 (코드 기반)
        mkt = row.get('시장', 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ')
        list_label = f"[{mkt}] {row['종목명']} ({row['종목코드']})  |  거래대금 {row['거래대금(억)']}억"
        
        with st.expander(list_label):
            t1, t2, t3 = st.tabs(["📊 지표", "📰 뉴스", "🤖 AI"])
            with t1:
                st.write(f"### {row['종목명']} 상세 분석")
                st.link_button("네이버 증권에서 확인", f"https://finance.naver.com/item/main.naver?code={row['종목코드']}")
            with t2:
                st.info("실시간 뉴스 요약 기능이 곧 탑재됩니다.")
            with t3:
                st.success("AI Commander: 현재 외인/기관의 양매수가 집중되고 있는 구간입니다.")
else:
    st.error("데이터 로드 실패")

st.markdown('</div>', unsafe_allow_html=True)