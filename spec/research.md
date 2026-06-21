---
current_phase: research
status: complete
next_phase: plan
next_skill: /sdd-plan
---

# SDD Research: Market Regime Indicator Refinement

## Context Summary

The Market Owl regime indicator needs refactoring to produce more accurate, trustworthy macro regime signals for index ETF investment decisions. Key problems: wrong historical calls (2020 crash, 2022 stagflation, 2023 recovery) and mis-weighted composite indices. Must stay on static GitHub Pages with Python data pipeline and vanilla JS + Chart.js frontend. Open to any free data sources.

## Codebase Analysis

### Current Architecture (`scripts/update_indices.py`)

**Data Sources:**
- FRED: PMI (IPMAN), 5Y Inflation Expectations (T5YIFR), Fed Assets (WALCL), TGA (WTREGEN), RRP (RRPONTSYD), Junk Spread (BAMLH0A0HYM2), 10Y/2Y yields
- Yahoo Finance: SPY, TLT, sector ETFs (XLY/XLI/XLB/XLK/XLP/XLV/XLU), DBC, VIX, HG=F, GC=F, SPHB, SPLV

**Current Composite Indices:**
| Index | Formula | Issues |
|-------|---------|--------|
| Growth | 0.5 × Z(PMI) + 0.5 × Z(Cyclical/Defensive ratio) | Only 2 inputs, PMI is monthly & lagging, equal weighting |
| Inflation | 0.5 × Z(T5YIFR RoC) + 0.5 × Z(DBC RoC) | Only 2 inputs, 252-day RoC very slow to react |
| Liquidity | Z(WALCL − TGA − RRP) | Single composite, no smoothing |
| Sentiment | avg(Min-Max of: Momentum, VIX, SafeHaven, JunkSpread) | Put/Call placeholder=50, different scale (0-100) vs z-scores |
| Leading | avg(Z(Copper/Gold), Z(SPHB/SPLV), Z(10Y-2Y)) | Equal weight, no smoothing |

**Regime Detection:**
- Simple Growth vs Inflation scatter plot (4 quadrants divided at 0,0)
- No smoothing, no transition logic, no confidence score
- Z-score window: 252 days (1 year) — single lookback for everything

### Identified Weaknesses

1. **Too few inputs per composite** — 2 indicators per composite is fragile; one noisy reading dominates
2. **No smoothing** — raw z-scores jump day-to-day, causing noisy regime transitions
3. **PMI lag** — IPMAN (Industrial Production) is monthly, published with ~2 week lag; not a true PMI
4. **Equal weighting** — all components weighted 50/50 regardless of predictive power
5. **Fixed z-score window** — 252 days for everything; some indicators need shorter/longer lookbacks
6. **No transition logic** — regime flips on single-day z-score crossing zero
7. **Inflation RoC period too long** — 252-day rate of change is a full year; misses turning points by months
8. **Sentiment on different scale** — 0-100 min-max vs z-scores elsewhere; hard to compare
9. **Put/Call ratio placeholder** — hardcoded to 50, contributing nothing

---

## Solution Approaches

### Option 1: Enhanced Composites with EMA Smoothing (Recommended)

**Description:** Keep the 4-quadrant Growth/Inflation framework (aligned with Bridgewater All Weather and Merrill Lynch Investment Clock) but significantly improve each composite index with more inputs, adaptive weighting, and EMA smoothing to reduce noise.

**Changes:**

**A. Growth Index — expand to 4-5 indicators:**
- ISM Manufacturing PMI (FRED: `MANEMP` or use existing `IPMAN` but add...)
- Cyclical/Defensive ratio (keep, proven)
- OECD CLI or Conference Board LEI proxy (FRED: `T10Y3M` as leading indicator)
- Initial Jobless Claims inverted (FRED: `ICSA`) — weekly, very timely
- High-Beta/Low-Vol ratio (keep SPHB/SPLV, move from Leading to Growth — it's a growth signal)

Weight by signal timeliness: weekly indicators (jobless claims, market-based) get higher weight than monthly (PMI).

**B. Inflation Index — expand to 4 indicators, shorten RoC:**
- 5Y Breakeven Inflation (T5YIFR) — use 63-day RoC (quarterly) instead of 252-day
- Commodity index (DBC) — use 63-day RoC
- Copper price RoC (HG=F) — industrial inflation signal, move from Leading
- CPI YoY (FRED: `CPIAUCSL`) — monthly anchor, but use its z-score trend

**C. Liquidity Index — add breadth:**
- Net Liquidity (WALCL − TGA − RRP) — keep
- Add credit spreads inverted (already have junk spread — move from Sentiment)
- Financial Conditions proxy: TLT price trend (inverted, falling bonds = tighter conditions)

**D. Sentiment Index — unify to z-scores, fix placeholder:**
- Convert all to z-scores (drop min-max scaling for consistency)
- Remove Put/Call placeholder
- Components: SPY momentum (keep), VIX inverted (keep), Junk spread inverted (move to Liquidity), add AAII Sentiment Survey if available via free API, or use equity put/call from CBOE (FRED: `PCOTTM` — but check availability)

**E. Regime Detection — add smoothing + confidence:**
- Apply 10-day EMA to final composite indices before regime classification
- Add regime confidence score: distance from origin in Growth/Inflation space
- Add transition buffer: require 3+ consecutive days in new quadrant before official regime switch
- Add regime duration tracking in output JSON

**F. Reduce Inflation RoC to 63-day (quarterly):**
This alone would have caught 2022 stagflation ~2 months earlier.

**Pros:**
- Academically grounded (Bridgewater 4-box, ML Investment Clock)
- More robust composites (4-5 inputs each vs 2)
- EMA smoothing eliminates daily noise
- Transition buffer prevents whipsaws
- Confidence score adds transparency
- Shorter inflation RoC catches turning points faster
- All free data sources (FRED + Yahoo Finance)

**Cons:**
- More complex pipeline code
- More API calls (slightly slower daily update)
- Need to validate new weights don't overfit to 2020-2023

**Effort:** Medium

---

### Option 2: Hidden Markov Model (HMM) Regime Detection

**Description:** Replace the quadrant-based classification with a statistical HMM that learns regime states from data. Use `hmmlearn` Python library to fit a Gaussian HMM on growth + inflation + liquidity observables, letting the model discover regimes from data.

**Approach:**
- Fit 4-state GaussianHMM on rolling macro data
- Use Viterbi algorithm for most likely state sequence
- Map discovered states to economic labels (post-hoc)

**Pros:**
- Statistically rigorous regime detection
- Handles transition probabilities naturally
- Can discover regimes humans might miss
- Published academic methodology (Kritzman et al. 2012)

**Cons:**
- Black box — users can't see "why" a regime was called (violates transparency goal)
- Requires sufficient training data (3 years may not be enough for 4 states)
- State labels are arbitrary — "State 2" doesn't inherently mean "Stagflation"
- Model can be unstable with small data windows
- Harder to debug when wrong
- Static site constraint: model must be pre-computed; can't retrain in browser

**Effort:** High

---

### Option 3: Percentile Rank + Trend Direction Hybrid

**Description:** Instead of z-scores, use percentile ranks (0-100) for all indicators with a 2-year lookback, combined with trend direction (rising/falling measured by slope). Regime = combination of level (percentile) and direction (slope sign).

**Approach:**
- Each indicator → percentile rank over 504-day window
- Slope = linear regression over 63 days
- Growth regime = avg percentile > 50 AND slope positive
- More nuanced: 4 states based on Growth direction × Inflation direction

**Pros:**
- Bounded scale (0-100) — intuitive for users
- Percentile ranks are more robust to outliers than z-scores
- Direction adds leading signal
- Consistent scale across all composites

**Cons:**
- Percentile ranks compress extreme readings (a 99th percentile reading and 95th look similar)
- 2-year lookback means Jan 2020 data drops out of window by 2022 — moving reference point
- Slope can be noisy without smoothing
- Less established in academic literature for regime detection specifically

**Effort:** Medium

---

### Option 4: Minimal Fix — Tune Existing System

**Description:** Keep current architecture but fix the most impactful issues only:
- Shorten inflation RoC from 252 to 63 days
- Add 10-day EMA smoothing to composites
- Remove put/call placeholder
- Add 3-day transition buffer

**Pros:**
- Minimal code changes
- Low risk of breaking existing functionality
- Quick to implement and test

**Cons:**
- Doesn't address fundamental issue of too few inputs per composite
- Still fragile with only 2 indicators per index
- Doesn't add confidence scoring or transparency
- Doesn't address weighting

**Effort:** Low

---

## Recommendation

**Recommended: Option 1 — Enhanced Composites with EMA Smoothing**

**Reasoning:**

1. **Academic grounding** — The Growth/Inflation 4-quadrant framework is well-established (Bridgewater All Weather, Merrill Lynch Investment Clock, MSCI regime research). Enhancing it with more inputs and smoothing is the orthodox approach.

2. **Transparency** — Unlike HMM (Option 2), users can see exactly which indicators drive each composite and why a regime was called. This is critical for "most trusted" — trust requires explainability.

3. **Addresses root causes** — The current system fails because composites are too thin (2 inputs) and too noisy (no smoothing). Option 1 directly fixes both. The 63-day inflation RoC alone would have flagged 2022 stagflation ~8 weeks earlier.

4. **Practical** — All data sources are free (FRED + Yahoo Finance). No new dependencies except potentially moving indicator groupings. The Python pipeline gets more code but no new libraries.

5. **Backtestable** — Can validate against the three benchmark periods (2020, 2022, 2023) before shipping.

**Key risks:**
- **Overfitting** — Tuning weights to hit 2020-2023 correctly may not generalize. Mitigation: use simple equal-ish weights within composites, let the number of inputs (not weights) drive robustness.
- **Data availability** — Some FRED series may have gaps or revisions. Mitigation: all proposed series have 10+ year history.

## Additional Recommendations

### Visual Improvements
- Add regime label with confidence percentage to dashboard header
- Color-code the scatter chart quadrants (green=Reflation, red=Stagflation, etc.)
- Add historical regime timeline bar below the scatter chart
- Show regime duration counter ("Day 47 of Reflation")

### ETF Allocation Recommendations per Regime
Based on Merrill Lynch Investment Clock research + Bridgewater All Weather:

| Regime | Favored ETFs | Avoid |
|--------|-------------|-------|
| **Reflation** (↑Growth, ↓Inflation) | SPY, QQQ, XLF, XLK, IWM | GLD, TIP, XLU |
| **Overheat** (↑Growth, ↑Inflation) | DBC, XLE, XLI, XLB, TIP | TLT, XLU, XLP |
| **Stagflation** (↓Growth, ↑Inflation) | GLD, TIP, XLU, XLP, DBMF | SPY, QQQ, XLK, IWM |
| **Deflation** (↓Growth, ↓Inflation) | TLT, IEF, XLU, XLV, GOVT | DBC, XLE, XLB, HYG |

### New Free Data Sources to Add
| Source | Series | Purpose | Frequency |
|--------|--------|---------|-----------|
| FRED | ICSA | Initial Jobless Claims (Growth) | Weekly |
| FRED | T10Y3M | 10Y-3M spread — recession leading indicator | Daily |
| FRED | CPIAUCSL | CPI YoY (Inflation anchor) | Monthly |
| FRED | UMCSENT | U Mich Consumer Sentiment (Sentiment) | Monthly |
| Yahoo Finance | Move from Leading→Growth: SPHB/SPLV | Beta appetite = growth signal | Daily |
| Yahoo Finance | Move from Sentiment→Liquidity: Junk spread | Credit conditions = liquidity signal | Daily |

## Open Questions

1. Should we extend the data lookback from 3 years to 5 years? (needed for proper backtesting of 2020 crash)
2. What specific EMA period works best for smoothing? (10-day proposed, but 5 or 21 may be better)
3. Should we add a "Transition" regime label for when the indicator is near the origin?

---

## Summary for Next Phase

Recommended approach: **Enhanced Composites with EMA Smoothing** — expand each composite index to 4-5 indicators (adding ICSA, T10Y3M, CPI, moving indicators between composites for better signal alignment), shorten Inflation RoC from 252 to 63 days, apply 10-day EMA smoothing to final composites, add 3-day regime transition buffer and confidence score. Also add visual improvements (color-coded quadrants, regime label with confidence, historical timeline) and per-regime ETF allocation recommendations. All within existing constraints: Python pipeline, FRED + Yahoo Finance data, static GitHub Pages, vanilla JS + Chart.js. Key risk is overfitting — mitigate by using simple weights and validating against 2020/2022/2023 benchmark periods.
