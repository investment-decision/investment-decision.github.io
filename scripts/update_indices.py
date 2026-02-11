import pandas as pd
import yfinance as yf
from fredapi import Fred
import json
import os
from datetime import datetime, timedelta

# 1. Configuration
FRED_API_KEY = os.environ.get('FRED_API_KEY')
DATA_PATH = 'data/market_indices.json'
Z_SCORE_WINDOW = 252  # 1 year for Z-Scores
SENTIMENT_WINDOW = 504 # 2 years for Min-Max Scaling (Sentiment)

def get_z_score(series, window):
    """Calculate Z-Score using rolling mean and std"""
    roll_mean = series.rolling(window=window).mean()
    roll_std = series.rolling(window=window).std()
    z_score = (series - roll_mean) / roll_std
    return z_score

def get_min_max_score(series, window, inverse=False):
    """
    Calculate Min-Max Score (0-100) based on rolling window.
    If inverse=True, higher values get lower scores (for Fear indicators).
    """
    min_val = series.rolling(window=window, min_periods=window//2).min()
    max_val = series.rolling(window=window, min_periods=window//2).max()
    
    # Avoid division by zero
    denominator = max_val - min_val
    denominator = denominator.replace(0, 1) # Prevent div by zero
    
    score = 100 * (series - min_val) / denominator
    
    if inverse:
        score = 100 - score
        
    return score

def fetch_market_data(fred):
    # --- A. Data Collection Setup (Last 3 years to ensure 2-year lookback) ---
    start_date = (datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d')
    
    # 1. Fetch FRED Data
    print("Fetching FRED data...")
    try:
        # Macro
        pmi_series = fred.get_series('IPMAN', observation_start=start_date) # Industrial Production
        inf_exp_series = fred.get_series('T5YIFR', observation_start=start_date) # 5Y Inflation Expectation
        
        # Liquidity
        walcl = fred.get_series('WALCL', observation_start=start_date) # Fed Assets
        tga = fred.get_series('WTREGEN', observation_start=start_date) # TGA
        rrp = fred.get_series('RRPONTSYD', observation_start=start_date) # Reverse Repo
        
        # Sentiment Components (FRED)
        junk_spread = fred.get_series('BAMLH0A0HYM2', observation_start=start_date)
        
        # Leading Components (FRED)
        yield10 = fred.get_series('DGS10', observation_start=start_date)
        yield2 = fred.get_series('DGS2', observation_start=start_date)
        
    except Exception as e:
        print(f"Error fetching FRED data: {e}")
        return None
    
    # 2. Fetch Yahoo Finance Data
    print("Fetching Yahoo Finance data...")
    tickers = [
        'XLY', 'XLI', 'XLB', 'XLK', 'XLP', 'XLV', 'XLU', 'DBC', 
        'SPY', 'TLT', '^VIX',
        'HG=F', 'GC=F', 'SPHB', 'SPLV'
    ]

    data = yf.download(tickers, start=start_date, progress=False, threads=False)

    if isinstance(data.columns, pd.MultiIndex):
        if 'Adj Close' in data.columns.get_level_values(0):
            df = data['Adj Close']
        else:
            df = data['Close']
    else:
        df = data['Adj Close'] if 'Adj Close' in data.columns else data

    required_tickers = ['XLY', 'XLI', 'XLB', 'XLK', 'XLP', 'XLV', 'XLU', 'DBC', 'SPY', 'TLT', '^VIX']
    leading_tickers = ['HG=F', 'GC=F', 'SPHB', 'SPLV']
    all_required = required_tickers + leading_tickers
    
    missing = [t for t in all_required if t not in df.columns]
    
    if missing:
        print(f"Warning: Missing data for tickers: {missing}")
        if 'SPY' in missing or '^VIX' in missing:
             print("Critical tickers missing for Sentiment Index. Aborting.")
             return None
    
    # --- B. Preprocessing & Merging ---
    df.index = df.index.normalize()
    
    # FRED Data Merge
    df['PMI'] = pmi_series.resample('D').ffill().reindex(df.index).ffill()
    df['T5YIFR'] = inf_exp_series.reindex(df.index).ffill()
    
    s_walcl = walcl.resample('D').ffill().reindex(df.index).ffill()
    s_tga = tga.resample('D').ffill().reindex(df.index).ffill()
    s_rrp = rrp.reindex(df.index).ffill()
    
    df['Junk_Spread'] = junk_spread.reindex(df.index).ffill()
    df['DGS10'] = yield10.reindex(df.index).ffill()
    df['DGS2'] = yield2.reindex(df.index).ffill()

    # --- C. Index Calculation ---
    
    # 1. Macro
    cyclical = df['XLY'] + df['XLI'] + df['XLB'] + df['XLK']
    defensive = df['XLP'] + df['XLV'] + df['XLU']
    df['Cyc_Def_Ratio'] = cyclical / defensive
    
    # 2. Liquidity
    df['Net_Liquidity_Raw'] = s_walcl - s_tga - s_rrp

    # 3. Composite Sentiment
    spy_125ma = df['SPY'].rolling(window=125).mean()
    df['Sent_Momentum_Raw'] = (df['SPY'] - spy_125ma) / spy_125ma
    df['Sent_VIX_Raw'] = df['^VIX']
    
    spy_ret_20 = df['SPY'].pct_change(20)
    tlt_ret_20 = df['TLT'].pct_change(20)
    df['Sent_SafeHaven_Raw'] = spy_ret_20 - tlt_ret_20
    
    # 4. Leading
    if 'HG=F' in df.columns and 'GC=F' in df.columns:
        df['Lead_CopperGold_Raw'] = df['HG=F'] / df['GC=F']
    else:
        df['Lead_CopperGold_Raw'] = pd.NA
        
    if 'SPHB' in df.columns and 'SPLV' in df.columns:
        df['Lead_BetaVol_Raw'] = df['SPHB'] / df['SPLV']
    else:
        df['Lead_BetaVol_Raw'] = pd.NA
        
    df['Lead_YieldSpread_Raw'] = df['DGS10'] - df['DGS2']

    # --- D. Normalization ---
    df = df.ffill()

    df['Z_PMI'] = get_z_score(df['PMI'], Z_SCORE_WINDOW)
    df['Z_Ratio'] = get_z_score(df['Cyc_Def_Ratio'], Z_SCORE_WINDOW)
    
    # --- Inflation: Use Rate of Change (RoC) to capture momentum ---
    # Calculate 1-Year RoC (252 trading days)
    df['T5YIFR_RoC'] = df['T5YIFR'].pct_change(periods=252)
    df['Commodity_RoC'] = df['DBC'].pct_change(periods=252)
    
    # Normalize the RoC (not the absolute level)
    df['Z_T5YIFR'] = get_z_score(df['T5YIFR_RoC'], Z_SCORE_WINDOW)
    df['Z_Commodity'] = get_z_score(df['Commodity_RoC'], Z_SCORE_WINDOW)
    
    df['Z_Liquidity'] = get_z_score(df['Net_Liquidity_Raw'], Z_SCORE_WINDOW)
    
    df['Z_CopperGold'] = get_z_score(df['Lead_CopperGold_Raw'], Z_SCORE_WINDOW)
    df['Z_BetaVol'] = get_z_score(df['Lead_BetaVol_Raw'], Z_SCORE_WINDOW)
    df['Z_YieldSpread'] = get_z_score(df['Lead_YieldSpread_Raw'], Z_SCORE_WINDOW)
    
    df['Score_Momentum'] = get_min_max_score(df['Sent_Momentum_Raw'], SENTIMENT_WINDOW, inverse=False)
    df['Score_VIX'] = get_min_max_score(df['Sent_VIX_Raw'], SENTIMENT_WINDOW, inverse=True)
    df['Score_SafeHaven'] = get_min_max_score(df['Sent_SafeHaven_Raw'], SENTIMENT_WINDOW, inverse=False)
    df['Score_Junk'] = get_min_max_score(df['Junk_Spread'], SENTIMENT_WINDOW, inverse=True)
    df['Score_PutCall'] = 50.0 # Placeholder
    
    df['Sentiment_Index'] = (
        df['Score_Momentum'] + 
        df['Score_VIX'] + 
        df['Score_SafeHaven'] + 
        df['Score_Junk']
    ) / 4.0
    
    df['Leading_Index'] = (
        df['Z_CopperGold'] + 
        df['Z_BetaVol'] + 
        df['Z_YieldSpread']
    ) / 3.0

    # --- E. Final Indices ---
    df['Growth_Index'] = 0.5 * df['Z_PMI'] + 0.5 * df['Z_Ratio']
    df['Inflation_Index'] = 0.5 * df['Z_T5YIFR'] + 0.5 * df['Z_Commodity']
    df['Liquidity_Index'] = df['Z_Liquidity']

    valid_df = df.dropna(subset=['Growth_Index', 'Sentiment_Index', 'Leading_Index'])
    
    if valid_df.empty:
        print("Error: Not enough data points.")
        return None

    latest = valid_df.iloc[-1]
    
    return {
        "growth": round(latest['Growth_Index'], 2),
        "inflation": round(latest['Inflation_Index'], 2),
        "liquidity": round(latest['Liquidity_Index'], 2),
        "sentiment": round(latest['Sentiment_Index'], 2),
        "leading": round(latest['Leading_Index'], 2),
        
        "z_pmi": round(latest['Z_PMI'], 2),
        "z_ratio": round(latest['Z_Ratio'], 2),
        "z_t5yifr": round(latest['Z_T5YIFR'], 2),
        "z_commodity": round(latest['Z_Commodity'], 2),
        "net_liquidity_raw": round(latest['Net_Liquidity_Raw'], 2),
        
        "score_momentum": round(latest['Score_Momentum'], 1),
        "score_vix": round(latest['Score_VIX'], 1),
        "score_putcall": 50.0,
        "score_safehaven": round(latest['Score_SafeHaven'], 1),
        "score_junk": round(latest['Score_Junk'], 1),
        
        "z_coppergold": round(latest['Z_CopperGold'], 2),
        "z_betavol": round(latest['Z_BetaVol'], 2),
        "z_yieldspread": round(latest['Z_YieldSpread'], 2)
    }

def update_json_file(new_record_list):
    data = []
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                
                # Check format: If it's a list of dicts (Old format), migrate it
                if loaded and isinstance(loaded, list) and len(loaded) > 0 and isinstance(loaded[0], dict):
                    print("Migrating old JSON format (Dict) to new format (List)...")
                    for item in loaded:
                        # Extract in specific order matches new_record_list below
                        row = [
                            item.get('date'),
                            item.get('growth_index'),
                            item.get('inflation_index'),
                            item.get('liquidity_index'),
                            item.get('sentiment_index'),
                            item.get('leading_index'),
                            item.get('z_pmi'),
                            item.get('z_ratio'),
                            item.get('z_t5yifr'),
                            item.get('z_commodity'),
                            item.get('net_liquidity_raw'),
                            item.get('score_momentum'),
                            item.get('score_vix'),
                            item.get('score_putcall'),
                            item.get('score_safehaven'),
                            item.get('score_junk'),
                            item.get('z_coppergold'),
                            item.get('z_betavol'),
                            item.get('z_yieldspread')
                        ]
                        data.append(row)
                else:
                    data = loaded
        except json.JSONDecodeError:
            data = []

    # Remove existing record for same date (index 0)
    # Filter out if date matches new record
    data = [d for d in data if d[0] != new_record_list[0]]
    
    data.append(new_record_list)
    # Sort by date
    data.sort(key=lambda x: x[0])

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(',', ':')) # Minimal separators for smaller file
    print(f"Updated data for {new_record_list[0]}")

if __name__ == "__main__":
    if not FRED_API_KEY:
        print("Error: FRED_API_KEY missing")
        exit(1)
        
    try:
        fred = Fred(api_key=FRED_API_KEY)
        market_data = fetch_market_data(fred)
        
        if market_data:
            # Create record as a List (Array) to save space
            # Order MUST match the migration logic and index.html parsing
            new_record = [
                datetime.now().strftime("%Y-%m-%d"), # 0
                market_data['growth'],               # 1
                market_data['inflation'],            # 2
                market_data['liquidity'],            # 3
                market_data['sentiment'],            # 4
                market_data['leading'],              # 5
                market_data['z_pmi'],                # 6
                market_data['z_ratio'],              # 7
                market_data['z_t5yifr'],             # 8
                market_data['z_commodity'],          # 9
                market_data['net_liquidity_raw'],    # 10
                market_data['score_momentum'],       # 11
                market_data['score_vix'],            # 12
                market_data['score_putcall'],        # 13
                market_data['score_safehaven'],      # 14
                market_data['score_junk'],           # 15
                market_data['z_coppergold'],         # 16
                market_data['z_betavol'],            # 17
                market_data['z_yieldspread']         # 18
            ]
            
            update_json_file(new_record)
        else:
            print("Failed to generate market data.")
            exit(1)
        
    except Exception as e:
        print(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)