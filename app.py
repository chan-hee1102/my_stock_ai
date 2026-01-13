import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# 페이지 설정
st.set_page_config(page_title="AI STOCK COMMANDER", layout="wide")

# Gemini AI 설정 (짝꿍을 맞춘 안전한 코드)
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 모델 이름에서 models/ 를 빼고 깔끔하게 설정
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.error("API 키를 찾을 수 없습니다. Streamlit Cloud의 Secrets 설정을 확인하세요.")
except Exception as e:
    st.error(f"AI 엔진 초기화 중 오류 발생: {e}")

# --- 이후 CSS 및 데이터 로드 코드는 그대로 유지 ---