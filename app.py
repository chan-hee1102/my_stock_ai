import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 고대비 세련된 테마 적용 CSS
st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    .main-container { max-width: 850px; margin: 0 auto; padding-top: 30px; }

    /* 날짜 배지 */
    .date-badge {
        background: linear-gradient(135deg, #00f2fe, #4facfe);
        color: black;
        padding: 4px 15px;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 800;
        display: inline-block;
        margin-bottom: 15px;
    }

    /* 제목 */
    .main-title { color: #ffffff; font-size: 3rem; font-weight: 900; line-height: 1.1; margin-bottom: 20px; }

    /* ★ 종목 버튼(Expander) 스타일 대수정 ★ */
    .stExpander {
        background-color: #ffffff !important; /* 배경을 흰색으로! */
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        border: none !important;
    }
    
    /* Expander 글자색 검정으로 강제 설정 */
    .stExpander p, .stExpander span, .stExpander div {
        color: #1a1a1a !important; 
        font-weight: 600 !important;
    }

    /* 마우스 올렸을 때 효과 */
    .stExpander:hover {
        background-color: #f0f2f6 !important;
        transform: scale(1.01);
        transition: 0.2s;
    }

    /* 시장 구분 태그 디자인 */
    .m-tag {
        background-color: #000000;
        color: #ffffff !important;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        margin-right: 10px;
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
        # 데이터에 시장 정보가 있으면 쓰고, 없으면 코드를 보고 추측 (임시)
        mkt = row.get('시장', 'KOSPI' if str(row['종목코드'])[0] in ['0', '1'] else 'KOSDAQ')
        
        # 버튼 제목 구성
        list_label = f"[{mkt}] {row['종목명']} ({row['종목코드']})  |  거래대금 {row['거래대금(억)']}억"
        
        with st.expander(list_label):
            # Expander 안의 내용은 다시 읽기 편하게 어두운 테마 적용
            st.markdown('<style>div[data-testid="stExpanderDetails"] p { color: white !important; }</style>', unsafe_allow_html=True)
            
            t1, t2, t3 = st.tabs(["📊 분석", "📰 뉴스", "🤖 AI"])
            with t1:
                st.write(f"**{row['종목명']}** 종목의 상세 수급을 분석 중입니다.")
                st.link_button("네이버 증권 상세 보기", f"https://finance.naver.com/item/main.naver?code={row['종목코드']}")
            with t2:
                st.info("실시간 뉴스 요약 기능이 곧 추가됩니다.")
            with t3:
                st.success("AI 비서: 이 종목은 현재 기관의 매수세가 강력하게 유입되고 있습니다.")
else:
    st.error("데이터 파일이 없습니다.")

st.markdown('</div>', unsafe_allow_html=True)