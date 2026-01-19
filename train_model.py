# -*- coding: utf-8 -*-
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from lightgbm import LGBMClassifier
import joblib
from datetime import datetime, timedelta
import os
import warnings
import logging 
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# 워닝 및 로그 제어 (깨끗한 터미널 출력 유지)
warnings.filterwarnings("ignore")
logging.getLogger("lightgbm").setLevel(logging.ERROR) 

# =========================
# 1. 설정 및 경로
# =========================
OUTPUT_DIR = "outputs"
MODEL_NAME = "stock_model.pkl"
LOG_NAME = "model_history.csv" 
TRAIN_YEARS = 5

def get_latest_selected_stocks():
    """outputs 폴더에서 가장 최근에 선정된 종목 리스트를 가져옵니다."""
    try:
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            return None
            
        files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("final_result_") and f.endswith(".csv")]
        if not files:
            return None
        
        latest_file = sorted(files)[-1]
        print(f"📂 [시스템] 최신 선정 파일 분석 중: {latest_file}")
        df = pd.read_csv(os.path.join(OUTPUT_DIR, latest_file))
        return [str(code).zfill(6) for code in df['종목코드'].tolist()]
    except Exception as e:
        print(f"❌ [에러] 파일 읽기 실패: {e}")
        return None

def extract_ml_features(df, market_df, nasdaq_df, vix_df, dxy_df, tnx_df, gold_df):
    """
    [최종 진화] 국채 금리, 금 선물, 요일 데이터까지 포함한 초고도화 피처 로직
    """
    try:
        if len(df) < 60: return None 
        
        # 1. 개별 종목 기술적 지표 (RSI, 볼린저밴드, 이평선)
        df['rsi'] = ta.rsi(df['Close'], length=14)
        bb = ta.bbands(df['Close'], length=20, std=2)
        l_col = [c for c in bb.columns if 'BBL' in c][0]
        u_col = [c for c in bb.columns if 'BBU' in c][0]
        df['bb_per'] = (df['Close'] - bb[l_col]) / (bb[u_col] - bb[l_col])
        
        ma5, ma20 = ta.sma(df['Close'], 5), ta.sma(df['Close'], 20)
        df['ma_diff'] = (ma5 - ma20) / ma20
        
        # 2. 수급 및 거래량 패턴
        vol_up = (df['Volume'] > df['Volume'].shift(1)).astype(int)
        df['vol_consecutive_days'] = vol_up.groupby((vol_up != vol_up.shift()).cumsum()).cumsum()
        df['vol_spike_ratio'] = df['Volume'] / ta.sma(df['Volume'], 20)
        
        # 3. 캔들 분석 및 시장 대비 상대 강도
        df['candle_body'] = (df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-9)
        df = df.join(market_df.rename("market_close"), how='left')
        df['relative_strength'] = df['Close'].pct_change(5) - df['market_close'].pct_change(5)
        
        # 4. 모멘텀 및 변동성
        macd = ta.macd(df['Close'])
        df['macd_hist'] = macd['MACDh_12_26_9']
        df['mfi'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        df['atr_ratio'] = ta.atr(df['High'], df['Low'], df['Close'], length=14) / df['Close']

        # 5. 스토케스틱 및 이격도
        stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=14, d=3, smooth_k=3)
        df['stoch_k'] = stoch['STOCHk_14_3_3']
        ma60 = ta.sma(df['Close'], 60)
        df['disparity_60'] = (df['Close'] / ma60) * 100
        
        # 6. 가격 변동폭 및 거래대금 가속도
        df['price_range'] = (df['High'] - df['Low']) / df['Close']
        df['vol_roc'] = ta.roc(df['Volume'], length=5)

        # 7. [추가] 요일 피처 (월=0, 금=4) - 요일별 심리 패턴 반영
        df['day_of_week'] = df.index.dayofweek

        # 8. [매크로 피처] 나스닥, VIX, 달러, 국채금리, 금 선물 수익률
        df = df.join(nasdaq_df.rename("nasdaq_return"), how='left')
        df = df.join(vix_df.rename("vix_close"), how='left')
        df = df.join(dxy_df.rename("dxy_return"), how='left')
        df = df.join(tnx_df.rename("tnx_close"), how='left')
        df = df.join(gold_df.rename("gold_return"), how='left')
        
        return df.dropna()
    except Exception:
        return None

def save_training_log(accuracy, feature_list):
    """학습 결과를 CSV 파일에 누적 기록하여 성능을 추적합니다."""
    log_data = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'accuracy': round(accuracy * 100, 2),
        'feature_count': len(feature_list),
        'features': ", ".join(feature_list)
    }
    df_log = pd.DataFrame([log_data])
    if not os.path.exists(LOG_NAME):
        df_log.to_csv(LOG_NAME, index=False, encoding='utf-8-sig')
    else:
        df_log.to_csv(LOG_NAME, mode='a', header=False, index=False, encoding='utf-8-sig')
    print(f"📝 [기록] 학습 결과가 {LOG_NAME}에 업데이트되었습니다.")

def train_specialized_model():
    """초고도화 패턴 분석 및 모델 학습 실행 루틴"""
    study_list = get_latest_selected_stocks()
    if not study_list:
        print("⚠️ [알림] 선정된 종목 리스트가 없습니다.")
        return

    print(f"🚀 [진행] {len(study_list)}개 종목 + 글로벌 거시지표 풀패키지 학습 시작")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * TRAIN_YEARS)
    
    # 데이터 다운로드 (종합)
    kospi_data = yf.download("^KS11", start=start_date, end=end_date, progress=False)['Close']
    kosdaq_data = yf.download("^KQ11", start=start_date, end=end_date, progress=False)['Close']
    nasdaq_data = yf.download("^IXIC", start=start_date, end=end_date, progress=False)['Close']
    vix_data = yf.download("^VIX", start=start_date, end=end_date, progress=False)['Close']
    dxy_data = yf.download("DX-Y.NYB", start=start_date, end=end_date, progress=False)['Close']
    tnx_data = yf.download("^TNX", start=start_date, end=end_date, progress=False)['Close'] # 10년물 금리
    gold_data = yf.download("GC=F", start=start_date, end=end_date, progress=False)['Close'] # 금 선물
    
    nasdaq_return = nasdaq_data.pct_change()
    dxy_return = dxy_data.pct_change()
    gold_return = gold_data.pct_change()
    
    # 데이터 정리 함수
    def clean_ser(ser):
        return ser.iloc[:, 0] if isinstance(ser, pd.DataFrame) else ser

    kospi_data = clean_ser(kospi_data)
    kosdaq_data = clean_ser(kosdaq_data)
    nasdaq_return = clean_ser(nasdaq_return)
    vix_data = clean_ser(vix_data)
    dxy_return = clean_ser(dxy_return)
    tnx_data = clean_ser(tnx_data)
    gold_return = clean_ser(gold_return)
    
    all_data = []
    feature_columns = [
        'rsi', 'bb_per', 'ma_diff', 'vol_consecutive_days', 'vol_spike_ratio', 
        'candle_body', 'relative_strength', 'macd_hist', 'mfi', 'atr_ratio',
        'stoch_k', 'disparity_60', 'price_range', 'vol_roc', 'day_of_week',
        'nasdaq_return', 'vix_close', 'dxy_return', 'tnx_close', 'gold_return'
    ]
    
    for code in study_list:
        is_kospi = code.startswith(('0', '1', '2'))
        ticker = f"{code}.KS" if is_kospi else f"{code}.KQ"
        target_market = kospi_data if is_kospi else kosdaq_data
        
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            processed_df = extract_ml_features(df, target_market, nasdaq_return, vix_data, dxy_return, tnx_data, gold_return)
            if processed_df is not None:
                # 타겟: 내일 종가가 오늘보다 상승하면 1
                processed_df['target'] = (processed_df['Close'].shift(-1) > processed_df['Close']).astype(int)
                all_data.append(processed_df[feature_columns + ['target']].dropna())
        except Exception:
            continue

    if not all_data:
        print("❌ [에러] 학습 데이터 부족")
        return

    train_set = pd.concat(all_data)
    X, y = train_set[feature_columns], train_set['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print(f"📊 [분석] 총 {len(train_set)}개의 매매 패턴 학습 중 (글로벌 매크로 변수 통합)...")
    
    # 최종 최적화 하이퍼파라미터
    model = LGBMClassifier(
        n_estimators=700, 
        learning_rate=0.007, 
        max_depth=9,
        num_leaves=63, 
        min_child_samples=30, 
        random_state=42, 
        verbosity=-1
    )
    
    model.fit(X_train, y_train)
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"\n🎯 [결과] AI 최종 초고도화 정확도: {round(acc * 100, 2)}%")
    
    # 중요도 분석
    importances = pd.DataFrame({
        'Feature': feature_columns,
        'Importance': model.feature_importances_
    }).sort_values(by='Importance', ascending=False)
    
    print("\n🔍 [분석] 어떤 지표가 가장 중요했나요? (Top 10)")
    print(importances.head(10).to_string(index=False))
    print("-" * 50)
    
    save_training_log(acc, feature_columns)
    model.fit(X, y)
    joblib.dump(model, MODEL_NAME)
    print(f"✅ [완료] 전 세계 매크로가 통합된 최강 모델 저장 완료")

if __name__ == "__main__":
    train_specialized_model()