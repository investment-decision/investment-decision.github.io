import pandas as pd
import yfinance as yf
from fredapi import Fred
import json
import os
from datetime import datetime

# 1. 설정 (Github Secrets에서 API 키를 받아옵니다)
FRED_API_KEY = os.environ.get('FRED_API_KEY')
DATA_PATH = 'data/market_indices.json'

def fetch_and_calculate():
    # --- A. 데이터 소싱 ---
    fred = Fred(api_key=FRED_API_KEY)
    
    # 예시: FRED 데이터 (GDP, 금리 등)
    # 10년물 국채 금리 (DGS10)
    treasury_10y = fred.get_series('DGS10').iloc[-1] 
    
    # 예시: Yahoo Finance 데이터 (주가, VIX 등)
    # S&P 500(SPY), VIX
    tickers = yf.Tickers("SPY ^VIX")
    spy_price = tickers.tickers['SPY'].history(period="1d")['Close'].iloc[-1]
    vix_price = tickers.tickers['^VIX'].history(period="1d")['Close'].iloc[-1]

    # --- B. 지수 계산 로직 (User의 4가지 지수 공식 적용) ---
    # * 실제 프로젝트에서는 여기에 구체적인 Z-Score 계산 수식을 넣으세요.
    # * 현재는 예시 값입니다.
    
    macro_index = treasury_10y * 10  # 예: 거시경제 지수 로직
    liquidity_index = spy_price / 100 # 예: 유동성 지수 로직
    sentiment_index = 100 - vix_price # 예: 심리 지수 (VIX 역상관)
    leading_index = 50.5              # 예: 선행 지수

    # --- C. 데이터 포맷팅 ---
    new_record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "macro": round(macro_index, 2),
        "liquidity": round(liquidity_index, 2),
        "sentiment": round(sentiment_index, 2),
        "leading": round(leading_index, 2)
    }
    
    return new_record

def update_json_file(new_record):
    data = []
    
    # 기존 데이터 로드 (파일이 있으면)
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []

    # 중복 날짜 방지 (선택 사항)
    data = [d for d in data if d['date'] != new_record['date']]
    
    # 새 데이터 추가
    data.append(new_record)
    
    # 저장
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    print(f"Updated data with: {new_record}")

if __name__ == "__main__":
    if not FRED_API_KEY:
        print("Error: FRED_API_KEY is missing.")
    else:
        record = fetch_and_calculate()
        update_json_file(record)