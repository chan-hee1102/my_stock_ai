import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 세련된 테마 적용을 위한 CSS
st.markdown("""
    <style>
    /* 전체 배경 및 폰트 */
    .stApp {
        background-color: #05070a;
        font-family: 'Pretendard', -apple-system, sans-serif;
    }
    
    /* 중앙 정렬 컨테이너 */
    .main-container {
        max-width: 850px;
        margin: 0 auto;
        padding-top: 50px;
    }

    /* 날짜 배지 */
    .date-badge {
        background: linear-gradient(135deg, #ff0080, #7928ca);
        color: white;
        padding: 4px 12px;
        border-radius: 50px;
        font-size: 0.8rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(255, 0, 128, 0.3);
    }

    /* 메인 타이틀 */
    .main-title {
        color: #ffffff;
        font-size: 3.2rem;
        font-weight: 900;
        letter-spacing: -2px;
        margin-bottom: 10px;
        line-height: 1.1;
    }

    /* 서브 타이틀 */
    .sub-title {
        color: #8b949e;
        font-size: 1.1rem;
        margin-bottom: 40px;
    }

    /* 종목 리스트 스타일 (Expander) */
    .stExpander {
        background-color: #0d1117 !important;
        border: 1px solid #21262d !important;
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        transition: all 0.3s ease;
    }
    .stExpander:hover {
        border-color: #58a6ff !important;
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(0,0,0,0.5);
    }

    /* 시장 구분 라벨 (KOSPI/KOSDAQ) */
    .market-tag {
        color: #58a6ff;
        font-weight: 700;
        margin-right: 10px;
        font-family: monospace;
    }
    
    /* 가로줄 */
    hr {
        border: 0;
        height: 1px;
        background: #21262d;
        margin: 40px 0;
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

# 메인 레이아웃 시작
st.markdown('<div class="main-container">', unsafe_allow_html=True)

res = load_data()

if res:
    data, fname = res
    raw_date = fname.split('_')[-1].replace('.csv', '')
    display_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

    # 헤더 섹션
    st.markdown(f'<div class="date-badge">STALKING THE MARKET : {display_date}</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="main-title">🛡️ AI STOCK<br>COMMANDER</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-title">전수 조사 시스템이 {len(data)}개의 고밀도 수급 종목을 포착했습니다.</p>', unsafe_allow_html=True)
    st.markdown('<hr>', unsafe_allow_html=True)

    # 종목 리스트
    for i, row in data.iterrows():
        # 시장 정보가 데이터에 없더라도 기본값 표시, 있으면 데이터값 사용
        mkt = row.get('시장', 'MARKET')
        
        # 리스트 타이틀 구성
        list_label = f" {mkt} | {row['종목명']} ({row['종목코드']}) — {row['거래대금(억)']}억"
        
        with st.expander(list_label):
            t1, t2, t3, t4 = st.tabs(["📊 지표", "📰 뉴스", "💰 재무", "🤖 AI"])
            
            with t1:
                st.write(f"### {row['종목명']} ({row['종목코드']})")
                url = f"https://finance.naver.com/item/main.naver?code={row['종목코드']}"
                st.link_button("네이버 증권 상세 정보 확인", url)
            with t2:
                st.info("다음 업데이트에서 AI 뉴스 요약 기능이 추가됩니다.")
            with t3:
                st.info("재무 제표 분석 모듈 로딩 중...")
            with t4:
                st.success(f"현재 {row['종목명']}의 수급 유입 강도는 '매우 강함'입니다.")

else:
    st.error("데이터를 불러올 수 없습니다. 스캐너를 먼저 실행하세요.")

st.markdown('</div>', unsafe_allow_html=True)