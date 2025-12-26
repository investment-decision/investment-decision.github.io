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
    # Use min_periods to allow calculation even if we don't have full window yet (at start)
    # but strictly speaking, we need enough history for accuracy.
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
    # Need enough history for 504-day rolling window
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
        # BAMLH0A0HYM2: ICE BofA US High Yield Index Option-Adjusted Spread
        junk_spread = fred.get_series('BAMLH0A0HYM2', observation_start=start_date)
        # PCRVOL: CBOE Total Put/Call Ratio (Note: Data might be delayed/discontinued on FRED sometimes)
        put_call = fred.get_series('PCRVOL', observation_start=start_date)
        
        # Leading Components (FRED)
        # DGS10: 10-Year Treasury Constant Maturity Rate
        # DGS2: 2-Year Treasury Constant Maturity Rate
        yield10 = fred.get_series('DGS10', observation_start=start_date)
        yield2 = fred.get_series('DGS2', observation_start=start_date)
        
    except Exception as e:
        print(f"Error fetching FRED data: {e}")
        return None
    
    # 2. Fetch Yahoo Finance Data
    print("Fetching Yahoo Finance data...")
    # Added SPY (Momentum/SafeHaven), TLT (SafeHaven), ^VIX (Volatility)
    # Added for Leading Index: HG=F (Copper), GC=F (Gold), SPHB (High Beta), SPLV (Low Vol)
    tickers = [
        'XLY', 'XLI', 'XLB', 'XLK', 'XLP', 'XLV', 'XLU', 'DBC', 
        'SPY', 'TLT', '^VIX',
        'HG=F', 'GC=F', 'SPHB', 'SPLV'
    ]

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
    required_tickers = ['XLY', 'XLI', 'XLB', 'XLK', 'XLP', 'XLV', 'XLU', 'DBC', 'SPY', 'TLT', '^VIX']
    # Leading Index specific check
    leading_tickers = ['HG=F', 'GC=F', 'SPHB', 'SPLV']
    
    # Check intersection to allow partial success, but warn
    all_required = required_tickers + leading_tickers
    missing = [t for t in all_required if t not in df.columns]
    
    if missing:
        print(f"Warning: Missing data for tickers: {missing}")
        # If critical tickers are missing, might need to abort or handle carefully
        if 'SPY' in missing or '^VIX' in missing:
             print("Critical tickers missing for Sentiment Index. Aborting.")
             return None
    
    # --- B. Preprocessing & Merging ---
    df.index = df.index.normalize()
    
    # FRED Data Merge
    # Macro
    df['PMI'] = pmi_series.resample('D').ffill().reindex(df.index).ffill()
    df['T5YIFR'] = inf_exp_series.reindex(df.index).ffill()
    
    # Liquidity
    s_walcl = walcl.resample('D').ffill().reindex(df.index).ffill()
    s_tga = tga.resample('D').ffill().reindex(df.index).ffill()
    s_rrp = rrp.reindex(df.index).ffill()
    
    # Sentiment (FRED)
    df['Junk_Spread'] = junk_spread.reindex(df.index).ffill()
    df['Put_Call'] = put_call.reindex(df.index).ffill()
    
    # Leading (FRED)
    df['DGS10'] = yield10.reindex(df.index).ffill()
    df['DGS2'] = yield2.reindex(df.index).ffill()

    # --- C. Index Calculation ---
    
    # 1. Macro (Cyclical / Defensive)
    cyclical = df['XLY'] + df['XLI'] + df['XLB'] + df['XLK']
    defensive = df['XLP'] + df['XLV'] + df['XLU']
    df['Cyc_Def_Ratio'] = cyclical / defensive
    
    # 2. Liquidity
    df['Net_Liquidity_Raw'] = s_walcl - s_tga - s_rrp

    # 3. Composite Sentiment Oscillator (New Implementation)
    # 3.1 Market Momentum: (SPY - 125MA) / 125MA
    spy_125ma = df['SPY'].rolling(window=125).mean()
    df['Sent_Momentum_Raw'] = (df['SPY'] - spy_125ma) / spy_125ma
    
    # 3.2 Market Volatility: VIX
    df['Sent_VIX_Raw'] = df['^VIX']
    
    # 3.3 Put/Call Ratio: Already fetched as 'Put_Call'
    
    # 3.4 Safe Haven Demand: SPY 20d Return - TLT 20d Return
    spy_ret_20 = df['SPY'].pct_change(20)
    tlt_ret_20 = df['TLT'].pct_change(20)
    df['Sent_SafeHaven_Raw'] = spy_ret_20 - tlt_ret_20
    
    # 3.5 Junk Bond Demand: Already fetched as 'Junk_Spread'
    
    # 4. Inter-Market Leading Indicator (IMLI)
    # 4.1 Copper/Gold Ratio
    # Check if we have data for Copper and Gold
    if 'HG=F' in df.columns and 'GC=F' in df.columns:
        df['Lead_CopperGold_Raw'] = df['HG=F'] / df['GC=F']
    else:
        df['Lead_CopperGold_Raw'] = pd.NA
        
    # 4.2 High Beta / Low Volatility
    if 'SPHB' in df.columns and 'SPLV' in df.columns:
        df['Lead_BetaVol_Raw'] = df['SPHB'] / df['SPLV']
    else:
        df['Lead_BetaVol_Raw'] = pd.NA
        
    # 4.3 Yield Curve Spread (10Y - 2Y)
    df['Lead_YieldSpread_Raw'] = df['DGS10'] - df['DGS2']

    # --- D. Normalization ---
    # Fill NaN to allow rolling calculations
    df = df.ffill()

    # Z-Scores for Macro/Liquidity
    df['Z_PMI'] = get_z_score(df['PMI'], Z_SCORE_WINDOW)
    df['Z_Ratio'] = get_z_score(df['Cyc_Def_Ratio'], Z_SCORE_WINDOW)
    df['Z_T5YIFR'] = get_z_score(df['T5YIFR'], Z_SCORE_WINDOW)
    df['Z_Commodity'] = get_z_score(df['DBC'], Z_SCORE_WINDOW)
    df['Z_Liquidity'] = get_z_score(df['Net_Liquidity_Raw'], Z_SCORE_WINDOW)
    
    # Z-Scores for Leading Indicator
    df['Z_CopperGold'] = get_z_score(df['Lead_CopperGold_Raw'], Z_SCORE_WINDOW)
    df['Z_BetaVol'] = get_z_score(df['Lead_BetaVol_Raw'], Z_SCORE_WINDOW)
    df['Z_YieldSpread'] = get_z_score(df['Lead_YieldSpread_Raw'], Z_SCORE_WINDOW)
    
    # Min-Max Scores for Sentiment (Window=504 days approx 2 years)
    # Note: High Momentum = Greed (Score 100)
    df['Score_Momentum'] = get_min_max_score(df['Sent_Momentum_Raw'], SENTIMENT_WINDOW, inverse=False)
    
    # Note: High VIX = Fear (Score 0) -> Inverse
    df['Score_VIX'] = get_min_max_score(df['Sent_VIX_Raw'], SENTIMENT_WINDOW, inverse=True)
    
    # Note: High Put/Call = Fear (Score 0) -> Inverse
    df['Score_PutCall'] = get_min_max_score(df['Put_Call'], SENTIMENT_WINDOW, inverse=True)
    
    # Note: High SafeHaven (Stocks > Bonds) = Greed (Score 100)
    df['Score_SafeHaven'] = get_min_max_score(df['Sent_SafeHaven_Raw'], SENTIMENT_WINDOW, inverse=False)
    
    # Note: High Junk Spread = Fear (Score 0) -> Inverse
    df['Score_Junk'] = get_min_max_score(df['Junk_Spread'], SENTIMENT_WINDOW, inverse=True)
    
    # Composite Sentiment Index (Average of 5)
    df['Sentiment_Index'] = (
        df['Score_Momentum'] + 
        df['Score_VIX'] + 
        df['Score_PutCall'] + 
        df['Score_SafeHaven'] + 
        df['Score_Junk']
    ) / 5.0
    
    # Composite Leading Index (Sum/Average of Z-Scores)
    # Using average to keep scale consistent with other indices
    df['Leading_Index'] = (
        df['Z_CopperGold'] + 
        df['Z_BetaVol'] + 
        df['Z_YieldSpread']
    ) / 3.0

    # --- E. Final Indices ---
    df['Growth_Index'] = 0.5 * df['Z_PMI'] + 0.5 * df['Z_Ratio']
    df['Inflation_Index'] = 0.5 * df['Z_T5YIFR'] + 0.5 * df['Z_Commodity']
    df['Liquidity_Index'] = df['Z_Liquidity']

    # Drop NaNs
    valid_df = df.dropna(subset=['Growth_Index', 'Sentiment_Index', 'Leading_Index'])
    
    if valid_df.empty:
        print("Error: Not enough data points.")
        return None

    latest = valid_df.iloc[-1]
    
    return {
        # Main Indices
        "growth": round(latest['Growth_Index'], 2),
        "inflation": round(latest['Inflation_Index'], 2),
        "liquidity": round(latest['Liquidity_Index'], 2),
        "sentiment": round(latest['Sentiment_Index'], 2),
        "leading": round(latest['Leading_Index'], 2), # New
        
        # Macro Components
        "z_pmi": round(latest['Z_PMI'], 2),
        "z_ratio": round(latest['Z_Ratio'], 2),
        "z_t5yifr": round(latest['Z_T5YIFR'], 2),
        "z_commodity": round(latest['Z_Commodity'], 2),
        
        # Liquidity Component
        "net_liquidity_raw": round(latest['Net_Liquidity_Raw'], 2),
        
        # Sentiment Components (0-100)
        "score_momentum": round(latest['Score_Momentum'], 1),
        "score_vix": round(latest['Score_VIX'], 1),
        "score_putcall": round(latest['Score_PutCall'], 1),
        "score_safehaven": round(latest['Score_SafeHaven'], 1),
        "score_junk": round(latest['Score_Junk'], 1),
        
        # Leading Components
        "z_coppergold": round(latest['Z_CopperGold'], 2),
        "z_betavol": round(latest['Z_BetaVol'], 2),
        "z_yieldspread": round(latest['Z_YieldSpread'], 2)
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
            # Create record
            new_record = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                
                # Indices
                "growth_index": market_data['growth'],
                "inflation_index": market_data['inflation'],
                "liquidity_index": market_data['liquidity'],
                "sentiment_index": market_data['sentiment'],
                "leading_index": market_data['leading'], # New
                
                # Components
                "z_pmi": market_data['z_pmi'],
                "z_ratio": market_data['z_ratio'],
                "z_t5yifr": market_data['z_t5yifr'],
                "z_commodity": market_data['z_commodity'],
                "net_liquidity_raw": market_data['net_liquidity_raw'],
                
                # Sentiment Scores
                "score_momentum": market_data['score_momentum'],
                "score_vix": market_data['score_vix'],
                "score_putcall": market_data['score_putcall'],
                "score_safehaven": market_data['score_safehaven'],
                "score_junk": market_data['score_junk'],
                
                # Leading Components
                "z_coppergold": market_data['z_coppergold'],
                "z_betavol": market_data['z_betavol'],
                "z_yieldspread": market_data['z_yieldspread']
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