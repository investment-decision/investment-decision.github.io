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
**Status:** FAIL (red) — pins the T2.3 contract; no such helper exists yet

## Integration Tests

### TC-I01: Synthetic stagflation onset classifies correctly
**Requirement:** Phase 2, T2.5 (backtest acceptance criterion)
**Given:** 800 trading days of mocked FRED/Yahoo Finance data — gentle baseline growth for ~740 days, then a sharp 60-day cyclical-sector selloff plus a commodity/inflation-expectations spike
**When:** `fetch_market_data(fred)` runs end-to-end against the mocks
**Then:** `growth < 0` and `inflation > 0` (Stagflation quadrant)
**File:** `/test/integration/test_regime_quadrant.py::test_synthetic_stagflation_onset_lands_in_stagflation_quadrant`
**Status:** PASS — an extreme, clean shock already classifies correctly today. Kept as a Phase 2 regression guard (must not break), not as proof of the bug — see TC-I02 for that.

### TC-I02: Live data is not stuck in a single quadrant (regression guard)
**Requirement:** FR-01 — the reported bug
**Given:** The committed `data/market_indices.json`, last 60 records
**When:** Checking the sign of `growth` and `inflation` across those records
**Then:** Not every record shares the same sign on both axes
**File:** `/test/integration/test_regime_quadrant.py::test_live_data_is_not_stuck_in_a_single_quadrant`
**Status:** FAIL (red) — **this is the concrete reproduction of the reported bug.** All 49 stored records currently have `growth > 0` and `inflation > 0`. Must pass after Phase 2 ships and the pipeline is re-run.

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
| FR-01 (scatter quadrant correctness) | TC-I02, TC-E01 | RED → fix in Phase 2 |
| Phase 2, T2.1 (63-day RoC) | TC-U04 | RED → implement |
| Phase 2, T2.3 (EMA smoothing) | TC-U05 | RED → implement |
| Phase 2, T2.5 (backtest) | TC-I01 | GREEN (regression guard) |
| `get_z_score` correctness | TC-U01, TC-U02, TC-U03 | GREEN (pre-existing) |

## Known Gaps

- FR-02 (composite line charts) and FR-07 (responsive layout) are not covered by automated tests — manual checks only, per the existing project Test Strategy. No JS test framework exists in this repo; adding one is out of scope for this bug fix.
- Phase 2's T2.2 (expanded Growth Index inputs: ICSA, T10Y3M) has no dedicated test yet — TC-I02 will validate it indirectly once the pipeline is re-run, but a more targeted unit test should be added during `/sdd-execute` once the new indicator wiring exists to test against.
- Sentiment/Liquidity index changes (research.md Option 1, Sections C/D) are explicitly out of scope for this phase (deferred to Phase 6) and have no tests here.

---
test_status: locked
locked_at: 2026-06-21T01:47:08Z
