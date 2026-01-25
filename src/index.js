// --- Chart Logic ---
async function createCharts() {
    try {
        // Ensure the path is correct for your environment
        const response = await fetch('/data/market_indices.json');
        if (!response.ok) throw new Error("Network response was not ok");
        const rawData = await response.json();

        // Map array data to charts
        // Index Map:
        // 0: date
        // 1: growth_index, 2: inflation_index, 3: liquidity_index, 4: sentiment_index, 5: leading_index
        // 6: z_pmi, 7: z_ratio, 8: z_t5yifr, 9: z_commodity, 10: net_liquidity_raw
        // 11: score_momentum, 12: score_vix, 13: score_putcall, 14: score_safehaven, 15: score_junk
        // 16: z_coppergold, 17: z_betavol, 18: z_yieldspread

        // Update "Last Updated" text
        if (rawData.length > 0) {
            const lastDate = rawData[rawData.length - 1][0]; // Last item, first element (date)
            document.getElementById('last-updated').textContent = `Last updated: ${lastDate}`;
        }

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
                            // Only show label if it's the 1st of the month
                            if (label && label.endsWith('-01')) {
                                return label.substring(0, 7); // Shows YYYY-MM
                            }
                            return null;
                        }
                    },
                    grid: { display: false }
                },
                y: { grid: { color: '#f0f0f0' } }
            },
            elements: { point: { radius: 0, hoverRadius: 4 } }
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
                            // Only show label if it's the 1st of the month
                            if (label && label.endsWith('-01')) {
                                return label.substring(0, 7); // Shows YYYY-MM
                            }
                            return null;
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
        const scatterData = recentData.map(d => ({ x: d[1], y: d[2], date: d[0] })); // Growth(1), Inflation(2), Date(0)

        // Calculate dynamic scale based on data
        const allXValues = scatterData.map(d => Math.abs(d.x));
        const allYValues = scatterData.map(d => Math.abs(d.y));
        const maxAbsValue = Math.max(...allXValues, ...allYValues);
        // Round up to nearest 0.5
        const scaleMax = Math.ceil(maxAbsValue * 2) / 2;

        // 2. Macro Regime Options (Scatter, Dynamic Scale)
        const scatterOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'point',
                intersect: true
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    // Only show one tooltip item at a time
                    filter: function (tooltipItem, index) {
                        // Only show the first tooltip item (closest point)
                        return index === 0;
                    },
                    callbacks: {
                        // Show the date for the hovered point (instead of reusing the dataset label for every point)
                        title: (items) => {
                            const raw = items?.[0]?.raw;
                            return raw?.date ?? '';
                        },
                        // Keep a compact value readout
                        label: (item) => {
                            const { x, y } = item.raw || {};
                            const fx = (typeof x === 'number') ? x.toFixed(2) : x;
                            const fy = (typeof y === 'number') ? y.toFixed(2) : y;
                            return `Growth: ${fx}, Inflation: ${fy}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    min: -scaleMax, max: scaleMax,
                    grid: { color: (ctx) => ctx.tick.value === 0 ? '#333' : '#eee', lineWidth: (ctx) => ctx.tick.value === 0 ? 1.5 : 1 }
                },
                y: {
                    min: -scaleMax, max: scaleMax,
                    grid: { color: (ctx) => ctx.tick.value === 0 ? '#333' : '#eee', lineWidth: (ctx) => ctx.tick.value === 0 ? 1.5 : 1 }
                }
            }
        };

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
        // createComponentChart('chartSentPC', 13, '#ff9500', sentimentOptions);
        createComponentChart('chartSentSafe', 14, '#ff9500', sentimentOptions);
        createComponentChart('chartSentJunk', 15, '#ff9500', sentimentOptions);

        // Row 4: Leading Components
        createComponentChart('chartLeadCG', 16, '#34c759');
        createComponentChart('chartLeadBV', 17, '#34c759');
        createComponentChart('chartLeadYS', 18, '#34c759');

    } catch (error) {
        console.error("Error:", error);
    }
}

// --- Router & Navigation Logic ---

const navigateTo = url => {
    history.pushState(null, null, url);
    handleLocation();
};

const handleLocation = async () => {
    const path = location.pathname;

    // Normalize path (handle trailing slashes or empty)
    // Simple route map
    let route = 'dashboard';
    if (path === '/about') route = 'about';
    if (path === '/references') route = 'references';

    // Show/Hide Sections
    const dashboardPage = document.getElementById('dashboard-page');
    const aboutPage = document.getElementById('about-page');
    const referencesPage = document.getElementById('references-page');

    if (dashboardPage) dashboardPage.style.display = (route === 'dashboard') ? '' : 'none';
    if (aboutPage) aboutPage.style.display = (route === 'about') ? '' : 'none';
    if (referencesPage) referencesPage.style.display = (route === 'references') ? '' : 'none';

    // Update Nav State
    const btnDashboard = document.getElementById('btn-dashboard');
    const btnAbout = document.getElementById('btn-about');
    const btnReferences = document.getElementById('btn-references');

    if (btnDashboard) btnDashboard.classList.toggle('nav-btn-active', route === 'dashboard');
    if (btnAbout) btnAbout.classList.toggle('nav-btn-active', route === 'about');
    if (btnReferences) btnReferences.classList.toggle('nav-btn-active', route === 'references');

    // Update Title & Meta Description
    const metaDesc = document.querySelector('meta[name="description"]');
    if (route === 'dashboard') {
        document.title = "Market Owl | Wise Market Regime Analysis";
        if (metaDesc) metaDesc.content = "Market Owl: Quantitative market regime dashboard visualizing Growth, Inflation, Liquidity, and Sentiment. See through the noise with data-driven insights.";
    }
    if (route === 'about') {
        document.title = "About MarketOwl.net";
        if (metaDesc) metaDesc.content = "Learn about Market Owl's quantitative methodology: How we track Global Net Liquidity, identify Market Regimes (Reflation vs Stagflation), and forecast trends.";
    }
    if (route === 'references') {
        document.title = "References | MarketOwl.net";
        if (metaDesc) metaDesc.content = "Trusted data sources and references used by Market Owl, including IMF, World Bank, FRED, and BIS data for macro-economic analysis.";
    }

    // If dashboard is shown and charts technically need resize or init (usually Chart.js handles resize fine if canvas exists)
    // We initialized charts once on load.
};

// Handle Browser Back/Forward
window.addEventListener("popstate", handleLocation);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // 1. Intercept navigation links
    document.body.addEventListener('click', e => {
        if (e.target.matches('[data-link]')) {
            e.preventDefault();
            navigateTo(e.target.href);
        }
    });

    // 2. Initial Route
    handleLocation();

    // 3. Initialize Charts (Only once)
    createCharts();
});