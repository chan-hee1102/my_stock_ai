# -*- coding: utf-8 -*-
import warnings
warnings.filterwarnings("ignore")

import os
import time
import random
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from groq import Groq  # AI 분석을 위해 추가

# =========================
# 1. 파라미터 설정 (찬희님 로직 반영)
# =========================
FULL_COUNT = 320
LOOKBACK_20 = 20
VOL_RATIO_THRESHOLD = 5.0
TURNOVER_MAX_20_THRESHOLD = 1000 * 1e8   # 1000억
LAST_TURNOVER_THRESHOLD   = 50   * 1e8   # 50억
SLOPE_LOOKBACK_DAYS = 5

# 일목균형표 파라미터
ICHIMOKU_TENKAN = 9
ICHIMOKU_KIJUN  = 26

# 서버 부하 방지용 슬립
SLEEP_MIN = 0.05
SLEEP_MAX = 0.15
RETRY_FULL  = 2

OUT_DIR = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

# [수정] API 키 불러오기: st.secrets 대신 os.getenv 사용 (GitHub Actions 호환)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# =========================
# 2. 유틸리티 및 데이터 수집
# =========================
def today_yyyymmdd():
    return datetime.today().strftime("%Y%m%d")

def to_eok(x):
    return int(round(x / 1e8, 0))

def safe_get(url, params):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://finance.naver.com/"
    }
    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    return r.text

def get_listing():
    print("[INFO] KRX 종목 리스트 수집 중...")
    url = "https://kind.krx.co.kr/corpgeneral/corpList.do"
    r = requests.get(url, params={"method": "download"}, timeout=15)
    df = pd.read_html(r.text, header=0)[0]
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return pd.DataFrame({
        "Code": df["종목코드"],
        "Name": df["회사명"],
        "Market": df["시장구분"] if "시장구분" in df.columns else "Unknown"
    })

def get_ohlcv(code, count):
    url = "https://fchart.stock.naver.com/sise.nhn"
    params = {"symbol": code, "timeframe": "day", "count": str(count), "requestType": "0"}
    try:
        xml = safe_get(url, params)
        soup = BeautifulSoup(xml, "lxml-xml")
        items = soup.find_all("item")
        if not items: return None
        rows = []
        for it in items:
            d = it["data"].split("|")
            rows.append({"Date": pd.to_datetime(d[0]), "Open": int(d[1]), "High": int(d[2]),
                         "Low":  int(d[3]), "Close": int(d[4]), "Volume": int(d[5])})
        return pd.DataFrame(rows).sort_values("Date").set_index("Date")
    except: return None

def get_ohlcv_retry(code, count, retry):
    for _ in range(retry + 1):
        df = get_ohlcv(code, count)
        if df is not None and not df.empty: return df
        time.sleep(0.3)
    return None

# =========================
# 3. 기술적 분석 조건 (찬희님 오리지널 로직)
# =========================
def has_vol_spike(df):
    rv = df.tail(LOOKBACK_20 + 2)
    r1 = rv["Volume"] / rv["Volume"].shift(1)
    r2 = rv["Volume"] / rv["Volume"].shift(2)
    return ((r1 >= VOL_RATIO_THRESHOLD) | (r2 >= VOL_RATIO_THRESHOLD)).iloc[2:].any()

def ma(series, n): return series.rolling(n).mean()

def ichimoku_calc(df, n):
    return (df["High"].rolling(n).max() + df["Low"].rolling(n).min()) / 2

def check_all_conditions(df):
    if len(df) < 260: return False
    
    # A) 거래대금
    turnover20 = (df.tail(20)["Close"] * df.tail(20)["Volume"]).max()
    last_turnover = df.iloc[-1]["Close"] * df.iloc[-1]["Volume"]
    if turnover20 < TURNOVER_MAX_20_THRESHOLD or last_turnover < LAST_TURNOVER_THRESHOLD:
        return False

    # B) 거래량 스파이크
    if not has_vol_spike(df): return False

    # C) 이평선 정배열 & 종가 위치
    c = df["Close"]
    ma5, ma20, ma60 = ma(c, 5), ma(c, 20), ma(c, 60)
    ma120, ma240 = ma(c, 120), ma(c, 240)
    if not (ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]) or not (c.iloc[-1] > ma5.iloc[-1]):
        return False

    # D) 장기선 기울기
    lb = SLOPE_LOOKBACK_DAYS
    if not (ma120.iloc[-1] > ma120.iloc[-(lb+1)] and ma240.iloc[-1] > ma240.iloc[-(lb+1)]):
        return False

    # E) 120일 신고가 근접
    if df["Close"].tail(20).max() < df["Close"].tail(120).max():
        return False

    # F) 일목균형표 조건
    tenkan = ichimoku_calc(df, ICHIMOKU_TENKAN)
    kijun  = ichimoku_calc(df, ICHIMOKU_KIJUN)
    if pd.isna(tenkan.iloc[-1]) or pd.isna(kijun.iloc[-1]): return False
    if not (tenkan.iloc[-1] > kijun.iloc[-1]) or not (c.iloc[-1] > tenkan.iloc[-1]):
        return False

    return True

# =========================
# 4. 메인 실행부
# =========================
def main():
    start_time = time.time()
    listing = get_listing()
    print(f"[INFO] 대상 종목 수: {len(listing)} | 스캔 시작...")

    results = []
    for i, row in listing.iterrows():
        code, name, market = row["Code"], row["Name"], row["Market"]
        df = get_ohlcv_retry(code, FULL_COUNT, RETRY_FULL)
        
        if df is not None and check_all_conditions(df):
            turnover20 = to_eok((df.tail(20)["Close"] * df.tail(20)["Volume"]).max())
            last_turnover = to_eok(df.iloc[-1]["Close"] * df.iloc[-1]["Volume"])
            
            results.append({
                "종목코드": code, "종목명": name, "시장": market,
                "최근20일최대거래대금(억)": turnover20,
                "최근거래일거래대금(억)": last_turnover
            })

        if (i + 1) % 100 == 0:
            print(f"[PROGRESS] {i+1}/{len(listing)} 완료 | 포착: {len(results)}개")
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

    if results:
        out = pd.DataFrame(results).sort_values("최근거래일거래대금(억)", ascending=False).reset_index(drop=True)
        path = os.path.join(OUT_DIR, f"final_result_{today_yyyymmdd()}.csv")
        out.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"\n[DONE] {len(out)}개 종목 포착 완료: {path}")
    else:
        print("\n[RESULT] 포착된 종목이 없습니다.")
    
    print(f"[INFO] 소요 시간: {round((time.time() - start_time)/60, 1)}분")

if __name__ == "__main__":
    main()