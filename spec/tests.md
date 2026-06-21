---
current_phase: test
next_phase: execute
---

# Test Cases

**Plan:** /spec/plan.md

## Test Strategy

Scope is the regime quadrant bug and its Phase 2 fix (FR-01, the
Growth/Inflation scatter), not the full 5-phase plan. Python pipeline
logic (`scripts/update_indices.py`) is tested with `pytest` — unit tests
for the pure normalization helpers, integration tests with FRED/Yahoo
Finance mocked out (no network or API key required). Frontend (FR-02,
FR-07) stays manual/visual per the existing Test Strategy in
`spec/features/market-owl-dashboard.md` — no JS test framework exists in
this project and adding one is out of scope for this bug fix.

Run: `pip install -r requirements-dev.txt && pytest test/ -v`

All test cases below were executed against the current (pre-Phase-2)
codebase to confirm they are valid Python and to establish a true TDD
red/green baseline — see the Coverage Matrix for current pass/fail state.

## Unit Tests

### TC-U01: get_z_score on an oscillating series crosses zero
**Requirement:** Phase 2 acceptance criteria (composite indices must not be permanently one-signed)
**Given:** A synthetic 600-day series oscillating sinusoidally around a fixed mean
**When:** `get_z_score(series, window=252)` is applied
**Then:** The resulting z-score series contains both positive and negative values
**File:** `/test/unit/test_update_indices.py::test_get_z_score_oscillating_series_crosses_zero`
**Status:** PASS (existing `get_z_score` already correct for mean-reverting input)

### TC-U02: get_z_score on a constant series (boundary)
**Requirement:** N/A — documents a known gap (zero-std guard, unlike `get_min_max_score`)
**Given:** A 300-day constant series (std = 0)
**When:** `get_z_score` is applied
**Then:** Output is NaN/inf, not an exception
**File:** `/test/unit/test_update_indices.py::test_get_z_score_constant_series_is_nan_not_crash`
**Status:** PASS (documents current behavior; not in scope to fix)

### TC-U03: get_z_score with window larger than series (error scenario)
**Requirement:** N/A — defensive/error-path coverage
**Given:** A 10-day series, window=252
**When:** `get_z_score` is applied
**Then:** Every value is NaN, no exception raised
**File:** `/test/unit/test_update_indices.py::test_get_z_score_window_larger_than_series_is_all_nan`
**Status:** PASS

### TC-U04: Inflation RoC period is 63 trading days
**Requirement:** Phase 2, T2.1 (research.md Option 1, Section F)
**Given:** The `update_indices` module
**When:** Checking for `INFLATION_ROC_PERIOD`
**Then:** It exists and equals `63` (not the current hardcoded `252`)
**File:** `/test/unit/test_update_indices.py::test_inflation_roc_period_is_63_days`
**Status:** FAIL (red) — pins the T2.1 contract; no such constant exists yet

### TC-U05: EMA smoothing reduces noise
**Requirement:** Phase 2, T2.3 (research.md Option 1, Section E)
**Given:** A 120-day series of random daily noise
**When:** `get_ema(series, span=10)` is applied
**Then:** `get_ema` exists, and its mean day-over-day change is smaller than the raw series'
**File:** `/test/unit/test_update_indices.py::test_ema_smoothing_reduces_step_noise`
**Status:** PASS

### TC-U06: GROWTH_RATIO_ROC_PERIOD constant exists (T2.6, follow-up)
**Requirement:** Phase 2, T2.6 — added after the first real-data backfill showed Growth_Index never crossed zero (0/272 real days)
**Given:** The `update_indices` module
**When:** Checking for `GROWTH_RATIO_ROC_PERIOD`
**Then:** It exists and equals `63`
**File:** `/test/unit/test_update_indices.py::test_growth_ratio_roc_period_exists`
**Status:** PASS

### TC-U07: Cyc_Def_Ratio Z-score uses RoC, not raw level (T2.6, follow-up)
**Requirement:** Phase 2, T2.6
**Given:** A synthetic ratio with constant secular drift (~10%/year), mimicking real cyclical-sector outperformance
**When:** Z-scoring the ratio's 63-day RoC (instead of its raw level)
**Then:** The Z-score is near zero (mean-reverting), not permanently positive
**File:** `/test/unit/test_update_indices.py::test_cyc_def_ratio_zscore_uses_roc_not_raw_level`
**Status:** PASS

## Integration Tests

### TC-I01: Synthetic stagflation onset classifies correctly
**Requirement:** Phase 2, T2.5 (backtest acceptance criterion)
**Given:** 800 trading days of mocked FRED/Yahoo Finance data — gentle baseline growth for ~740 days, then a sharp 60-day cyclical-sector selloff plus a commodity/inflation-expectations spike
**When:** `fetch_market_data(fred)` runs end-to-end against the mocks
**Then:** `growth < 0` and `inflation > 0` (Stagflation quadrant)
**File:** `/test/integration/test_regime_quadrant.py::test_synthetic_stagflation_onset_lands_in_stagflation_quadrant`
**Status:** PASS. Post-T2.6, also re-checked the full synthetic history (not just the latest classification): growth now crosses negative on 318/425 valid days (75%), vs 0/425 before T2.6 — confirms the fix produces real bidirectional movement, not just a lucky single classification.

### TC-I02: Live data is not stuck in a single quadrant (regression guard)
**Requirement:** FR-01 — the reported bug
**Given:** The committed `data/market_indices.json`, last 60 records
**When:** Checking the sign of `growth` and `inflation` across those records
**Then:** Not every record shares the same sign on both axes
**File:** `/test/integration/test_regime_quadrant.py::test_live_data_is_not_stuck_in_a_single_quadrant`
**Status:** PASS, confirmed against a real production backfill (`scripts/backfill_indices.py`, run via `weekly_update.yml`'s temporary `backfill` mode): 272 real trading days (2025-05-23 to 2026-06-19) recomputed with the new formula. Inflation crosses zero on 25% of real days (was 1%). Growth crossing zero on real data has NOT yet been re-confirmed after T2.6 — the backfill that produced these numbers predates T2.6; another backfill run is needed to verify T2.6 on real (not just synthetic) data.

## E2E Tests

### TC-E01: Dashboard scatter chart shows multi-quadrant spread (manual)
**Flow:**
1. Open the live dashboard (or local `src/index.html` against a freshly re-run `data/market_indices.json`)
2. Observe the "Macro Regime" scatter chart's trailing 60-point history
**Pass criteria:** Points are not all confined to the "Overheat" (top-right) quadrant; axis auto-scaling (`src/index.js:91-95`) does not clip any point
**Status:** Manual — cannot be automated without a JS test framework (out of scope for this fix; see `spec/features/market-owl-dashboard.md` Test Strategy)

## Coverage Matrix

| Requirement | Test Cases | Status |
|---|---|---|
| FR-01 (scatter quadrant correctness) | TC-I02, TC-E01 | GREEN on real data (Inflation axis); Growth axis fix (T2.6) not yet re-confirmed on real data |
| Phase 2, T2.1 (63-day RoC) | TC-U04 | GREEN |
| Phase 2, T2.3 (EMA smoothing) | TC-U05 | GREEN |
| Phase 2, T2.5 (backtest) | TC-I01 | GREEN (regression guard) |
| Phase 2, T2.6 (Growth RoC follow-up) | TC-U06, TC-U07 | GREEN (synthetic-verified; needs a fresh real-data backfill to confirm) |
| `get_z_score` correctness | TC-U01, TC-U02, TC-U03 | GREEN (pre-existing) |

## Known Gaps

- FR-02 (composite line charts) and FR-07 (responsive layout) are not covered by automated tests — manual checks only, per the existing project Test Strategy. No JS test framework exists in this repo; adding one is out of scope for this bug fix.
- T2.6 was discovered via a real production backfill, not anticipated when this file was first locked. Reopened here to document the follow-up fix and its tests, consistent with the SDD validate→execute feedback loop. The constant rename from `INFLATION_ROC_PERIOD`-only to a parallel `GROWTH_RATIO_ROC_PERIOD` was the minimal fix; no other formula inputs were touched.
- A second real-data backfill is still needed to confirm T2.6 the same way T2.1/T2.3 were confirmed (TC-I02 passing was measured BEFORE T2.6 shipped — only proves Inflation's fix, not Growth's).
- Sentiment/Liquidity index changes (research.md Option 1, Sections C/D) are explicitly out of scope for this phase (deferred to Phase 6) and have no tests here.

---
test_status: locked
locked_at: 2026-06-21T01:47:08Z
