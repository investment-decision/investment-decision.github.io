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

// Fix: Ensure DOM is fully loaded before initializing charts
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createCharts);
} else {
    createCharts();
}