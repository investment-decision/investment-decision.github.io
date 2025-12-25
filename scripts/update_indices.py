import pandas as pd
import yfinance as yf
from fredapi import Fred
import json
import os
from datetime import datetime, timedelta

# 1. Configuration
FRED_API_KEY = os.environ.get('FRED_API_KEY')
DATA_PATH = 'data/market_indices.json'
Z_SCORE_WINDOW = 252  # 1 year

def get_z_score(series, window):
    """Calculate Z-Score using rolling mean and std"""
    roll_mean = series.rolling(window=window).mean()
    roll_std = series.rolling(window=window).std()
    z_score = (series - roll_mean) / roll_std
    return z_score

def fetch_market_data(fred):
    # --- A. Data Collection Setup (Last 2.5 years) ---
    start_date = (datetime.now() - timedelta(days=365*2.5)).strftime('%Y-%m-%d')
    
    # 1. Fetch FRED Data
    print("Fetching FRED data...")
    try:
        # Macro
        pmi_series = fred.get_series('IPMAN', observation_start=start_date) # Using Industrial Production as proxy
        inf_exp_series = fred.get_series('T5YIFR', observation_start=start_date)
        
        # Liquidity
        walcl = fred.get_series('WALCL', observation_start=start_date)
        tga = fred.get_series('WTREGEN', observation_start=start_date)
        rrp = fred.get_series('RRPONTSYD', observation_start=start_date)
    except Exception as e:
        print(f"Error fetching FRED data: {e}")
        return None
    
    # 2. Fetch Yahoo Finance Data
    print("Fetching Yahoo Finance data...")
    # Added 'DBC' to tickers
    tickers = ['XLY', 'XLI', 'XLB', 'XLK', 'XLP', 'XLV', 'XLU', 'DBC']

    # threads=False helps avoid rate limits in GitHub Actions
    data = yf.download(tickers, start=start_date, progress=False, threads=False)

    # Handle yfinance MultiIndex
    if isinstance(data.columns, pd.MultiIndex):
        if 'Adj Close' in data.columns.get_level_values(0):
            df = data['Adj Close']
        else:
            df = data['Close']
    else:
        df = data['Adj Close'] if 'Adj Close' in data.columns else data

    # Check for missing columns
    required_tickers = ['XLY', 'XLI', 'XLB', 'XLK', 'XLP', 'XLV', 'XLU', 'DBC']
    missing = [t for t in required_tickers if t not in df.columns]
    
    if missing:
        print(f"Error: Missing data for tickers: {missing}")
        return None 
    
    # --- B. Preprocessing & Merging ---
    # Normalize index to remove time component (00:00:00) for alignment
    df.index = df.index.normalize()
    
    # Convert/Merge FRED data (resample to Daily to match Stock data)
    # Using reindex(df.index) aligns FRED data to the trading days present in Yahoo data
    df['PMI'] = pmi_series.resample('D').ffill().reindex(df.index).ffill()
    df['T5YIFR'] = inf_exp_series.reindex(df.index).ffill()
    
    s_walcl = walcl.resample('D').ffill().reindex(df.index).ffill()
    s_tga = tga.resample('D').ffill().reindex(df.index).ffill()
    s_rrp = rrp.reindex(df.index).ffill()

    # --- C. Index Calculation ---
    
    # 1. Macro (Cyclical / Defensive)
    cyclical = df['XLY'] + df['XLI'] + df['XLB'] + df['XLK']
    defensive = df['XLP'] + df['XLV'] + df['XLU']
    df['Cyc_Def_Ratio'] = cyclical / defensive
    
    # 2. Liquidity
    df['Net_Liquidity_Raw'] = s_walcl - s_tga - s_rrp

    # --- D. Z-Score Normalization ---
    # Ensure no NaN values interfere with rolling calculation
    df = df.ffill()

    df['Z_PMI'] = get_z_score(df['PMI'], Z_SCORE_WINDOW)
    df['Z_Ratio'] = get_z_score(df['Cyc_Def_Ratio'], Z_SCORE_WINDOW)
    df['Z_T5YIFR'] = get_z_score(df['T5YIFR'], Z_SCORE_WINDOW)
    df['Z_Commodity'] = get_z_score(df['DBC'], Z_SCORE_WINDOW)
    df['Z_Liquidity'] = get_z_score(df['Net_Liquidity_Raw'], Z_SCORE_WINDOW)
    
    # --- E. Final Indices ---
    df['Growth_Index'] = 0.5 * df['Z_PMI'] + 0.5 * df['Z_Ratio']
    df['Inflation_Index'] = 0.5 * df['Z_T5YIFR'] + 0.5 * df['Z_Commodity']
    df['Liquidity_Index'] = df['Z_Liquidity']

    # Get the latest VALID data point (drop rows where Z-scores might be NaN due to window)
    valid_df = df.dropna(subset=['Growth_Index', 'Inflation_Index', 'Liquidity_Index'])
    
    if valid_df.empty:
        print("Error: Not enough data points to calculate Z-scores (need > 252 days)")
        return None

    latest = valid_df.iloc[-1]
    
    return {
        "growth": round(latest['Growth_Index'], 2),
        "inflation": round(latest['Inflation_Index'], 2),
        "liquidity": round(latest['Liquidity_Index'], 2),
        
        "z_pmi": round(latest['Z_PMI'], 2),
        "z_ratio": round(latest['Z_Ratio'], 2),
        "z_t5yifr": round(latest['Z_T5YIFR'], 2),
        "z_commodity": round(latest['Z_Commodity'], 2),
        
        "net_liquidity_raw": round(latest['Net_Liquidity_Raw'], 2)
    }

def update_json_file(new_record):
    data = []
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []

    # Remove existing record for the same date to avoid duplicates
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
        
        if market_data:
            # Create record with Today's date (or the date of the latest data)
            new_record = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "growth_index": market_data['growth'],
                "inflation_index": market_data['inflation'],
                "liquidity_index": market_data['liquidity'],
                
                "z_pmi": market_data['z_pmi'],
                "z_ratio": market_data['z_ratio'],
                "z_t5yifr": market_data['z_t5yifr'],
                "z_commodity": market_data['z_commodity'],
                "net_liquidity_raw": market_data['net_liquidity_raw']
            }
            
            update_json_file(new_record)
        else:
            print("Failed to generate market data.")
            exit(1)
        
    except Exception as e:
        print(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)