import pandas as pd
import yfinance as yf
from fredapi import Fred
import json
import os
from datetime import datetime, timedelta

# 1. 설정
FRED_API_KEY = os.environ.get('FRED_API_KEY')
DATA_PATH = 'data/market_indices.json'
Z_SCORE_WINDOW = 252  # 1년 기준

def get_z_score(series, window):
    """이동 평균 및 표준편차를 이용한 Z-Score 계산"""
    roll_mean = series.rolling(window=window).mean()
    roll_std = series.rolling(window=window).std()
    z_score = (series - roll_mean) / roll_std
    return z_score

def fetch_market_data(fred):
    # --- A. 데이터 수집 설정 (최근 2.5년치) ---
    start_date = (datetime.now() - timedelta(days=365*2.5)).strftime('%Y-%m-%d')
    
    # 1. FRED 데이터 가져오기 (거시경제 + 유동성)
    print("Fetching FRED data...")
    # (1) 거시경제 지표
    pmi_series = fred.get_series('IPMAN', observation_start=start_date)
    inf_exp_series = fred.get_series('T5YIFR', observation_start=start_date)
    
    # (2) 유동성 지표 (새로 추가된 부분)
    # WALCL: 연준 총자산 (주간)
    # WTREGEN: 재무부 일반계정 TGA (주간)
    # RRPONTSYD: 역레포 RRP (일간)
    walcl = fred.get_series('WALCL', observation_start=start_date)
    tga = fred.get_series('WTREGEN', observation_start=start_date)
    rrp = fred.get_series('RRPONTSYD', observation_start=start_date)
    
    # 2. Yahoo Finance 데이터 가져오기 (주가, 원자재)
    print("Fetching Yahoo Finance data...")
    tickers = ['XLY', 'XLI', 'XLB', 'XLK', 'XLP', 'XLV', 'XLU', 'DBC']
    yf_data = yf.download(tickers, start=start_date, progress=False)['Close']
    
    # --- B. 데이터 전처리 및 병합 ---
    df = pd.DataFrame(index=yf_data.index)
    
    # FRED 데이터 일간 변환 및 병합
    # Timezone 문제 방지를 위해 normalize() 사용
    df.index = df.index.normalize()

    # Series들을 DataFrame에 맞게 리샘플링 및 병합
    # 거시경제
    df['PMI'] = pmi_series.resample('D').ffill().reindex(df.index).ffill()
    df['T5YIFR'] = inf_exp_series.reindex(df.index).ffill()
    
    # 유동성 (주간 데이터는 일간으로 ffill)
    s_walcl = walcl.resample('D').ffill().reindex(df.index).ffill()
    s_tga = tga.resample('D').ffill().reindex(df.index).ffill()
    s_rrp = rrp.reindex(df.index).ffill()

    # --- C. 지수 계산 로직 ---
    
    # 1. 거시경제 (Macro)
    cyclical = df['XLY'] + df['XLI'] + df['XLB'] + df['XLK']
    defensive = df['XLP'] + df['XLV'] + df['XLU']
    df['Cyc_Def_Ratio'] = cyclical / defensive
    
    # 2. 유동성 (Liquidity) - [요청하신 로직 반영]
    # Net Liquidity = Fed Balance Sheet - TGA - RRP
    df['Net_Liquidity_Raw'] = s_walcl - s_tga - s_rrp

    # --- D. Z-Score 정규화 (표준화) ---
    # 각 지표를 동일한 스케일로 변환
    df['Z_PMI'] = get_z_score(df['PMI'], Z_SCORE_WINDOW)
    df['Z_Ratio'] = get_z_score(df['Cyc_Def_Ratio'], Z_SCORE_WINDOW)
    df['Z_T5YIFR'] = get_z_score(df['T5YIFR'], Z_SCORE_WINDOW)
    df['Z_Commodity'] = get_z_score(df['DBC'], Z_SCORE_WINDOW)
    
    # 유동성 지수도 Z-Score로 변환
    df['Z_Liquidity'] = get_z_score(df['Net_Liquidity_Raw'], Z_SCORE_WINDOW)
    
    # --- E. 최종 인덱스 산출 ---
    df['Growth_Index'] = 0.5 * df['Z_PMI'] + 0.5 * df['Z_Ratio']
    df['Inflation_Index'] = 0.5 * df['Z_T5YIFR'] + 0.5 * df['Z_Commodity']
    # 유동성 지수는 Z-Score 자체를 사용 (필요시 가중치 부여 가능)
    df['Liquidity_Index'] = df['Z_Liquidity']

    # 최신 데이터 추출
    latest = df.iloc[-1]
    
    return {
        # 메인 지수
        "growth": round(latest['Growth_Index'], 2),
        "inflation": round(latest['Inflation_Index'], 2),
        "liquidity": round(latest['Liquidity_Index'], 2), # 추가됨
        
        # 세부 구성 요소 (Growth & Inflation)
        "z_pmi": round(latest['Z_PMI'], 2),
        "z_ratio": round(latest['Z_Ratio'], 2),
        "z_t5yifr": round(latest['Z_T5YIFR'], 2),
        "z_commodity": round(latest['Z_Commodity'], 2),
        
        # 세부 구성 요소 (Liquidity)
        "net_liquidity_raw": round(latest['Net_Liquidity_Raw'], 2) # 실제 금액(백만 달러)
    }

def update_json_file(new_record):
    data = []
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []

    # 중복 날짜 처리
    data = [d for d in data if d['date'] != new_record['date']]
    data.append(new_record)
    data.sort(key=lambda x: x['date'])

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"Updated data for {new_record['date']}")

if __name__ == "__main__":
    if not FRED_API_KEY:
        print("Error: FRED_API_KEY missing")
        exit(1)
        
    try:
        fred = Fred(api_key=FRED_API_KEY)
        market_data = fetch_market_data(fred)
        
        # JSON 저장 구조
        new_record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            # Main Indices
            "growth_index": market_data['growth'],
            "inflation_index": market_data['inflation'],
            "liquidity_index": market_data['liquidity'], # 추가됨
            
            # Components
            "z_pmi": market_data['z_pmi'],
            "z_ratio": market_data['z_ratio'],
            "z_t5yifr": market_data['z_t5yifr'],
            "z_commodity": market_data['z_commodity'],
            "net_liquidity_raw": market_data['net_liquidity_raw']
        }
        
        update_json_file(new_record)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)