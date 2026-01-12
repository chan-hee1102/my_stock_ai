import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# 2. 스타일링
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stApp { max-width: 900px; margin: 0 auto; }
    .date-badge {
        background-color: #eb1f5a; /* 강조색 변경 */
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    .market-badge {
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 5px;
        background-color: #30363d;
        color: #8b949e;
        margin-right: 8px;
    }
    h1 { color: #ffffff; font-size: 2.8rem; font-weight: 800; letter-spacing: -1px; }
    .subtitle { color: #8b949e; margin-bottom: 30px; font-size: 1.1rem; }
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

res = load_data()

if res:
    data, fname = res
    raw_date = fname.split('_')[-1].replace('.csv', '')
    display_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

    # 상단 헤더 (새 이름 적용)
    st.markdown(f"<div class='date-badge'>{display_date} ANALYSIS</div>", unsafe_allow_html=True)
    st.title("🛡️ AI STOCK COMMANDER")
    st.markdown(f"<p class='subtitle'>전체 시장을 전수 조사하여 엄선한 {len(data)}개의 핵심 종목입니다.</p>", unsafe_allow_html=True)

    # 종목 리스트 (시장 정보 포함)
    for i, row in data.iterrows():
        # 데이터에 '시장' 열이 있으면 가져오고, 없으면 '정보없음' 표시
        market = row.get('시장', 'KOSPI/KOSDAQ') 
        
        with st.expander(f"[{market}] {row['종목명']} ({row['종목코드']}) | 거래대금 {row['거래대금(억)']}억"):
            t1, t2, t3 = st.tabs(["📊 상세 지표", "📰 뉴스 요약", "🤖 AI 전략"])
            
            with t1:
                st.write(f"**{row['종목명']}**의 정밀 분석 데이터를 준비 중입니다.")
                url = f"https://finance.naver.com/item/main.naver?code={row['종목코드']}"
                st.link_button("네이버 증권 상세 페이지", url)
            with t2:
                st.info("최신 뉴스 API 연동 예정입니다.")
            with t3:
                st.success("AI가 이 종목의 매수 강도를 분석하고 있습니다.")

else:
    st.error("분석된 데이터를 찾을 수 없습니다.")