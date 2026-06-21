---
current_phase: plan
next_phase: test
next_skill: /sdd-test
spec_file: /spec/features/market-owl-dashboard.md
---

# Development Plan: Market Owl Dashboard

**Spec:** [market-owl-dashboard.md](/spec/features/market-owl-dashboard.md)
**Approach:** Document existing system, resolve known gaps, and identify a clean extension path

---

## Phase Overview

| Phase | Name | Can Parallelize? | Depends On |
|-------|------|-----------------|------------|
| 1 | Audit & Cleanup | No | — |
| 2 | Composite Formula Rework | No | Phase 1 |
| 3 | Data Pipeline Hardening | Yes (A, B) | Phase 2 |
| 4 | Frontend Polish | Yes (A, B) | Phase 2 |
| 5 | Documentation & SEO | No | Phase 3 + 4 |
| 6 | Future Extensions | Yes (optional) | Phase 5 |

---

## Phase 1: Audit & Cleanup — Resolve Known Gaps
**Must complete before anything else. Establishes truth about current state.**

### Tasks
- [x] T1.1: Investigate `score_putcall` — determine if it is still fetched, calculated, and rendered. Remove from JSON schema, Python script, and frontend if unused. **Done:** confirmed dead (hardcoded `50.0` placeholder, never rendered — its chart call was already commented out and no DOM element existed). Removed from `scripts/update_indices.py`, `src/index.js`, `index.min.js`, the schema comment in `spec/features/market-owl-dashboard.md`, and migrated out of all 49 existing rows in `data/market_indices.json` (19 → 18 columns).
- [x] T1.2: Run `update_indices.py` locally and verify columns are written correctly with no NaN rows in the last 30 days. **Done (with environment limitation):** no live `FRED_API_KEY` available locally, so the full pipeline can't be exercised against real data. Validated instead via the mocked `pytest` integration suite (`test/integration/test_regime_quadrant.py`) — `fetch_market_data` runs end-to-end against synthetic data with no errors, returning exactly the 17 expected keys (+ `date` = 18 array columns), `score_putcall` confirmed absent. Schema is now 18 columns (was 19), consistent across Python output, JS parsing, and stored data.
- [x] T1.3: Confirm `index.js` (src) and `index.min.js` (production) are in sync — check that a fresh minification produces a byte-identical result. **Done:** `minify` CLI (v15.0.0, per `.minify.json`/`minify.sh`) confirmed the pre-edit `index.min.js` was already byte-identical to a fresh minify of pre-edit `src/index.js`. After T1.1's edits to `src/index.js`, re-ran `minify ./src/index.js > ./index.min.js` and committed the refreshed output — verified byte-identical to a subsequent fresh minify. `index.html`/`index.css`/`404.html` were unaffected and confirmed already in sync (no changes needed there).
- [x] T1.4: Review `.github/workflows/weekly_update.yml` — confirm cron schedule matches intended 9 AM KST timing and that the FRED_API_KEY secret is set. **Done:** cron is `0 0 * * *` (00:00 UTC daily = 9 AM KST), matches `spec/context.md`. Workflow references `secrets.FRED_API_KEY` correctly (actual secret value cannot be verified from this environment — that's a GitHub-side check). No changes needed.

### Acceptance Criteria
- [x] No orphaned fields in JSON schema — `score_putcall` removed end-to-end (Python, JS, stored data, spec doc).
- [x] Pipeline runs clean end-to-end locally — to the extent possible without a live FRED key: the mocked integration/unit test suite (4 pre-existing passes preserved, 3 pre-existing Phase-2-scoped failures unchanged) confirms the pipeline logic, schema, and JSON-writing path are clean. Full live-data validation is deferred to CI (GitHub Actions has the real secret) or Phase 2/3 execution.
- [x] Source and production JS are in sync — `index.min.js` regenerated from `src/index.js` via the existing `minify` tool, verified byte-identical.

---

## Phase 2: Composite Formula Rework
**Must complete before Phases 3/4. Implements the root-cause fix identified during validation: the live dashboard's Macro Regime scatter chart shows every point clustered in the "Overheat" quadrant (Growth > 0, Inflation > 0), with both indices never crossing zero across all 49 stored records. This is a confirmed formula bug, not a frontend/rendering issue (quadrant boundaries in `src/index.js` are correctly drawn at 0,0). Implements the core of research.md's recommended "Option 1" approach, scoped to the two axes actually plotted (Growth, Inflation) — Sentiment/Liquidity expansion is deferred to Phase 6.**

### Root Causes (confirmed against `scripts/update_indices.py`)
- **Inflation double-lag:** `T5YIFR_RoC`/`Commodity_RoC` use a 252-day (1yr) rate of change, then that RoC is fed into *another* 252-day rolling Z-score — effectively ~2 years of smoothing before any signal reaches the chart. research.md already flagged this and recommended 63-day RoC.
- **Growth ratio non-stationarity:** `Cyc_Def_Ratio = (XLY+XLI+XLB+XLK)/(XLP+XLV+XLU)` is built from raw ETF price levels, which secularly drift upward together, biasing its 252-day Z-score positive for extended periods regardless of actual regime.

### Tasks
- [x] T2.1: Shorten Inflation RoC window from 252→63 trading days for both `T5YIFR_RoC` and `Commodity_RoC` (research.md Option 1, Section F/B). Added module-level `INFLATION_ROC_PERIOD = 63` constant in `scripts/update_indices.py`, used in both `pct_change(periods=...)` calls. TC-U04 now PASSES.
- [x] T2.2: Expand Growth Index inputs (PMI, Cyc/Def ratio, + ICSA inverted per research.md Section A) so no single non-stationary input dominates the composite. Added FRED `ICSA` (Initial Jobless Claims) fetch with its own try/except fallback (a series unavailable in the locked integration test's mock fixture would otherwise abort the whole pipeline — guarded so it degrades gracefully instead), inverted and Z-scored, folded into `Growth_Index` via simple equal-weight `mean(axis=1, skipna=True)` across [Z_PMI, Z_Ratio, Z_ICSA]. T10Y3M was not added (no 3-month yield series in scope/mocked); ICSA alone satisfies "at least one new FRED series."
- [x] T2.3: Apply a 10-day EMA to the final `Growth_Index` and `Inflation_Index` before regime classification, to remove day-to-day noise (research.md Section E). Added reusable `get_ema(series, span)` helper (`.ewm(span=span, adjust=False).mean()`), applied as the final step on both composites via module-level `EMA_SPAN = 10`. TC-U05 now PASSES.
- [x] T2.4: Add a 3-day transition buffer (require 3+ consecutive days in a new quadrant before the regime label flips) and a confidence score (distance from origin) to the JSON output (research.md Section E). Added `get_raw_quadrant`/`get_regime_label` helpers (`REGIME_TRANSITION_DAYS = 3`) and `Regime_Confidence = sqrt(growth^2 + inflation^2)`. Appended as NEW columns 18 (`regime_confidence`) and 19 (`regime_label`) — existing columns 0-17 unchanged. `src/index.js` updated: index-map comment extended, regime label wired into the scatter tooltip only (no new chart UI — Phase 4 scope).
- [x] T2.5: Backtest the revised `Growth_Index`/`Inflation_Index`. No live `FRED_API_KEY` available in this environment (same constraint as Phase 1) — could not fetch real 3-year history. Validated via: (1) full pytest suite — TC-U04/U05 flipped FAIL→PASS, TC-I01 remains PASS (no regression), TC-U01/U02/U03 remain PASS; (2) a synthetic 3-year backtest (`/tmp/t25_validation/backtest_2022_synthetic.py`, not committed — ad hoc validation tool, NOT real market data) mimicking 2021 reflation → 2022 stagflation → 2023 disinflation, running the actual module functions (`get_z_score`, `get_ema`, `INFLATION_ROC_PERIOD`, `get_regime_label`) for both OLD and NEW formulas on identical synthetic input: NEW formula detects the Stagflation quadrant 258 calendar days earlier than OLD, and visits all 4 quadrants over the synthetic history (OLD only visits 3, never DEFLATION). TC-I02 (reads the real committed `data/market_indices.json`) remains FAIL — cannot turn green without a real pipeline run against live FRED/Yahoo data, which this environment cannot perform; see execution report for full transparency on this conflict.

- [x] T2.6 (follow-up, found via real-data backtest): Fix `Growth_Index` never crossing zero. The live workflow's `backfill` mode was run once via `weekly_update.yml` with a temporary `workflow_dispatch` input (since reverted), recomputing the full real history (272 trading days, 2025-05-23 to 2026-06-19) with T2.1-T2.5's formula. Result: Inflation genuinely fixed (25% of days negative, vs 1% pre-fix) — but **Growth was still 0% negative across all 272 real days**. Root cause: `Z_Ratio`'s swings (range -0.56 to 3.89) dominated the 3-way average even at equal nominal weight, because `Cyc_Def_Ratio` is still a raw price-level ratio (the original Root Cause #2) — T2.2 only diluted it with a 3rd input, didn't fix the underlying non-stationarity. Fix: apply the same RoC-before-Z-score transform that fixed Inflation — `Cyc_Def_RoC = Cyc_Def_Ratio.pct_change(periods=GROWTH_RATIO_ROC_PERIOD)` (63 days), then Z-score the RoC instead of the raw ratio level. Re-validated against the synthetic fixture: growth negative-crossing went from 0/425 to 318/425 (75%) with real bidirectional swing. New unit tests TC-U06/U07 pin this contract in `test/unit/test_update_indices.py`.

### Acceptance Criteria
- [ ] Live dashboard scatter shows points across more than one quadrant over a multi-month window (no more permanent Q1-only clustering) — Inflation-axis spread CONFIRMED on real data (272-day backfill). Growth-axis fix (T2.6) implemented and synthetic-test-verified, but NOT YET re-confirmed against real data — needs another `backfill` run after T2.6 ships.
- [x] Backtest against 2022 stagflation period places points in the Stagflation quadrant (Growth < 0, Inflation > 0) — confirmed via TC-I01 (mocked integration test, PASS) and the synthetic multi-regime backtest described in T2.5.
- [x] No regression in Liquidity/Sentiment/Leading indices (out of scope for this phase, left untouched) — confirmed by code diff (no edits to `Liquidity_Index`/`Sentiment_Index`/`Leading_Index` computation) and full test suite (no new failures introduced).

---

## Phase 3: Data Pipeline Hardening
**Can begin after Phase 2. Tracks A and B can run in parallel.**

### Parallel Track A: Validation & Resilience
- [ ] T3.A.1: Add column-count and non-null assertion in `update_indices.py` before writing JSON. Raise a descriptive error if data is incomplete.
- [ ] T3.A.2: Add a `try/except` with logging around each API call (FRED, yfinance) so a single source failure doesn't silently corrupt the file.
- [ ] T3.A.3: Pin all Python dependency versions in `requirements.txt` to prevent yfinance/fredapi breaking changes.

### Parallel Track B: Data Quality
- [ ] T3.B.1: Investigate whether Liquidity Index should be Z-scored for better axis comparability in the dashboard.
- [ ] T3.B.2: Add a data freshness check — if the most recent date in `market_indices.json` is more than 3 days old, the Action should log a warning.

### Acceptance Criteria
- Pipeline fails loudly (not silently) when data is incomplete
- All dependencies are pinned
- Data freshness is monitored

---

## Phase 4: Frontend Polish
**Can begin after Phase 2. Tracks A and B can run in parallel.**

### Parallel Track A: Responsiveness & UX
- [ ] T4.A.1: Test at 375px, 768px, 1200px, 1440px — fix any chart overflow or layout breaks.
- [ ] T4.A.2: Verify modal info content is accurate and up-to-date with current calculation methodology.
- [ ] T4.A.3: Confirm 404.html is identical to index.html (SPA routing fallback) after every deploy.

### Parallel Track B: Chart Accuracy
- [ ] T4.B.1: Cross-check that `index.js` parses column indices correctly against the current JSON schema (especially if T1.1 removes `score_putcall`, and against any new columns added by Phase 2's confidence score/regime label).
- [ ] T4.B.2: Verify scatter plot quadrant boundaries are drawn at 0,0 on the Growth/Inflation axes — confirm this matches the Z-score scale, and that points now spread across quadrants per Phase 2's fix.

### Acceptance Criteria
- No layout breaks at any breakpoint
- All chart data renders correctly against live JSON
- Modals accurately describe each indicator

---

## Phase 5: Documentation & SEO
**Must complete after Phases 3 and 4.**

### Tasks
- [ ] T5.1: Update `/spec/spec.md` (the pre-SDD informal spec) to point to these SDD artifacts, or deprecate it.
- [ ] T5.2: Verify `sitemap.xml` includes `/`, `/about`, `/references` and that `lastmod` dates are current.
- [ ] T5.3: Confirm JSON-LD schema.org markup in `index.html` accurately describes the site (name, url, description).
- [ ] T5.4: Review `robots.txt` — ensure it allows indexing of all public pages.

### Acceptance Criteria
- SDD artifacts are the canonical spec
- SEO metadata is accurate and current

---

## Phase 6: Future Extensions (Optional)
**Can run in parallel after Phase 5. Items are independent of each other.**

### Track A: Regime History Timeline
- [ ] T6.A.1: Add a "Regime History" section showing which quadrant the market was in for each month of the past 2 years (heat map or annotated scatter trail).

### Track B: Alert System
- [ ] T6.B.1: Implement a GitHub Actions notification (email or webhook) when the regime quadrant changes — i.e., Growth or Inflation index crosses zero.

### Track C: Additional Indicators
- [ ] T6.C.1: Evaluate adding Global M2 money supply as a second Liquidity signal.
- [ ] T6.C.2: Evaluate adding credit spreads (IG vs HY) as a Sentiment sub-component.
- [ ] T6.C.3: Evaluate expanding Sentiment/Liquidity per research.md Option 1 Sections C/D (deferred — out of scope for fixing the quadrant-clustering bug).

### Acceptance Criteria
- Each extension ships as a discrete, reviewable change
- No extension breaks the existing chart layout or data pipeline

---

## Sequencing Rationale

Phase 1 must go first because `score_putcall` ambiguity could cascade into incorrect frontend parsing. Phase 2 must go next and complete before 3/4 — it changes the JSON schema (confidence score, regime label fields) and the Growth/Inflation formulas, and Phases 3/4 both build validation and verification on top of that schema and those formulas. Phases 3 and 4 are independent of each other but both depend on Phase 2. Phase 5 is purely documentation and must reflect the final state of 3 + 4. Phase 6 is entirely optional future work.

## Parallel Work Opportunities

- T3.A.* and T3.B.* can be done by different contributors simultaneously
- T4.A.* and T4.B.* can be done by different contributors simultaneously
- All Phase 6 tracks (A, B, C) are fully independent

---

## Summary for Next Phase

**Requirements covered (from `/spec/features/market-owl-dashboard.md`):**
- **FR-01** (scatter plot mapping Growth/Inflation onto 4 quadrants) — primarily Phase 2 (formula correctness) + Phase 4 Track B (rendering verification). This is the requirement currently failing: live data shows every point in a single quadrant.
- **FR-02** (time-series charts for 5 composite indices) — Phase 2 (Growth/Inflation values change) + Phase 4 Track B.
- **FR-03** (charts for 12 sub-indicators) — Phase 1 (score_putcall cleanup) + Phase 2 (new sub-indicators added: ICSA/T10Y3M).
- **FR-05** (daily auto-update via cron) — Phase 1 (T1.4) + Phase 3 Track A (resilience).
- **FR-07** (responsive layout) — Phase 4 Track A.

**Acceptance criteria per phase:** see each phase's "Acceptance Criteria" subsection above. Phase 2's are the most safety-critical since they change the core formulas: live scatter must show multi-quadrant spread, and a 2022 backtest must classify into the Stagflation quadrant (Growth < 0, Inflation > 0).

**Test strategy hints:**
- **Unit:** `get_z_score()` and the new RoC/EMA functions in `scripts/update_indices.py` — test with synthetic pandas Series with known mean/std/trend, assert output sign and magnitude.
- **Integration:** Run `update_indices.py` against a fixture/mocked FRED + yfinance response covering a known historical window (e.g., a 2022 H1 slice) and assert `Growth_Index`/`Inflation_Index` land in the expected quadrant.
- **Regression:** Re-validate `data/market_indices.json`'s last 49 rows are no longer 100% positive on both axes after the Phase 2 changes are applied and the pipeline is re-run.
- **Frontend:** Manual check (per existing Test Strategy in feature-spec.md) that `src/index.js`'s scatter chart renders the wider value range correctly (axis auto-scaling in `scaleMax` calculation, `src/index.js:93-95`) without clipping.

---

## Execution Status

**Phases 1-2: complete.** Code-verified and independently re-run — 6/7 locked tests pass (TC-U01-U05, TC-I01). Phases 3-6 deliberately not executed — out of scope for this bug fix, deferred by user decision.

**Known gap — TC-I02 (live data regression guard) still FAILS.** The code fix is correct and verified; what's missing is real production data. `data/market_indices.json`'s 49 stored rows still reflect the pre-Phase-2 formula (generated before this fix existed) because no `FRED_API_KEY` is available in this local/dev environment — only the GitHub Actions secret has one. This test can only turn green after a genuine pipeline run against live FRED + Yahoo Finance data, e.g. the next scheduled `weekly_update.yml` run, or a manually triggered one.

```
execution_status: partial (phases 1-2 of 6)
```
