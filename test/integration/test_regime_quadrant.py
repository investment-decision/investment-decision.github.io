"""Integration tests for the Growth/Inflation regime quadrant calculation.

These exercise scripts/update_indices.py end-to-end (fetch_market_data),
with FRED and Yahoo Finance calls mocked out so no network/API key is
required.

Run: pytest test/integration/test_regime_quadrant.py -v
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import update_indices as ui  # noqa: E402


def _build_synthetic_market(days=800, selloff_days=60):
    """800 trading days: a long, gently-rising baseline followed by a
    sharp cyclical-sector selloff + commodity/inflation spike in the
    final `selloff_days` — a synthetic 'stagflation onset' scenario.
    """
    idx = pd.bdate_range("2023-01-02", periods=days)
    t = np.arange(days)

    baseline_growth = 0.0006   # daily drift, cyclical sectors
    baseline_defensive = 0.0003  # daily drift, defensive sectors

    cyc_drift = np.where(t < days - selloff_days, baseline_growth, -0.004)
    def_drift = np.where(t < days - selloff_days, baseline_defensive, 0.0005)

    cyc_log_price = np.cumsum(cyc_drift)
    def_log_price = np.cumsum(def_drift)

    cyclical_tickers = ["XLY", "XLI", "XLB", "XLK"]
    defensive_tickers = ["XLP", "XLV", "XLU"]

    prices = {}
    for tkr in cyclical_tickers:
        prices[tkr] = 100 * np.exp(cyc_log_price)
    for tkr in defensive_tickers:
        prices[tkr] = 100 * np.exp(def_log_price)

    # Commodities (DBC) + broad market (SPY/TLT/VIX) + leading indicators:
    # flat baseline, then a sharp spike in the selloff window (inflation shock)
    commodity_drift = np.where(t < days - selloff_days, 0.0001, 0.006)
    prices["DBC"] = 50 * np.exp(np.cumsum(commodity_drift))
    prices["SPY"] = 100 * np.exp(cyc_log_price * 0.5)
    prices["TLT"] = 100 * np.exp(-cyc_log_price * 0.2)
    prices["^VIX"] = 15 + np.where(t < days - selloff_days, 0, 10)
    prices["HG=F"] = 4 * np.exp(np.cumsum(commodity_drift * 0.5))
    prices["GC=F"] = 1800 * np.exp(np.cumsum(commodity_drift * 0.3))
    prices["SPHB"] = prices["SPY"]
    prices["SPLV"] = prices["TLT"]

    columns = pd.MultiIndex.from_product([["Adj Close"], list(prices.keys())])
    data = pd.DataFrame(
        {("Adj Close", k): v for k, v in prices.items()}, index=idx
    )
    data.columns = columns
    return idx, data


@pytest.fixture
def mocked_fred_and_yfinance(monkeypatch):
    idx, yf_data = _build_synthetic_market()

    fake_fred = MagicMock()
    rng = np.random.default_rng(7)
    t = np.arange(len(idx))

    # Every FRED series needs *some* variation — a constant series has zero
    # rolling std, which makes get_z_score divide by zero and NaN out the
    # whole row (see test_get_z_score_constant_series_is_nan_not_crash).
    # A tiny random walk keeps each series realistic without affecting the
    # directional scenario this test is actually checking.
    def _noisy_walk(level, scale=0.02):
        return level + np.cumsum(rng.normal(0, scale, size=len(idx)))

    series_map = {
        "IPMAN": _noisy_walk(100, scale=0.05),
        "WALCL": _noisy_walk(8_000_000, scale=500),
        "WTREGEN": _noisy_walk(500_000, scale=200),
        "RRPONTSYD": _noisy_walk(1_000_000, scale=300),
        "BAMLH0A0HYM2": _noisy_walk(4.0, scale=0.01),
        "DGS10": _noisy_walk(4.0, scale=0.01),
        "DGS2": _noisy_walk(4.5, scale=0.01),
    }

    def fake_get_series(series_id, observation_start=None):
        if series_id == "T5YIFR":
            # Inflation expectations: flat, then rise sharply in the
            # final 60 days (the same window as the commodity spike).
            vals = np.where(t < len(idx) - 60, 2.2, 2.2 + (t - (len(idx) - 60)) * 0.03)
            return pd.Series(vals, index=idx) + np.cumsum(rng.normal(0, 0.002, size=len(idx)))
        return pd.Series(series_map[series_id], index=idx)

    fake_fred.get_series.side_effect = fake_get_series

    monkeypatch.setattr(ui.yf, "download", lambda *a, **kw: yf_data)

    return fake_fred


def test_synthetic_stagflation_onset_lands_in_stagflation_quadrant(
    mocked_fred_and_yfinance,
):
    """Acceptance criterion for Phase 2 (T2.5 backtest): a sharp, clean
    cyclical-sector selloff combined with a commodity/inflation spike
    should classify as Growth < 0, Inflation > 0 (Stagflation quadrant).

    Verified PASSING against the current (pre-Phase-2) implementation —
    an extreme, clean synthetic shock is large enough to overcome the
    price-level ratio's secular drift. This is intentionally kept as a
    regression guard: Phase 2's refactor (63-day RoC, expanded Growth
    inputs) must not regress the ability to detect an extreme, obvious
    regime shift. The bug this plan exists to fix is NOT "the formula
    never moves" — see test_live_data_is_not_stuck_in_a_single_quadrant
    for the actual failing case: realistic, noisier market moves get
    dampened out by the 252-day windows before they ever cross zero.
    """
    market_data = ui.fetch_market_data(mocked_fred_and_yfinance)

    assert market_data is not None, "fetch_market_data returned None"
    assert market_data["growth"] < 0, (
        f"expected Growth_Index < 0 after a sharp cyclical selloff, "
        f"got {market_data['growth']}"
    )
    assert market_data["inflation"] > 0, (
        f"expected Inflation_Index > 0 after a commodity/inflation-"
        f"expectations spike, got {market_data['inflation']}"
    )


# --- TC-I02: live data regression guard -----------------------------------

def test_live_data_is_not_stuck_in_a_single_quadrant():
    """Regression guard tied directly to the reported bug: the committed
    data/market_indices.json must not have every recent record sitting in
    the same Growth/Inflation quadrant. Currently FAILS — all 49 stored
    records have growth > 0 and inflation > 0. Should PASS once the
    pipeline is re-run after Phase 2 ships.
    """
    data_path = REPO_ROOT / "data" / "market_indices.json"
    with open(data_path) as f:
        records = json.load(f)

    recent = records[-60:]
    growth_signs = {1 if r[1] >= 0 else -1 for r in recent if r[1] is not None}
    inflation_signs = {1 if r[2] >= 0 else -1 for r in recent if r[2] is not None}

    assert not (len(growth_signs) == 1 and len(inflation_signs) == 1), (
        "all recent records share the same Growth AND Inflation sign — "
        "the scatter chart is stuck in a single quadrant"
    )
