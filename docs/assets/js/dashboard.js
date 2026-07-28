/**
 * Tibia Ops Config - DevSecOps Dashboard
 * JavaScript for loading metrics and rendering charts
 */

// =============================================================================
// Configuration
// =============================================================================

const CONFIG = {
    metricsFile: 'data/metrics.json',
    refreshInterval: 300000, // 5 minutes
    chartColors: {
        blue: 'rgba(88, 166, 255, 1)',
        green: 'rgba(63, 185, 80, 1)',
        yellow: 'rgba(210, 153, 34, 1)',
        red: 'rgba(248, 81, 73, 1)',
        purple: 'rgba(163, 113, 247, 1)',
        blueAlpha: 'rgba(88, 166, 255, 0.2)',
        greenAlpha: 'rgba(63, 185, 80, 0.2)',
    }
};

// =============================================================================
// Initialize Dashboard
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    loadMetrics();
    setInterval(loadMetrics, CONFIG.refreshInterval);
});

// =============================================================================
// Chart Initialization
// =============================================================================

let pipelineChart = null;
let securityChart = null;

function initCharts() {
    // Pipeline Success/Failure Chart
    const pipelineCtx = document.getElementById('pipelineChart').getContext('2d');
    pipelineChart = new Chart(pipelineCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'CI Runs',
                    data: [],
                    borderColor: CONFIG.chartColors.blue,
                    backgroundColor: CONFIG.chartColors.blueAlpha,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'CD Deployments',
                    data: [],
                    borderColor: CONFIG.chartColors.green,
                    backgroundColor: CONFIG.chartColors.greenAlpha,
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Pipeline Activity (Last 30 Days)',
                    color: '#c9d1d9'
                },
                legend: {
                    labels: { color: '#8b949e' }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#8b949e' },
                    grid: { color: '#30363d' }
                },
                y: {
                    ticks: { color: '#8b949e' },
                    grid: { color: '#30363d' }
                }
            }
        }
    });

    // Security Scans Chart
    const securityCtx = document.getElementById('securityChart').getContext('2d');
    securityChart = new Chart(securityCtx, {
        type: 'doughnut',
        data: {
            labels: ['Passed', 'Warnings', 'Failed'],
            datasets: [{
                data: [85, 12, 3],
                backgroundColor: [
                    CONFIG.chartColors.green,
                    CONFIG.chartColors.yellow,
                    CONFIG.chartColors.red
                ],
                borderColor: '#21262d',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Security Scan Results',
                    color: '#c9d1d9'
                },
                legend: {
                    position: 'bottom',
                    labels: { color: '#8b949e' }
                }
            }
        }
    });
}

// =============================================================================
// Load Metrics Data
// =============================================================================

async function loadMetrics() {
    try {
        const response = await fetch(CONFIG.metricsFile);
        if (response.ok) {
            const data = await response.json();
            updateDashboard(data);
        } else {
            // Use sample data if metrics file not found
            updateDashboard(getSampleData());
        }
    } catch (error) {
        console.log('Using sample data:', error.message);
        updateDashboard(getSampleData());
    }
}

function getSampleData() {
    // Sample data for demonstration
    const now = new Date();
    const labels = [];
    const ciData = [];
    const cdData = [];

    for (let i = 29; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        ciData.push(Math.floor(Math.random() * 10) + 5);
        cdData.push(Math.floor(Math.random() * 5) + 1);
    }

    return {
        pipeline: {
            labels: labels,
            ci: ciData,
            cd: cdData,
            ciSuccessRate: '94%',
            cdSuccessRate: '98%',
            avgBuildTime: '2m 34s',
            totalDeployments: 127
        },
        security: {
            passed: 85,
            warnings: 12,
            failed: 3
        },
        application: {
            trollsTotal: 342,
            bastexTotal: 156,
            enemiesOnline: 7,
            apiCalls: 15420,
            worldsMonitored: 14,
            guildsMonitored: 2
        }
    };
}

// =============================================================================
// Update Dashboard
// =============================================================================

function updateDashboard(data) {
    // Update metric cards
    document.getElementById('ci-success-rate').textContent = data.pipeline.ciSuccessRate;
    document.getElementById('cd-success-rate').textContent = data.pipeline.cdSuccessRate;
    document.getElementById('avg-build-time').textContent = data.pipeline.avgBuildTime;
    document.getElementById('total-deployments').textContent = data.pipeline.totalDeployments;

    // Update pipeline chart
    pipelineChart.data.labels = data.pipeline.labels;
    pipelineChart.data.datasets[0].data = data.pipeline.ci;
    pipelineChart.data.datasets[1].data = data.pipeline.cd;
    pipelineChart.update();

    // Update security chart
    securityChart.data.datasets[0].data = [
        data.security.passed,
        data.security.warnings,
        data.security.failed
    ];
    securityChart.update();

    // Update application metrics
    const appMetricsContainer = document.getElementById('app-metrics');
    appMetricsContainer.innerHTML = `
        <div class="app-metric">
            <div class="app-metric-value">${data.application.trollsTotal}</div>
            <div class="app-metric-label">Total Trolls</div>
        </div>
        <div class="app-metric">
            <div class="app-metric-value">${data.application.bastexTotal}</div>
            <div class="app-metric-label">Bastex Members</div>
        </div>
        <div class="app-metric">
            <div class="app-metric-value">${data.application.enemiesOnline}</div>
            <div class="app-metric-label">Enemies Online</div>
        </div>
        <div class="app-metric">
            <div class="app-metric-value">${formatNumber(data.application.apiCalls)}</div>
            <div class="app-metric-label">API Calls</div>
        </div>
        <div class="app-metric">
            <div class="app-metric-value">${data.application.worldsMonitored}</div>
            <div class="app-metric-label">Worlds Monitored</div>
        </div>
        <div class="app-metric">
            <div class="app-metric-value">${data.application.guildsMonitored}</div>
            <div class="app-metric-label">Guilds Monitored</div>
        </div>
    `;
}

// =============================================================================
// Utility Functions
// =============================================================================

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}
