# -*- coding: utf-8 -*-
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from lightgbm import LGBMClassifier
import joblib
from datetime import datetime, timedelta
import os
import warnings

warnings.filterwarnings("ignore")

# =========================
# 1. 설정 및 경로
# =========================
OUTPUT_DIR = "outputs"
MODEL_NAME = "stock_model.pkl"
TRAIN_YEARS = 5

def get_latest_selected_stocks():
    """outputs 폴더에서 가장 최근에 선정된 종목 리스트를 가져옵니다."""
    try:
        files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("final_result_") and f.endswith(".csv")]
        if not files:
            return None
        latest_file = sorted(files)[-1]
        print(f"📂 최신 선정 파일 발견: {latest_file}")
        df = pd.read_csv(os.path.join(OUTPUT_DIR, latest_file))
        # 종목코드 리스트 추출 (6자리 문자열 처리)
        return [str(code).zfill(6) for code in df['종목코드'].tolist()]
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {e}")
        return None

def extract_ml_features(df):
    """찬희님의 선정 로직에 특화된 기술적 지표 추출"""
    try:
        if len(df) < 30: return None
        df['rsi'] = ta.rsi(df['Close'], length=14)
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is None or bb.empty: return None
        l_col = [c for c in bb.columns if 'BBL' in c][0]
        u_col = [c for c in bb.columns if 'BBU' in c][0]
        df['bb_per'] = (df['Close'] - bb[l_col]) / (bb[u_col] - bb[l_col])
        ma5, ma20 = ta.sma(df['Close'], length=5), ta.sma(df['Close'], length=20)
        df['ma_diff'] = (ma5 - ma20) / ma20
        df['vol_ratio'] = df['Volume'] / df['Volume'].shift(1)
        return df.dropna()
    except:
        return None

def train_specialized_model():
    # 1. 오늘 선정된 종목들만 가져오기 (예: 28개 종목)
    study_list = get_latest_selected_stocks()
    
    if not study_list:
        print("❌ 학습할 선정 종목이 없습니다. 스캐너를 먼저 실행하세요.")
        return

    print(f"🚀 총 {len(study_list)}개 선정 종목의 특화 학습을 시작합니다.")
    
    all_data = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * TRAIN_YEARS)
    
    for code in study_list:
        ticker = f"{code}.KS" if code.startswith('0') else f"{code}.KQ"
        print(f"   [집중학습] {ticker} 과거 데이터 수집 중...")
        
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            processed_df = extract_ml_features(df)
            if processed_df is not None:
                # 다음 날 종가가 오를지 학습 데이터(Label) 생성
                processed_df['target'] = (processed_df['Close'].shift(-1) > processed_df['Close']).astype(int)
                all_data.append(processed_df[['rsi', 'bb_per', 'ma_diff', 'vol_ratio', 'target']].dropna())
        except:
            continue

    if not all_data:
        print("❌ 유효한 학습 데이터가 없습니다.")
        return

    # 2. 통합 데이터로 학습
    train_set = pd.concat(all_data)
    print(f"📊 총 {len(train_set)}개의 맞춤형 패턴 발견. 모델 최적화 중...")
    
    X = train_set.drop('target', axis=1)
    y = train_set['target']
    
    model = LGBMClassifier(n_estimators=100, learning_rate=0.05, random_state=42)
    model.fit(X, y)
    
    # 3. 모델 저장
    joblib.dump(model, MODEL_NAME)
    print(f"✅ 오늘 선정 종목 전용 AI 모델 생성 완료: {MODEL_NAME}")

if __name__ == "__main__":
    train_specialized_model()