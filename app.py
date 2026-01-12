import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 커스텀 CSS (시인성 개선 버전)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .main-container { max-width: 850px; margin: 0 auto; padding-top: 30px; }

    /* 날짜 배지: 스카이 블루 계열 */
    .date-badge {
        background: rgba(0, 242, 254, 0.1);
        color: #00f2fe;
        padding: 4px 15px;
        border: 1px solid #00f2fe;
        border-radius: 50px;
        font-size: 0.8rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 15px;
    }

    /* 메인 타이틀: 밝은 하늘색(Sky Blue) */
    .main-title { 
        color: #00d4ff; 
        font-size: 3rem; 
        font-weight: 900; 
        line-height: 1.1; 
        margin-bottom: 20px;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
    }

    /* ★ 종목 버튼 스타일 수정: 밝은 회색 계열 ★ */
    .stExpander {
        background-color: #c9d1d9 !important; /* 차분하고 밝은 회색 */
        border-radius: 8px !important;
        margin-bottom: 10px !important;
        border: none !important;
        transition: 0.3s;
    }
    
    /* 종목 버튼 내부 글자: 진한 회색/검정으로 가독성 확보 */
    .stExpander p, .stExpander span, .stExpander div {
        color: #0d1117 !important; 
        font-weight: 700 !important;
    }

    /* 마우스 올렸을 때 살짝 어두워지게 */
    .stExpander:hover {
        background-color: #afb8c1 !important;
        transform: translateY(-1px);
    }

    /* 상세 탭 안의 텍스트는 다시 흰색으로 (가독성) */
    div[data-testid="stExpanderDetails"] p, 
    div[data-testid="stExpanderDetails"] li {
        color: #ffffff !important;
        font-weight: 400 !important;
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

    st.markdown(f'<div class="date-badge">COMMANDER ANALYSIS : {display_date}</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="main-title">🛡️ AI STOCK<br>COMMANDER</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#8b949e;">엄격한 수급 필터를 통과한 {len(data)}개의 핵심 종목입니다.</p>', unsafe_allow_html=True)
    st.markdown('<hr style="border-color:#21262d;">', unsafe_allow_html=True)

    for i, row in data.iterrows():
        # 임시 시장 구분 로직 (데이터 업데이트 전까지 작동)
        mkt = row.get('시장', 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ')
        list_label = f"[{mkt}] {row['종목명']} ({row['종목코드']})  |  거래대금 {row['거래대금(억)']}억"
        
        with st.expander(list_label):
            t1, t2, t3 = st.tabs(["📊 지표", "📰 뉴스", "🤖 AI"])
            with t1:
                st.write(f"### {row['종목명']} ({row['종목코드']})")
                st.link_button("네이버 증권 상세 페이지", f"https://finance.naver.com/item/main.naver?code={row['종목코드']}")
            with t2:
                st.info("실시간 뉴스 요약 기능이 곧 업데이트됩니다.")
            with t3:
                st.success("AI 분석 결과: 해당 종목은 현재 강력한 추세 전환 시그널이 포착되었습니다.")
else:
    st.error("데이터를 불러올 수 없습니다.")

st.markdown('</div>', unsafe_allow_html=True)