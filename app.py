import streamlit as st
import pandas as pd
import os

# 1. 페이지 설정 (레이아웃을 넓게 설정)
st.set_page_config(page_title="QUANT STEALTH AI", layout="wide")

# 2. 스타일링 (검은색 테마와 깔끔한 카드 디자인)
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stApp { max-width: 1000px; margin: 0 auto; }
    .date-badge {
        background-color: #1f6feb;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    h1 { color: #f0f6fc; font-size: 2.5rem; margin-bottom: 5px; }
    p { color: #8b949e; }
    .stock-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    .stock-card:hover {
        border-color: #58a6ff;
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 함수
def load_data():
    out_dir = "outputs"
    if not os.path.exists(out_dir): return None
    files = [f for f in os.listdir(out_dir) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files: return None
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(out_dir, latest_file))
    # 종목코드 6자리 유지
    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    # 현재가 열 삭제 (사용자 요청)
    if '현재가' in df.columns:
        df = df.drop(columns=['현재가'])
    return df, latest_file

res = load_data()

if res:
    data, fname = res
    raw_date = fname.split('_')[-1].replace('.csv', '')
    display_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

    # 상단 헤더
    st.markdown(f"<div class='date-badge'>📅 {display_date} 데이터 기준</div>", unsafe_allow_html=True)
    st.title("🎯 QUANT STEALTH")
    st.write(f"오늘의 유망 종목 {len(data)}개를 발굴했습니다.")
    st.markdown("---")

    # 종목 리스트 출력 (클릭 시 상세정보가 나오도록 Expander 활용)
    for i, row in data.iterrows():
        # 시장 구분이 데이터에 없다면 코드를 통해 유추하거나, 
        # scanner.py에서 시장 정보를 저장하도록 나중에 수정이 필요할 수 있습니다.
        # 일단은 종목명과 거래대금 위주로 깔끔하게 배치합니다.
        
        with st.expander(f"✨ {row['종목명']} ({row['종목코드']}) - 거래대금: {row['거래대금(억)']}억"):
            st.write(f"### {row['종목명']} 상세 분석")
            
            # 상세 탭 구성 (다음 단계에서 구현할 영역)
            t1, t2, t3, t4 = st.tabs(["📈 차트", "📰 최신 뉴스", "💰 재무제표", "🤖 AI 코멘트"])
            
            with t1:
                st.info("실시간 인터랙티브 차트를 준비 중입니다.")
                url = f"https://finance.naver.com/item/main.naver?code={row['종목코드']}"
                st.link_button("네이버 증권에서 차트 보기", url)
            with t2:
                st.info("최신 뉴스를 수집하고 있습니다.")
            with t3:
                st.info("재무 지표(PER/PBR 등)를 분석 중입니다.")
            with t4:
                st.info(f"AI가 {row['종목명']}의 수급 강도를 분석할 예정입니다.")

else:
    st.error("데이터를 찾을 수 없습니다.")