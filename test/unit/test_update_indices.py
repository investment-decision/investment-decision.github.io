"""Unit tests for the pure normalization helpers in scripts/update_indices.py.

Run: pytest test/unit/test_update_indices.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import update_indices as ui  # noqa: E402


# --- TC-U01: get_z_score happy path -------------------------------------

def test_get_z_score_oscillating_series_crosses_zero():
    """Given a mean-reverting (oscillating) series, the rolling z-score
    should produce both positive and negative values within one window —
    it should NOT get stuck on one side of zero.
    """
    idx = pd.date_range("2023-01-01", periods=600, freq="D")
    # Sine wave oscillating around 100, amplitude 10 — genuinely mean-reverting.
    values = 100 + 10 * np.sin(np.arange(600) * (2 * np.pi / 60))
    series = pd.Series(values, index=idx)

    z = ui.get_z_score(series, window=252)
    z_valid = z.dropna()

    assert (z_valid > 0).any(), "expected at least one positive z-score"
    assert (z_valid < 0).any(), "expected at least one negative z-score"


# --- TC-U02: get_z_score boundary case -----------------------------------

def test_get_z_score_constant_series_is_nan_not_crash():
    """A constant series has zero rolling std. Division by zero should
    surface as NaN (current behavior), not raise. This documents a known
    gap: get_z_score has no zero-std guard, unlike get_min_max_score.
    """
    idx = pd.date_range("2023-01-01", periods=300, freq="D")
    series = pd.Series([50.0] * 300, index=idx)

    z = ui.get_z_score(series, window=252)

    last_valid = z.iloc[-1]
    assert np.isnan(last_valid) or np.isinf(last_valid)


# --- TC-U03: get_z_score error scenario -----------------------------------

def test_get_z_score_window_larger_than_series_is_all_nan():
    """When the window exceeds the series length, every rolling value is
    NaN — no exception should propagate.
    """
    idx = pd.date_range("2023-01-01", periods=10, freq="D")
    series = pd.Series(range(10), index=idx, dtype=float)

    z = ui.get_z_score(series, window=252)

    assert z.isna().all()


# --- TC-U04: Inflation RoC window must be 63 trading days (quarterly) ----

def test_inflation_roc_period_is_63_days():
    """research.md flags the 252-day RoC as 'very slow to react' and the
    plan (Phase 2, T2.1) commits to shortening it to a 63-day (quarterly)
    window. This test pins that contract via a named module constant.

    EXPECTED TO FAIL until Phase 2 T2.1 is implemented — today the period
    is a hardcoded literal `252` inline in fetch_market_data with no
    importable constant.
    """
    assert hasattr(ui, "INFLATION_ROC_PERIOD"), (
        "scripts/update_indices.py must expose INFLATION_ROC_PERIOD as a "
        "module-level constant (Phase 2, T2.1)"
    )
    assert ui.INFLATION_ROC_PERIOD == 63


# --- TC-U05: EMA smoothing helper must exist and smooth a step series ----

def test_ema_smoothing_reduces_step_noise():
    """Phase 2 T2.3 adds a 10-day EMA applied to the final composite
    indices before regime classification. This test pins the contract:
    a `get_ema(series, span)` helper must exist and its output must have
    lower day-over-day volatility than the raw input on a noisy series.

    EXPECTED TO FAIL until Phase 2 T2.3 is implemented.
    """
    assert hasattr(ui, "get_ema"), (
        "scripts/update_indices.py must expose a get_ema(series, span) "
        "helper (Phase 2, T2.3)"
    )

    idx = pd.date_range("2023-01-01", periods=120, freq="D")
    rng = np.random.default_rng(42)
    noisy = pd.Series(rng.normal(loc=0.0, scale=1.0, size=120), index=idx)

    smoothed = ui.get_ema(noisy, span=10)

    raw_vol = noisy.diff().abs().mean()
    smoothed_vol = smoothed.diff().abs().mean()
    assert smoothed_vol < raw_vol


# --- TC-U06: GROWTH_RATIO_ROC_PERIOD constant must exist (Growth fix) ----

def test_growth_ratio_roc_period_exists():
    """Backtesting Phase 2 against real data (272 days, backfilled) showed
    Growth_Index never went negative once — Z_Ratio was being computed on
    Cyc_Def_Ratio's raw price level, which secularly drifts upward
    (cyclicals have outpaced defensives for years), keeping it positive
    almost permanently regardless of actual regime. Fix mirrors what
    already worked for Inflation: Z-score the ratio's RoC, not its level.

    EXPECTED TO FAIL until this follow-up fix is implemented.
    """
    assert hasattr(ui, "GROWTH_RATIO_ROC_PERIOD"), (
        "scripts/update_indices.py must expose GROWTH_RATIO_ROC_PERIOD as "
        "a module-level constant"
    )
    assert ui.GROWTH_RATIO_ROC_PERIOD == 63


def test_cyc_def_ratio_zscore_uses_roc_not_raw_level():
    """A Cyc_Def_Ratio that secularly drifts upward (simulating years of
    cyclical-sector outperformance) should NOT keep Z_Ratio permanently
    positive once it's based on RoC instead of raw level: a ratio that's
    been climbing steadily at a *constant* rate has ~flat RoC, which
    should Z-score close to zero, not strongly positive.
    """
    idx = pd.date_range("2022-01-01", periods=700, freq="B")
    # Steady secular uptrend, ~10%/year compounding — same drift the whole
    # window, so the RATE of change is roughly constant throughout.
    ratio = pd.Series(100 * (1.0004 ** np.arange(700)), index=idx)

    roc = ratio.pct_change(periods=ui.GROWTH_RATIO_ROC_PERIOD)
    z = ui.get_z_score(roc, window=252)

    last_valid = z.dropna().iloc[-1]
    assert abs(last_valid) < 1.0, (
        f"a ratio with constant drift should Z-score near zero on its RoC "
        f"(mean-reverting), got {last_valid}"
    )
