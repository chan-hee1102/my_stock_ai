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
import streamlit as st
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# 1. 시스템 설정 및 환경 변수 처리
warnings.filterwarnings("ignore")
logging.getLogger("lightgbm").setLevel(logging.ERROR) 

# [핵심 보정] 깃허브 액션과 스트림릿 환경 모두에서 API 키를 충돌 없이 가져오는 최적화 로직
def get_api_key():
    """
    st.secrets 참조 시 발생하는 AttributeError 및 KeyError를 방지하기 위해 
    hasattr 검사와 환경 변수(os.environ) 우선 참조 방식을 결합했습니다.
    """
    # 1순위: 깃허브 액션 환경변수 확인
    api_key = os.environ.get("GROQ_API_KEY")
    
    # 2순위: 깃허브 액션에 없을 경우 스트림릿 Secrets 확인 (보안 검사 포함)
    if not api_key:
        if hasattr(st, "secrets"):
            try:
                api_key = st.secrets.get("GROQ_API_KEY")
            except Exception:
                api_key = None
    
    return api_key.strip() if api_key else ""

# 경로 및 상수 설정
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
    [해결] 시간대(Timezone) 충돌을 방지하며 22개의 피처를 추출하는 엔진
    """
    try:
        if len(df) < 60: return None 
        
        # 모든 데이터의 시간대 정보를 제거하여 병합 에러 방지
        df.index = df.index.tz_localize(None)
        
        # 1. 개별 종목 기술적 지표
        df['rsi'] = ta.rsi(df['Close'], length=14)
        bb = ta.bbands(df['Close'], length=20, std=2)
        l_col = [c for c in bb.columns if 'BBL' in c][0]
        u_col = [c for c in bb.columns if 'BBU' in c][0]
        df['bb_per'] = (df['Close'] - bb[l_col]) / (bb[u_col] - bb[l_col])
        
        ma5, ma20 = ta.sma(df['Close'], 5), ta.sma(df['Close'], 20)
        df['ma_diff'] = (ma5 - ma20) / (ma20 + 1e-9)
        
        # 2. 거래량 및 캔들 분석
        vol_up = (df['Volume'] > df['Volume'].shift(1)).astype(int)
        df['vol_consecutive_days'] = vol_up.groupby((vol_up != vol_up.shift()).cumsum()).cumsum()
        df['vol_spike_ratio'] = df['Volume'] / (ta.sma(df['Volume'], 20) + 1e-9)
        df['candle_body'] = (df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-9)
        
        # 3. 시장 대비 상대 강도 (RS)
        m_series = market_df.squeeze()
        if isinstance(m_series, pd.DataFrame): m_series = m_series.iloc[:, 0]
        m_series.index = m_series.index.tz_localize(None)
        m_series.name = "market_close"
        
        df = df.join(m_series, how='left').ffill()
        df['relative_strength'] = df['Close'].pct_change(5) - df['market_close'].pct_change(5)
        
        # 4. 모멘텀 및 보조 지표
        macd = ta.macd(df['Close'])
        df['macd_hist'] = macd['MACDh_12_26_9']
        df['mfi'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        df['atr_ratio'] = ta.atr(df['High'], df['Low'], df['Close'], length=14) / (df['Close'] + 1e-9)
        
        stoch = ta.stoch(df['High'], df['Low'], df['Close'])
        df['stoch_k'] = stoch['STOCHk_14_3_3']
        df['disparity_60'] = (df['Close'] / (ta.sma(df['Close'], 60) + 1e-9)) * 100
        df['price_range'] = (df['High'] - df['Low']) / (df['Close'] + 1e-9)
        df['vol_roc'] = ta.roc(df['Volume'], length=5)
        df['range_roc'] = ta.roc(df['price_range'], length=5)
        df['day_of_week'] = df.index.dayofweek
        
        # 5. 매크로 데이터 병합
        for ser, name in zip([nasdaq_df, vix_df, dxy_df, tnx_df, gold_df], 
                             ["nasdaq_return", "vix_close", "dxy_return", "tnx_close", "gold_return"]):
            s = ser.squeeze()
            if isinstance(s, pd.DataFrame): s = s.iloc[:, 0]
            s.index = s.index.tz_localize(None)
            s.name = name
            df = df.join(s, how='left').ffill()
            
        # 나스닥 선물 대용값 계산
        df['nasdaq_f_return'] = df['nasdaq_return'].shift(-1).fillna(0)
        
        return df.dropna()
    except Exception as e:
        print(f"⚠️ 지표 추출 중 오류: {e}")
        return None

def save_training_log(accuracy, feature_list):
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

def train_specialized_model():
    study_list = get_latest_selected_stocks()
    api_key = get_api_key() # [보정 적용] 최적화된 키 수집 로직 사용
    
    if not study_list:
        print("⚠️ [알림] 선정된 종목 리스트가 없습니다.")
        return

    print(f"🚀 [진행] {len(study_list)}개 종목 기반 AI 모델 재학습 시작 (v1.7)")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * TRAIN_YEARS)
    
    # 글로벌 매크로 데이터 수집
    tickers = ["^KS11", "^KQ11", "^IXIC", "^VIX", "DX-Y.NYB", "^TNX", "GC=F"]
    macro_raw = yf.download(tickers, start=start_date, end=end_date, progress=False)['Close'].ffill()
    
    kospi = macro_raw['^KS11']
    kosdaq = macro_raw['^KQ11']
    nasdaq_ret = macro_raw['^IXIC'].pct_change()
    vix = macro_raw['^VIX']
    dxy_ret = macro_raw['DX-Y.NYB'].pct_change()
    tnx = macro_raw['^TNX']
    gold_ret = macro_raw['GC=F'].pct_change()
    
    all_data = []
    feature_columns = [
        'rsi', 'bb_per', 'ma_diff', 'vol_consecutive_days', 'vol_spike_ratio', 
        'candle_body', 'relative_strength', 'macd_hist', 'mfi', 'atr_ratio',
        'stoch_k', 'disparity_60', 'price_range', 'vol_roc', 'range_roc',
        'day_of_week', 'nasdaq_return', 'vix_close', 'dxy_return', 'tnx_close', 
        'gold_return', 'nasdaq_f_return'
    ]
    
    for code in study_list:
        ticker = f"{code}.KS" if code.startswith(('0', '1', '2')) else f"{code}.KQ"
        market = kospi if ".KS" in ticker else kosdaq
        
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if df.empty or len(df) < 100: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            p_df = extract_ml_features(df, market, nasdaq_ret, vix, dxy_ret, tnx, gold_ret)
            if p_df is not None:
                p_df['target'] = (p_df['Close'].shift(-1) > p_df['Close']).astype(int)
                all_data.append(p_df[feature_columns + ['target']].dropna())
        except: continue

    if not all_data:
        print("❌ [에러] 유효 데이터 수집 실패. API 키 또는 네트워크 확인.")
        return

    train_set = pd.concat(all_data)
    X, y = train_set[feature_columns], train_set['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = LGBMClassifier(
        n_estimators=1000, learning_rate=0.01, max_depth=10,
        num_leaves=127, min_child_samples=20, random_state=42, verbosity=-1
    )
    
    model.fit(X_train, y_train)
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"\n🎯 [결과] AI 모델 정확도: {round(acc * 100, 2)}% (학습데이터: {len(train_set)}건)")
    
    save_training_log(acc, feature_columns)
    model.fit(X, y)
    joblib.dump(model, MODEL_NAME)
    print(f"✅ [완료] {MODEL_NAME} 갱신 완료.")

if __name__ == "__main__":
    train_specialized_model()