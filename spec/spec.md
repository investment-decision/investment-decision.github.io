# Project Specification: Market Owl (Investment Decision Dashboard)

## 1. Overview
**Market Owl** provides a quantitative market regime dashboard visualizing Growth, Inflation, Liquidity, and Sentiment. It aims to offer data-driven insights through various charts and indicators to help investors make informed decisions.

- **URL**: [marketowl.net](https://marketowl.net/)
- **Repository**: `investment-decision.github.io`
- **Goal**: Visualize complex economic data simply to identify market regimes (Goldilocks, Reflation, Stagflation, Deflation).

## 2. Technology Stack

### Frontend
- **HTML5**: Semantic structure with meta tags for SEO and Open Graph.
- **CSS3**: Vanilla CSS with custom properties (variables) for theming.
  - **Font**: Inter (Google Fonts).
  - **Responsive Design**: Grid and Flexbox (Desktop, Tablet, Mobile).
- **JavaScript (ES6+)**: Vanilla JS for logic, routing, and DOM manipulation.
  - **Library**: `Chart.js` (via CDN) for data visualization.

### Backend / Data
- **Static Hosting**: GitHub Pages.
- **Data Source**: JSON file (`/data/market_indices.json`) fetched client-side.
- **Automation**: Python scripts (`scripts/update_indices.py`) to fetch, process, and update data JSON.

## 3. Architecture

### 3.1. Client-Side Routing (SPA)
The application acts as a Single Page Application (SPA) with custom routing logic in `src/index.js`.
- **Routes**:
  - `/` (Dashboard) - Main visualization.
  - `/about` (About) - Methodology and philosophy.
  - `/references` (References) - Data sources and reading materials.
- **Mechanism**: Use `history.pushState` and `popstate` event to handle navigation without page reloads.

### 3.2. Directory Structure
```
.
├── index.html          # Entry point
├── index.css           # Global styles & variables
├── src/
│   └── index.js        # Core logic (Charts, Routing, Modals)
├── data/
│   └── market_indices.json # Time-series data
├── scripts/
│   └── update_indices.py   # Data automation script
└── spec/
    └── spec.md         # This specification file
```

## 4. Features & Components

### 4.1. Dashboard (Main View)
Organized into a grid layout with responsive adjustments.

#### Row 1: Key Indicators
1.  **Macro Regime Composite (Scatter)**:
    -   **X-Axis (Growth Index)**: Average of `Z_PMI` and `Z_Ratio`.
        -   `Z_PMI`: Z-Score (1yr window) of ISM Manufacturing PMI (`IPMAN`).
        -   `Z_Ratio`: Z-Score (1yr window) of Cyclical vs Defensive Stocks Ratio.
            -   *Cyclical*: XLY + XLI + XLB + XLK
            -   *Defensive*: XLP + XLV + XLU
    -   **Y-Axis (Inflation Index)**: Average of `Z_T5YIFR` and `Z_Commodity`.
        -   `Z_T5YIFR`: Z-Score (1yr window) of the **Rate-of-Change (RoC)** of 5-Year Forward Inflation Expectation (prioritizing momentum over absolute levels).
        -   `Z_Commodity`: Z-Score (1yr window) of the **Rate-of-Change (RoC)** of Invesco DB Commodity Index (`DBC`) (prioritizing momentum over absolute levels).
    -   **Quadrants**: Reflation (Growth↑, Inf↓), Overheat (Growth↑, Inf↑), Stagflation (Growth↓, Inf↑), Deflation (Growth↓, Inf↓).
    -   **Trail**: Shows historical movement (last 60 data points).
2.  **Global Net Liquidity Gauge**:
    -   Formula: `Fed Assets - TGA - RRP`.
    -   Visualizes liquidity trends.
3.  **Composite Sentiment Oscillator**:
    -   Range: 0-100 (Fear vs Greed).
    -   Thresholds: Overbought (>80), Oversold (<20).
4.  **Inter-Market Leading Indicator**:
    -   Composite of Copper/Gold, Yield Curve, etc.

#### Row 2: Macro Components
-   Z_PMI (Manufacturing)
-   Z_Ratio (Cyclical vs Defensive)
-   Z_T5YIFR (Inflation Expectations)
-   Z_Commodity (Broad Index)

#### Row 3: Sentiment Components
-   Momentum Score
-   Volatility Score (VIX)
-   Safe Haven Score
-   Junk Bond Score

#### Row 4: Leading Components
-   Z_Copper/Gold
-   Z_Beta/Volatility
-   Z_Yield Spread (10Y-2Y)

### 4.2. Modal System
-   Clicking the `?` button on any chart opens a modal with detailed explanations.
-   Content is dynamically loaded from a dictionary object in `index.html`.

### 4.3. Design System
-   **Colors**:
    -   `--brand-color`: #2c3e50 (Dark Blue/Grey)
    -   `--accent-liquidity`: #af52de (Purple)
    -   `--accent-growth`: #007aff (Blue)
    -   `--accent-inflation`: #ff3b30 (Red)
    -   `--accent-sentiment`: #ff9500 (Orange)
    -   `--accent-leading`: #34c759 (Green)
-   **Typography**: Inter, with Monospace for formulas.

## 5. Data Model (`market_indices.json`)
Array of arrays format for minimized size.
-   **Index 0**: Date (YYYY-MM-DD)
-   **Index 1-5**: Composite Indices (Growth, Inflation, Liquidity, Sentiment, Leading)
-   **Index 6-10**: Macro Raw/Z-Scores (PMI, Ratios, etc.)
-   **Index 11-15**: Sentiment Scores
-   **Index 16-18**: Leading Indicators

## 6. Deployment & Maintenance
-   **Build**: No build step for JS/CSS (served raw). Minification logic exists (`minify.sh`) but `index.html` loads raw files currently (needs verification/switch to `.min` for prod).
-   **Updates**: Python script updates JSON -> Commit -> Push triggers GitHub Pages build.
-   **SEO**: `sitemap.xml` and `robots.txt` configured.
