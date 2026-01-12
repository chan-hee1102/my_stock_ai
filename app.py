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
    files = [f for f in os.listdir(OUT_DIR) if f.startswith("final_result_")]
    if not files:
        return None
    latest_file = sorted(files)[-1]
    return pd.read_csv(os.path.join(OUT_DIR, latest_file)), latest_file

# CSS로 다크 세련미 추가
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: white; }
    .stDataFrame { border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

res = load_latest_result()

if res:
    data, fname = res
    st.title("🎯 QUANT STEALTH : AI 선정 종목")
    st.caption(f"기준 데이터: {fname} (총 {len(data)}개 종목 발견)")

    col1, col2 = st.columns([0.4, 0.6])
    
    with col1:
        st.subheader("✅ 필터링 결과")
        # 종목 선택
        selected_name = st.selectbox("상세 정보를 보려면 종목을 선택하세요", data["종목명"].tolist())
        st.dataframe(data, use_container_width=True, height=500)

    with col2:
        # 선택된 종목의 정보 추출
        stock_info = data[data["종목명"] == selected_name].iloc[0]
        code = stock_info["종목코드"]
        
        st.subheader(f"📊 {selected_name} ({code}) 분석")
        
        # 네이버 증권 링크 버튼
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        st.link_button(f"🔗 {selected_name} 네이버 증권에서 보기", url)
        
        tab1, tab2, tab3 = st.tabs(["📈 차트 미리보기", "💎 재무/뉴스", "🤖 AI 비서"])
        
        with tab1:
            # 네이버 금융 차트 이미지 불러오기
            chart_url = f"https://ssl.pstatic.net/imgstock/chart3/day/{code}.png"
            st.image(chart_url, caption=f"{selected_name} 일봉 차트", use_container_width=True)
            
        with tab2:
            st.info("재무 정보와 뉴스를 연동할 준비 중입니다.")
        with tab3:
            st.chat_message("assistant").write(f"{selected_name}에 대해 궁금한 점을 입력해 주세요.")

else:
    st.warning("분석 데이터가 없습니다. scanner.py를 먼저 실행해 주세요.")