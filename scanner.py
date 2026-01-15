# -*- coding: utf-8 -*-
import os
import time
import random
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

# =========================
# 1. 환경 설정 및 폴더 생성
# =========================
OUT_DIR = "outputs"
if not os.path.exists(OUT_DIR):
    os.makedirs(OUT_DIR)

# --- 원본 파라미터 유지 ---
FULL_COUNT = 320
VOL_RATIO_THRESHOLD = 5.0
TURNOVER_MAX_20_THRESHOLD = 1000 * 1e8   # 1000억
LAST_TURNOVER_THRESHOLD   = 50 * 1e8     # 50억
SLOPE_LOOKBACK_DAYS = 5
ICHIMOKU_TENKAN = 9
ICHIMOKU_KIJUN  = 26

# =========================
# 2. 데이터 수집 함수 (시장 분류 로직 추가)
# =========================
def get_listing():
    """KIND에서 코스피와 코스닥을 각각 가져와서 합치기"""
    # 1. KOSPI (stockMkt) 가져오기
    url = "https://kind.krx.co.kr/corpgeneral/corpList.do"
    r_kospi = requests.get(url, params={"method": "download", "marketType": "stockMkt"})
    df_kospi = pd.read_html(r_kospi.text, header=0)[0]
    df_kospi["시장"] = "KOSPI" # 네이버의 '유가'를 KOSPI로 명확히 기록

    # 2. KOSDAQ (kosdaqMkt) 가져오기
    r_kosdaq = requests.get(url, params={"method": "download", "marketType": "kosdaqMkt"})
    df_kosdaq = pd.read_html(r_kosdaq.text, header=0)[0]
    df_kosdaq["시장"] = "KOSDAQ"

    # 3. 데이터 합치기
    df = pd.concat([df_kospi, df_kosdaq], ignore_index=True)
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df

def get_ohlcv(code):
    """네이버 금융 XML API로 일봉 데이터 가져오기"""
    url = "https://fchart.stock.naver.com/sise.nhn"
    params = {"symbol": code, "timeframe": "day", "count": str(FULL_COUNT), "requestType": "0"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, "lxml-xml")
        items = soup.find_all("item")
        if not items: return None
        
        rows = []
        for it in items:
            d = it["data"].split("|")
            rows.append({
                "Date": pd.to_datetime(d[0]),
                "High": int(d[2]), "Low": int(d[3]),
                "Close": int(d[4]), "Volume": int(d[5])
            })
        df = pd.DataFrame(rows).sort_values("Date").set_index("Date")
        return df
    except:
        return None

# =========================
# 3. 조건 검증 함수 (원본 로직 완벽 반영)
# =========================
def check_all_conditions(df):
    if df is None or len(df) < 260: return False
    
    c, v, h, l = df["Close"], df["Volume"], df["High"], df["Low"]
    
    # [조건 1] 거래대금 필터
    turnover = c * v
    if turnover.tail(20).max() < TURNOVER_MAX_20_THRESHOLD: return False
    if turnover.iloc[-1] < LAST_TURNOVER_THRESHOLD: return False
    
    # [조건 2] 거래량 스파이크 (전일 또는 전전일 대비 5배)
    r1 = v / v.shift(1)
    r2 = v / v.shift(2)
    if not ((r1.tail(20) >= VOL_RATIO_THRESHOLD) | (r2.tail(20) >= VOL_RATIO_THRESHOLD)).any():
        return False
    
    # [조건 3] 이동평균선 정배열 (5 > 20 > 60) & 종가 > MA5
    ma5 = c.rolling(5).mean()
    ma20 = c.rolling(20).mean()
    ma60 = c.rolling(60).mean()
    if not (ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]): return False
    if not (c.iloc[-1] > ma5.iloc[-1]): return False
    
    # [조건 4] 장기 이평선(120, 240) 우상향 기울기
    ma120 = c.rolling(120).mean()
    ma240 = c.rolling(240).mean()
    lb = SLOPE_LOOKBACK_DAYS
    if not (ma120.iloc[-1] > ma120.iloc[-(lb+1)] and ma240.iloc[-1] > ma240.iloc[-(lb+1)]):
        return False
        
    # [조건 5] 120일 신고가가 최근 20일 이내 발생
    if c.tail(20).max() < c.tail(120).max(): return False
    
    # [조건 6] 일목균형표 (전환선 > 기준선 & 종가 > 전환선)
    tenkan = (h.rolling(ICHIMOKU_TENKAN).max() + l.rolling(ICHIMOKU_TENKAN).min()) / 2
    kijun = (h.rolling(ICHIMOKU_KIJUN).max() + l.rolling(ICHIMOKU_KIJUN).min()) / 2
    if pd.isna(tenkan.iloc[-1]) or pd.isna(kijun.iloc[-1]): return False
    if not (tenkan.iloc[-1] > kijun.iloc[-1] and c.iloc[-1] > tenkan.iloc[-1]): return False
    
    return True

# =========================
# 4. 메인 실행 루프
# =========================
def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 상장 종목 스캔 시작...")
    listing = get_listing()
    results = []
    
    for i, row in listing.iterrows():
        code, name, market = row["종목코드"], row["회사명"], row["시장"]
        
        df = get_ohlcv(code)
        if check_all_conditions(df):
            last_turnover = int(round((df["Close"].iloc[-1] * df["Volume"].iloc[-1]) / 1e8, 0))
            results.append({
                "종목코드": code,
                "종목명": name,
                "거래대금(억)": last_turnover,
                "시장": market, # 수집 시 분류된 KOSPI 또는 KOSDAQ이 들어감
                "현재가": df["Close"].iloc[-1]
            })
        
        # 진행 상황 표시
        time.sleep(random.uniform(0.02, 0.04))
        if (i + 1) % 100 == 0:
            print(f">>> {i+1}개 종목 분석 중... (현재 {len(results)}개 포착)")

    # 결과 저장
    if results:
        df_res = pd.DataFrame(results).sort_values("거래대금(억)", ascending=False).reset_index(drop=True)
        date_str = datetime.now().strftime("%Y%m%d")
        path = os.path.join(OUT_DIR, f"final_result_{date_str}.csv")
        df_res.to_csv(path, index=False, encoding="utf-8-sig")
        print("-" * 30)
        print(f"✅ 스캔 완료! 통과 종목: {len(results)}개")
        print(f"📂 결과 저장 위치: {path}")
    else:
        print("❌ 조건에 맞는 종목이 없습니다.")

if __name__ == "__main__":
    main()