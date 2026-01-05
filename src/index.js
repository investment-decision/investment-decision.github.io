// --- Modal Content Database ---
const MODAL_DATA = {
    macro: {
        title: "Macro Regime Composite",
        body: `
                    <p>Visualizes the four economic seasons based on Growth and Inflation. The current regime is determined by the dot's position.</p>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; font-size:0.9em; text-align:center;">
                        <div style="background:#fff3e0; padding:10px; border-radius:6px; border:1px solid #ffe0b2;">
                            <strong style="color:#e65100;">Overheat (Q1)</strong><br>
                            <span style="font-size:0.8em; color:#666;">Growth↑ Inflation↑</span><br>
                            <span style="color:#ef6c00; font-weight:600;">Commodities/Value</span>
                        </div>
                        <div style="background:#ffebee; padding:10px; border-radius:6px; border:1px solid #ffcdd2;">
                            <strong style="color:#c62828;">Stagflation (Q2)</strong><br>
                            <span style="font-size:0.8em; color:#666;">Growth↓ Inflation↑</span><br>
                            <span style="color:#d32f2f; font-weight:600;">Cash/Gold</span>
                        </div>
                        <div style="background:#e3f2fd; padding:10px; border-radius:6px; border:1px solid #bbdefb;">
                            <strong style="color:#1565c0;">Deflation (Q3)</strong><br>
                            <span style="font-size:0.8em; color:#666;">Growth↓ Inflation↓</span><br>
                            <span style="color:#1976d2; font-weight:600;">Bonds/USD</span>
                        </div>
                        <div style="background:#e8f5e9; padding:10px; border-radius:6px; border:1px solid #c8e6c9;">
                            <strong style="color:#2e7d32;">Reflation (Q4)</strong><br>
                            <span style="font-size:0.8em; color:#666;">Growth↑ Inflation↓</span><br>
                            <span style="color:#388e3c; font-weight:600;">Growth Stocks</span>
                        </div>
                    </div>`
    },
    liquidity: {
        title: "Global Net Liquidity Gauge",
        body: `
                    <p>Measures the net liquidity available in the market by subtracting liabilities (TGA, RRP) from the Fed's total assets.</p>
                    <p><strong>Formula:</strong> Fed Assets - TGA - RRP</p>
                    <ul>
                        <li><strong>Rising:</strong> Increased liquidity, favoring risk assets (stocks, crypto).</li>
                        <li><strong>Falling:</strong> Tightening liquidity, potential for market correction.</li>
                    </ul>`
    },
    sentiment: {
        title: "Composite Sentiment Oscillator",
        body: `<p>Measures market fear and greed on a scale of 0 to 100.</p>
                       <ul>
                           <li><strong>0-20 (Extreme Fear):</strong> Market panic. Potential contrarian buy signal.</li>
                           <li><strong>80-100 (Extreme Greed):</strong> Market euphoria. Consider taking profits.</li>
                           <li><strong>Components:</strong> VIX, Put/Call Ratio, Junk Bond Spread, Momentum, Safe Haven Demand.</li>
                       </ul>`
    },
    leading: {
        title: "Inter-Market Leading Indicator",
        body: `<p>Predicts future market direction using "smart money" signals from bond and commodity markets.</p>
                       <ul>
                           <li><strong>Copper/Gold Ratio:</strong> Economic recovery vs. fear.</li>
                           <li><strong>Yield Curve (10Y-2Y):</strong> Recession warning when inverted.</li>
                           <li><strong>High Beta/Low Vol:</strong> Internal market risk appetite.</li>
                       </ul>`
    },
    pmi: {
        title: "Z_PMI (ISM Manufacturing)",
        body: `<p>A leading indicator of economic health based on surveys of purchasing managers. 'New Orders' specifically leads the equity market cycle.</p>`
    },
    ratio: {
        title: "Z_Ratio (Cyclical vs Defensive)",
        body: `<p>The relative performance of Cyclical vs. Defensive stocks. Reflects real-time economic growth expectations from market participants.</p>`
    },
    t5yifr: {
        title: "Z_T5YIFR (5Y Inflation Exp)",
        body: `<p>The market's expectation for inflation over the 5-year period beginning 5 years from today. Filters out short-term oil price noise.</p>`
    },
    commodity: {
        title: "Z_Commodity (Broad Index)",
        body: `<p>Broad commodity index (Energy, Metals, Agriculture). A leading indicator for consumer price inflation (CPI).</p>`
    },
    mom: { title: "Momentum Score", body: "<p>Distance between current price and the 125-day moving average. Higher values indicate Greed.</p>" },
    vix: { title: "VIX Score", body: "<p>Volatility Index. Higher values indicate Fear (resulting in a lower score).</p>" },
    pc: { title: "Put/Call Score", body: "<p>Put/Call Ratio. Higher values indicate Fear (resulting in a lower score).</p>" },
    safe: { title: "Safe Haven Score", body: "<p>Return difference between Stocks and Bonds. Outperformance of stocks indicates Greed.</p>" },
    junk: { title: "Junk Bond Score", body: "<p>High Yield Bond Spread. Widening spreads indicate Fear (resulting in a lower score).</p>" },
    cg: { title: "Z_Copper/Gold", body: "<p>Copper (Growth) to Gold (Fear) ratio. Rising trend signals economic recovery.</p>" },
    bv: { title: "Z_Beta/Volatility", body: "<p>Ratio of High Beta to Low Volatility stocks. Indicates internal market risk appetite.</p>" },
    ys: { title: "Z_Yield Spread", body: "<p>Yield Curve Spread (10Y-2Y). Inversion (negative value) warns of an impending recession.</p>" }
};

function openModal(key) {
    const data = MODAL_DATA[key];
    if (data) {
        document.getElementById('modalTitle').innerHTML = data.title;
        document.getElementById('modalBody').innerHTML = data.body;
        document.getElementById('infoModal').style.display = 'flex';
    }
}

function closeModal() {
    document.getElementById('infoModal').style.display = 'none';
}

// --- Chart Logic ---
async function createCharts() {
    try {
        // Ensure the path is correct for your environment
        const response = await fetch('./data/market_indices.json');
        if (!response.ok) throw new Error("Network response was not ok");
        const rawData = await response.json();

        // Map array data to charts
        // Index Map:
        // 0: date
        // 1: growth_index, 2: inflation_index, 3: liquidity_index, 4: sentiment_index, 5: leading_index
        // 6: z_pmi, 7: z_ratio, 8: z_t5yifr, 9: z_commodity, 10: net_liquidity_raw
        // 11: score_momentum, 12: score_vix, 13: score_putcall, 14: score_safehaven, 15: score_junk
        // 16: z_coppergold, 17: z_betavol, 18: z_yieldspread

        const labels = rawData.map(d => d[0]);

        // 1. Line Chart Options (Time Series)
        const lineOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        maxTicksLimit: 6,
                        font: { size: 10 },
                        callback: function (value) {
                            const label = this.getLabelForValue(value);
                            return label.substring(0, 7); // Shows YYYY-MM
                        }
                    },
                    grid: { display: false }
                },
                y: { grid: { color: '#f0f0f0' } }
            },
            elements: { point: { radius: 0, hoverRadius: 4 } }
        };

        // 2. Macro Regime Options (Scatter, Fixed Scale)
        const scatterOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    min: -3, max: 3,
                    grid: { color: (ctx) => ctx.tick.value === 0 ? '#333' : '#eee', lineWidth: (ctx) => ctx.tick.value === 0 ? 1.5 : 1 }
                },
                y: {
                    min: -3, max: 3,
                    grid: { color: (ctx) => ctx.tick.value === 0 ? '#333' : '#eee', lineWidth: (ctx) => ctx.tick.value === 0 ? 1.5 : 1 }
                }
            }
        };

        // 3. Sentiment Options (Fixed 0-100)
        const sentimentOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        maxTicksLimit: 6,
                        font: { size: 10 },
                        callback: function (value) {
                            const label = this.getLabelForValue(value);
                            return label.substring(0, 7); // Shows YYYY-MM
                        }
                    },
                    grid: { display: false }
                },
                y: {
                    min: 0, max: 100,
                    grid: { color: '#f0f0f0' },
                    ticks: { stepSize: 20 }
                }
            },
            elements: { point: { radius: 0, hoverRadius: 4 } }
        };

        // --- Chart 1: Macro Regime (Scatter) ---
        const trailLength = 60;
        const recentData = rawData.slice(-trailLength);
        const scatterData = recentData.map(d => ({ x: d[1], y: d[2] })); // Growth(1), Inflation(2)

        const trailColors = scatterData.slice(0, -1).map((_, i, arr) => {
            const opacity = 0.1 + (0.9 * (i / arr.length));
            return `rgba(100, 110, 120, ${opacity})`;
        });

        const trailStart = recentData[0][0];
        const trailEnd = recentData[recentData.length - 2][0];

        const quadrantLabelsPlugin = {
            id: 'quadrantLabels',
            afterDraw: (chart) => {
                const { ctx, chartArea: { left, right, top, bottom, width, height }, scales: { x, y } } = chart;
                const midX = x.getPixelForValue(0);
                const midY = y.getPixelForValue(0);

                ctx.save();
                ctx.font = 'bold 12px Inter';
                ctx.fillStyle = 'rgba(150, 150, 150, 0.4)';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';

                const q1x = (midX + right) / 2;
                const q1y = (top + midY) / 2;
                const q2x = (left + midX) / 2;
                const q2y = (top + midY) / 2;
                const q3x = (left + midX) / 2;
                const q3y = (midY + bottom) / 2;
                const q4x = (midX + right) / 2;
                const q4y = (midY + bottom) / 2;

                ctx.fillText("OVERHEAT", q1x, q1y);
                ctx.fillText("STAGFLATION", q2x, q2y);
                ctx.fillText("DEFLATION", q3x, q3y);
                ctx.fillText("REFLATION", q4x, q4y);

                ctx.restore();
            }
        };

        new Chart(document.getElementById('chartMacro'), {
            type: 'scatter',
            data: {
                datasets: [
                    {
                        label: `${trailStart} ~ ${trailEnd}`,
                        data: scatterData.slice(0, -1),
                        backgroundColor: trailColors,
                        borderColor: trailColors,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    },
                    {
                        label: 'Current',
                        data: [scatterData[scatterData.length - 1]],
                        backgroundColor: '#e74c3c',
                        borderColor: '#ffffff',
                        borderWidth: 2,
                        pointRadius: 7,
                        pointHoverRadius: 9
                    }
                ]
            },
            options: scatterOptions,
            plugins: [quadrantLabelsPlugin]
        });

        // --- Chart 2: Liquidity (Line) ---
        new Chart(document.getElementById('chartLiquidity'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    data: rawData.map(d => d[3]), // liquidity_index
                    borderColor: '#af52de', borderWidth: 2, fill: false, tension: 0.3
                }]
            },
            options: lineOptions
        });

        // --- Chart 3: Sentiment (Line 0-100) ---
        new Chart(document.getElementById('chartSentiment'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        data: rawData.map(d => d[4]), // sentiment_index
                        borderColor: '#ff9500', borderWidth: 2, fill: false, tension: 0.3
                    },
                    {
                        data: Array(labels.length).fill(80),
                        borderColor: 'rgba(231, 76, 60, 0.3)', borderWidth: 1, borderDash: [5, 5], pointRadius: 0, fill: false
                    },
                    {
                        data: Array(labels.length).fill(20),
                        borderColor: 'rgba(46, 204, 113, 0.3)', borderWidth: 1, borderDash: [5, 5], pointRadius: 0, fill: false
                    }
                ]
            },
            options: sentimentOptions
        });

        // --- Chart 4: Leading (Line) ---
        new Chart(document.getElementById('chartLeading'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    data: rawData.map(d => d[5]), // leading_index
                    borderColor: '#34c759', borderWidth: 2, fill: false, tension: 0.3
                }]
            },
            options: lineOptions
        });

        // --- Helper for Single Line Chart ---
        const createComponentChart = (id, dataIndex, color, options = lineOptions) => {
            new Chart(document.getElementById(id), {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        data: rawData.map(d => d[dataIndex]),
                        borderColor: color, borderWidth: 1.5, fill: false, tension: 0.1
                    }]
                },
                options: options
            });
        };

        // Row 2: Macro Components
        createComponentChart('chartPmi', 6, '#007aff');
        createComponentChart('chartRatio', 7, '#007aff');
        createComponentChart('chartT5yifr', 8, '#ff3b30');
        createComponentChart('chartCommodity', 9, '#ff3b30');

        // Row 3: Sentiment Components (0-100)
        createComponentChart('chartSentMom', 11, '#ff9500', sentimentOptions);
        createComponentChart('chartSentVix', 12, '#ff9500', sentimentOptions);
        createComponentChart('chartSentPC', 13, '#ff9500', sentimentOptions);
        createComponentChart('chartSentSafe', 14, '#ff9500', sentimentOptions);

        // Row 4: Sentiment (Junk) & Leading Components
        createComponentChart('chartSentJunk', 15, '#ff9500', sentimentOptions);
        createComponentChart('chartLeadCG', 16, '#34c759');
        createComponentChart('chartLeadBV', 17, '#34c759');
        createComponentChart('chartLeadYS', 18, '#34c759');

    } catch (error) {
        console.error("Error:", error);
    }
}

// Fix: Ensure DOM is fully loaded before initializing charts
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createCharts);
} else {
    createCharts();
}