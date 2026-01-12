import streamlit as st
import pandas as pd
import os

# 페이지 설정
st.set_page_config(page_title="QUANT STEALTH AI", layout="wide")

# 폴더 설정
OUT_DIR = "outputs"

def load_latest_result():
    if not os.path.exists(OUT_DIR):
        return None
    # outputs 폴더에서 csv 파일들 찾기
    files = [f for f in os.listdir(OUT_DIR) if f.startswith("final_result_") and f.endswith(".csv")]
    if not files:
        return None
    # 가장 최근 파일 선택
    latest_file = sorted(files)[-1]
    df = pd.read_csv(os.path.join(OUT_DIR, latest_file))
    
    # 종목코드를 6자리 문자열로 (앞자리 0 유지)
    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    return df, latest_file

# CSS 스타일링
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: white; }
    .date-box {
        background-color: #1f6feb;
        padding: 10px 20px;
        border-radius: 10px;
        display: inline-block;
        margin-bottom: 25px;
        font-weight: bold;
        font-size: 1.2rem;
    }
    </style>
    """, unsafe_allow_html=True)

res = load_latest_result()

if res:
    data, fname = res
    # 파일명에서 날짜 추출 (final_result_20260112.csv -> 2026-01-12)
    raw_date = fname.split('_')[-1].replace('.csv', '')
    display_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

    st.title("🎯 QUANT STEALTH : AI 선정 종목")
    
    # 요청하신 데이터 기준일 표시 부분
    st.markdown(f"<div class='date-box'>📅 데이터 기준일: {display_date}</div>", unsafe_allow_html=True)
    st.caption(f"분석 대상: 유가증권/코스닥 전체 (총 {len(data)}개 종목 발굴 완료)")

    col1, col2 = st.columns([0.4, 0.6])
    
    with col1:
        st.subheader("✅ 필터링 결과")
        selected_name = st.selectbox("상세 정보를 보려면 종목을 선택하세요", data["종목명"].tolist())
        # 표 형식 개선
        st.dataframe(data, use_container_width=True, height=600)

    with col2:
        stock_info = data[data["종목명"] == selected_name].iloc[0]
        code = stock_info["종목코드"]
        
        st.subheader(f"📊 {selected_name} ({code}) 분석")
        
        # 네이버 증권 버튼
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        st.link_button(f"🔗 {selected_name} 네이버 증권 바로가기", url)
        
        tab1, tab2, tab3 = st.tabs(["📈 차트", "💎 재무/뉴스", "🤖 AI 비서"])
        
        with tab1:
            # 일봉 차트 (네이버 제공)
            chart_url = f"https://ssl.pstatic.net/imgstock/chart3/day/{code}.png"
            st.image(chart_url, caption=f"{selected_name} 일봉 차트", use_container_width=True)
            
        with tab2:
            st.info("실시간 재무 지표와 뉴스 데이터를 불러올 준비 중입니다.")
        with tab3:
            st.chat_message("assistant").write(f"{selected_name}의 최근 수급이나 향후 전망에 대해 알고 싶으신가요?")

else:
    st.error("분석 결과 파일이 없습니다. scanner.py를 먼저 실행해 주세요.")