# -*- coding: utf-8 -*-
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from pykrx import stock
from lightgbm import LGBMClassifier
import joblib
from datetime import datetime, timedelta
import os
import warnings
import logging
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np

# [엔지니어 조치] 터미널 가독성 확보 및 불필요한 로그 차단
warnings.filterwarnings("ignore")
logging.getLogger("lightgbm").setLevel(logging.ERROR)

# =========================
# 1. 설정 및 경로
# =========================
OUTPUT_DIR = "outputs"
MODEL_NAME = "stock_model.pkl"
TRAIN_YEARS = 6 

def get_latest_selected_stocks():
    """임찬희님의 전략으로 추출된 최신 종목 리스트 로드"""
    try:
        files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("final_result_") and f.endswith(".csv")]
        if not files: return None
        latest_file = sorted(files)[-1]
        print(f"📂 [타겟 확장] '{latest_file}' 기반 2거래일 상승 확률 학습 시작")
        df = pd.read_csv(os.path.join(OUTPUT_DIR, latest_file))
        return [str(code).zfill(6) for code in df['종목코드'].tolist()]
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}"); return None

def extract_ml_features(df, market_df, investor_df=None):
    """
    [통합 고도화 엔진] 
    1. 타겟: 선정일 종가 대비 다음날 '또는' 다다음날 종가 상승 여부 (T+1 or T+2)
    2. 글로벌 퀀트 피처: 변동성 보정 수익률 및 시장 알파
    3. 현대차 패턴: 120일 에너지 갱신 및 3일선 이격 리스크
    """
    try:
        if len(df) < 320: return None
        
        # --- [A. 지표 및 속성 계산] ---
        df['ma3'] = ta.sma(df['Close'], 3)
        df['ma5'] = ta.sma(df['Close'], 5)
        df['ma20'] = ta.sma(df['Close'], 20)
        df['trade_value'] = df['Close'] * df['Volume']
        df['rsi'] = ta.rsi(df['Close'], 14)
        
        df['body'] = abs(df['Close'] - df['Open'])
        df['range'] = df['High'] - df['Low'] + 1e-9
        df['up_shadow'] = (df['High'] - df[['Open', 'Close']].max(axis=1)) / df['range']
        df['is_bull'] = (df['Close'] > df['Open']).astype(int)
        
        # 일목균형표
        conv = (df['High'].rolling(9).max() + df['Low'].rolling(9).min()) / 2
        base = (df['High'].rolling(26).max() + df['Low'].rolling(26).min()) / 2
        
        # 수급 통합
        if investor_df is not None:
            df = df.join(investor_df, how='left').fillna(0)

        # --- [B. 임찬희의 7가지 절대 선정 필터] ---
        cond1 = (df['trade_value'].rolling(20).max() >= 100_000_000_000) & (df['trade_value'] >= 5_000_000_000)
        cond2 = (df['Volume'] >= df['Volume'].shift(1) * 5) | (df['Volume'] >= df['Volume'].shift(2) * 5)
        cond3 = (df['ma5'] > df['ma20']) & (df['Close'] > df['ma5'])
        cond4 = (ta.sma(df['Close'], 120) > ta.sma(df['Close'], 120).shift(5))
        cond5 = (df['Close'].rolling(20).max() >= df['Close'].rolling(120).max())
        cond6 = (conv > base) & (df['Close'] > conv)
        
        is_setup_day = cond1 & cond2 & cond3 & cond4 & cond5 & cond6
        
        # --- [C. 패턴 및 타겟 분석 루프] ---
        processed_list = []
        setup_indices = df.index[is_setup_day]
        
        for idx in setup_indices:
            pos = df.index.get_loc(idx)
            # [수정] 다다음날(T+2)까지 봐야 하므로 pos + 2 범위를 체크
            if pos < 120 or pos + 2 >= len(df): continue
            
            win_hist = df.iloc[pos-120 : pos-20]
            win_recent = df.iloc[pos-19 : pos+1]
            row_data = df.loc[idx].copy()
            
            # 1. 변동성 보정 수익률 (Risk-Adjusted Return)
            volat = win_recent['Close'].pct_change().std() + 1e-9
            ret = (win_recent['Close'].iloc[-1] - win_recent['Close'].iloc[0]) / (win_recent['Close'].iloc[0] + 1e-9)
            row_data['vol_scaled_ret'] = ret / volat
            
            # 2. [현대차 패턴] 에너지 갱신 (120일 거래량 돌파)
            row_data['energy_refresh_ratio'] = win_recent['Volume'].max() / (win_hist['Volume'].max() + 1e-9)
            
            # 3. [이격 리스크] 3일선 이격 vs 몸통
            ma3_dist = abs(row_data['Close'] - row_data['ma3'])
            row_data['ma3_body_risk'] = ma3_dist / (row_data['body'] + 1e-9)
            
            # 4. 수급 및 상대 강도
            if '외국인순매수' in df.columns:
                row_data['foreign_energy'] = win_recent['외국인순매수'].sum() / (win_recent['trade_value'].sum() + 1e-9)
                row_data['inst_energy'] = win_recent['기관순매수'].sum() / (win_recent['trade_value'].sum() + 1e-9)
            
            mkt_pos = market_df.index.get_loc(idx)
            mkt_ret = (market_df.iloc[mkt_pos] - market_df.iloc[mkt_pos-19]) / (market_df.iloc[mkt_pos-19] + 1e-9)
            row_data['market_alpha'] = ret - mkt_ret

            # 5. [핵심 수정] 타겟 설정: 내일 종가 '또는' 다다음날 종가가 오늘보다 높은지
            next_1_close = df.iloc[pos+1]['Close']
            next_2_close = df.iloc[pos+2]['Close']
            row_data['target'] = 1 if (next_1_close > row_data['Close'] or next_2_close > row_data['Close']) else 0
            
            processed_list.append(row_data)
            
        return pd.DataFrame(processed_list).dropna() if processed_list else None
    except Exception as e:
        print(f"Error: {e}"); return None

def train_specialized_model():
    study_list = get_latest_selected_stocks()
    if not study_list: return

    print(f"🚀 [타겟 최적화] 다음날/다다음날 상승 확률 통합 학습 시작")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * (TRAIN_YEARS + 2))
    
    kospi = yf.download("^KS11", start=start_date, end=end_date, progress=False)['Close']
    kosdaq = yf.download("^KQ11", start=start_date, end=end_date, progress=False)['Close']
    if isinstance(kospi, pd.DataFrame): kospi = kospi.iloc[:, 0]
    if isinstance(kosdaq, pd.DataFrame): kosdaq = kosdaq.iloc[:, 0]

    all_data = []
    feature_cols = [
        'vol_scaled_ret', 'energy_refresh_ratio', 'ma3_body_risk', 
        'market_alpha', 'foreign_energy', 'inst_energy'
    ]
    
    for code in study_list:
        try:
            df = yf.download(f"{code}.KS" if int(code) < 900000 else f"{code}.KQ", start=start_date, end=end_date, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            inv_data = stock.get_market_net_purchases_of_equities_by_ticker(start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"), code)
            investor_df = inv_data[['외국인', '기관합계']].rename(columns={'외국인': '외국인순매수', '기관합계': '기관순매수'})
            investor_df.index = pd.to_datetime(investor_df.index)

            target_market = kospi if int(code) < 900000 else kosdaq
            processed_df = extract_ml_features(df, target_market, investor_df)
            if processed_df is not None:
                all_data.append(processed_df[feature_cols + ['target']])
        except: continue

    if not all_data:
        print("❌ 유효 데이터 수집 실패."); return

    train_set = pd.concat(all_data)
    X, y = train_set[feature_cols], train_set['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = LGBMClassifier(n_estimators=3000, learning_rate=0.002, max_depth=12, num_leaves=127, random_state=42, verbosity=-1)
    model.fit(X_train, y_train)
    
    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("\n🧐 [타겟 확장 진단] 피처 기여도 분석:")
    print(importances)
    
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"\n🎯 [최종 검증] 2거래일 상승 예측 정확도: {round(acc * 100, 2)}%")
    
    model.fit(X, y)
    joblib.dump(model, MODEL_NAME)
    print(f"✅ 2일간의 상승 기회를 포착하는 AI 두뇌 저장 완료")

if __name__ == "__main__":
    train_specialized_model()