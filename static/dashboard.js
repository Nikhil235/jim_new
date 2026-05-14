/* ============================================
   Mini-Medallion Dashboard — JavaScript Engine
   ============================================ */

const API = '';  // Same origin
let ws = null;
let equityData = [];
let equityChart, allocationChart, pnlChart, modelConfChart;
let goldChart = null;
let goldCandleSeries = null;
let refreshInterval = null;
let goldRefreshInterval = null;
let liveSignalsInterval = null;
let currentGoldInterval = '15m';
let currentGoldPeriod = '5d';

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initCharts();
    updateClock();
    setInterval(updateClock, 1000);
    refreshAll();
    refreshInterval = setInterval(refreshAll, 5000);
    connectWebSocket();
    loadGoldChart('15m', '5d');
    // Auto-refresh gold chart every 60s
    goldRefreshInterval = setInterval(() => loadGoldChart(currentGoldInterval, currentGoldPeriod), 60000);
    // Live model signals — poll every 30s
    loadLiveSignals();
    liveSignalsInterval = setInterval(loadLiveSignals, 30000);
});

// ============================================
// NAVIGATION
// ============================================
function initNavigation() {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.dataset.section;
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            const target = document.getElementById('section-' + section);
            if (target) target.classList.add('active');
            if (section === 'trades') loadTrades();
            if (section === 'risk') loadRiskReport();
            if (section === 'models') loadModels();
        });
    });
}

function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent = now.toLocaleTimeString('en-US', { hour12: false });
}

// ============================================
// API CALLS
// ============================================
async function apiFetch(path, opts = {}) {
    try {
        const res = await fetch(API + path, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || err.error || res.statusText);
        }
        return await res.json();
    } catch (e) {
        log(`API Error: ${path} — ${e.message}`, 'error');
        throw e;
    }
}

async function apiPost(path, body) {
    return apiFetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
}

// ============================================
// REFRESH ALL DATA
// ============================================
async function refreshAll() {
    await Promise.allSettled([
        loadHealth(),
        loadStatus(),
        loadPortfolio(),
        loadPerformance(),
    ]);
}

// ============================================
// HEALTH
// ============================================
async function loadHealth() {
    try {
        const h = await apiFetch('/health');
        const grid = document.getElementById('healthGrid');

        // GPU status logic:
        // - green (ok): PyTorch CUDA available → GPU fully active
        // - yellow (warn): Hardware GPU exists but PyTorch is CPU-only
        // - red (fail): No GPU hardware at all
        let gpuStatus, gpuLabel;
        if (h.gpu_available) {
            gpuStatus = 'ok';
            const names = h.hardware_gpu_names && h.hardware_gpu_names.length
                ? h.hardware_gpu_names[0] : `GPU ×${h.gpu_count}`;
            gpuLabel = `GPU · ${names}`;
        } else if (h.hardware_gpu_detected) {
            gpuStatus = 'warn';
            const hwName = h.hardware_gpu_names && h.hardware_gpu_names.length
                ? h.hardware_gpu_names[0] : 'NVIDIA GPU';
            gpuLabel = `${hwName} (needs CUDA PyTorch)`;
        } else {
            gpuStatus = 'fail';
            gpuLabel = 'GPU (not detected)';
        }

        const items = [
            { name: 'API Server', status: 'ok' },
            { name: gpuLabel, status: gpuStatus },
            { name: 'Database', status: h.database_connected ? 'ok' : 'fail' },
            { name: 'Redis Cache', status: h.redis_connected ? 'ok' : 'fail' },
            { name: 'Models', status: h.models_loaded ? 'ok' : 'fail' },
            { name: 'WebSocket', status: (ws && ws.readyState === 1) ? 'ok' : 'fail' },
        ];
        grid.innerHTML = items.map(i =>
            `<div class="health-item ${i.status}"><span class="health-dot"></span><span>${i.name}</span></div>`
        ).join('');
        setConnection('connected', 'Connected');

        // Banner message with GPU detail
        let gpuMsg;
        if (h.gpu_available) {
            gpuMsg = `GPU: ${h.gpu_count} device(s) active`;
        } else if (h.hardware_gpu_detected) {
            const hw = h.hardware_gpu_names[0] || 'GPU';
            gpuMsg = `${hw} detected — install CUDA PyTorch to activate`;
        } else {
            gpuMsg = 'GPU: CPU mode';
        }
        setBanner('success', `Engine online — ${gpuMsg} | DB: ${h.database_connected ? '✓' : '✗'} | Redis: ${h.redis_connected ? '✓' : '✗'}`);
    } catch {
        setConnection('error', 'Disconnected');
        setBanner('error', 'Cannot reach API server. Is it running?');
    }
}

// ============================================
// STATUS
// ============================================
async function loadStatus() {
    try {
        const s = await apiFetch('/paper-trading/status');
        document.getElementById('engineStatus').textContent = s.status;
        document.getElementById('engineStatus').style.color = s.status === 'RUNNING' ? 'var(--green)' : 'var(--yellow)';
        document.getElementById('engineUptime').textContent = s.uptime_seconds ? formatDuration(s.uptime_seconds) : '--';
        document.getElementById('tradesToday').textContent = s.trading.daily_trades;
        document.getElementById('totalTrades').textContent = s.trading.num_trades;
        document.getElementById('positionQty').textContent = s.portfolio.position_quantity;
        document.getElementById('positionStatus').textContent = s.trading.position_status || 'FLAT';

        // KPIs from status
        setKPI('kpiTotalValue', formatCurrency(s.portfolio.total_value));
        setKPI('kpiPnl', formatCurrency(s.portfolio.pnl_total), s.portfolio.pnl_total);
        setKPI('kpiDailyPnl', formatCurrency(s.portfolio.pnl_daily), s.portfolio.pnl_daily);
        setKPI('kpiReturn', s.portfolio.return_pct.toFixed(2) + '%', s.portfolio.return_pct);

        // Update allocation chart
        updateAllocation(s.portfolio.cash, s.portfolio.position_value);

        // Update models section with signal counts
        if (s.models) updateModelCards(s.models);

        // Track equity over time
        equityData.push({ time: new Date(), value: s.portfolio.total_value });
        if (equityData.length > 500) equityData.shift();
        updateEquityChart();
    } catch {
        // Engine not started yet
        document.getElementById('engineStatus').textContent = 'NOT STARTED';
        document.getElementById('engineStatus').style.color = 'var(--text-muted)';
    }
}

// ============================================
// PORTFOLIO & PERFORMANCE
// ============================================
async function loadPortfolio() {
    try {
        const p = await apiFetch('/paper-trading/portfolio');
        document.getElementById('maxDrawdown').textContent = p.max_drawdown.toFixed(2) + '%';
    } catch { /* engine not started */ }
}

async function loadPerformance() {
    try {
        const p = await apiFetch('/paper-trading/performance');
        setKPI('kpiSharpe', p.sharpe_ratio.toFixed(2));
        setKPI('kpiWinRate', (p.win_rate * 100).toFixed(0) + '%');
    } catch { /* engine not started */ }
}

// ============================================
// TRADES
// ============================================
async function loadTrades() {
    try {
        const filter = document.getElementById('tradeFilter').value;
        const url = `/paper-trading/trades?limit=50${filter !== 'ALL' ? '&status_filter=' + filter : ''}`;
        const trades = await apiFetch(url);
        const list = Array.isArray(trades) ? trades : (trades.value || []);
        const tbody = document.getElementById('tradesBody');

        if (list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="empty-state">No trades yet.</td></tr>';
            updatePnlChart([]);
            return;
        }

        tbody.innerHTML = list.map(t => `
            <tr>
                <td>${t.trade_id.slice(0, 8)}</td>
                <td>${t.model_name}</td>
                <td><span class="badge ${t.signal_type.toLowerCase()}">${t.signal_type}</span></td>
                <td>$${t.entry_price.toFixed(2)}</td>
                <td>${t.exit_price ? '$' + t.exit_price.toFixed(2) : '—'}</td>
                <td>${t.quantity.toFixed(2)}</td>
                <td class="${t.pnl >= 0 ? 'positive' : 'negative'}">${formatCurrency(t.pnl)}</td>
                <td class="${t.pnl_pct >= 0 ? 'positive' : 'negative'}">${t.pnl_pct.toFixed(2)}%</td>
                <td><span class="badge ${t.status.toLowerCase()}">${t.status}</span></td>
                <td>${new Date(t.entry_time).toLocaleTimeString()}</td>
            </tr>
        `).join('');

        updatePnlChart(list.filter(t => t.status === 'CLOSED'));
    } catch { /* engine not started */ }
}

// ============================================
// RISK
// ============================================
async function loadRiskReport() {
    try {
        const r = await apiFetch('/paper-trading/risk-report');
        const rr = r.risk_report;
        const limits = rr.risk_limits;

        // Gauges
        setGauge('gaugeDrawdown', rr.drawdown_pct, limits.max_drawdown_pct);
        setGauge('gaugeDailyLoss', Math.abs(rr.daily_loss_pct), limits.max_daily_loss_pct);
        setGauge('gaugeConsecLoss', rr.consecutive_losses, limits.max_consecutive_losses);

        // Position gauge — calculate from portfolio
        try {
            const p = await apiFetch('/paper-trading/portfolio');
            const posPct = p.total_value > 0 ? (p.position_value / p.total_value) * 100 : 0;
            setGauge('gaugePosition', posPct, limits.max_position_pct);
        } catch { setGauge('gaugePosition', 0, limits.max_position_pct); }

        // Details
        const details = document.getElementById('riskDetails');
        details.innerHTML = `
            <div class="status-item"><span class="status-label">Current Equity</span><span class="status-value">${formatCurrency(rr.current_equity)}</span></div>
            <div class="status-item"><span class="status-label">Peak Equity</span><span class="status-value">${formatCurrency(rr.peak_equity)}</span></div>
            <div class="status-item"><span class="status-label">Drawdown</span><span class="status-value ${rr.drawdown_pct > 10 ? 'negative' : ''}">${rr.drawdown_pct.toFixed(2)}%</span></div>
            <div class="status-item"><span class="status-label">Daily P&L</span><span class="status-value">${formatCurrency(rr.daily_pnl)}</span></div>
            <div class="status-item"><span class="status-label">Consecutive Losses</span><span class="status-value">${rr.consecutive_losses}</span></div>
            <div class="status-item"><span class="status-label">Violations</span><span class="status-value" style="color:${rr.violations.length ? 'var(--red)' : 'var(--green)'}">${rr.violations.length ? rr.violations.join(', ') : 'None ✓'}</span></div>
        `;
    } catch {
        document.getElementById('riskDetails').innerHTML = '<p class="empty-state">Start engine to see risk data.</p>';
    }
}

function setGauge(prefix, value, limit) {
    const pct = limit > 0 ? Math.min(value / limit, 1) : 0;
    const circumference = 2 * Math.PI * 52; // r=52
    const offset = circumference * (1 - pct);
    const fill = document.getElementById(prefix + 'Fill');
    const valEl = document.getElementById(prefix + 'Val');
    if (fill) {
        fill.style.strokeDasharray = circumference;
        fill.style.strokeDashoffset = offset;
        fill.classList.remove('safe', 'warning', 'danger');
        if (pct < 0.5) fill.classList.add('safe');
        else if (pct < 0.8) fill.classList.add('warning');
        else fill.classList.add('danger');
    }
    if (valEl) {
        valEl.textContent = typeof limit === 'number' && limit <= 10 ? Math.round(value) : value.toFixed(1) + '%';
    }
}

// ============================================
// MODELS
// ============================================
// ============================================
// LIVE MODEL SIGNALS
// ============================================
async function loadLiveSignals() {
    try {
        const data = await apiFetch('/paper-trading/live-signals');
        if (data && data.models) {
            updateModelCardsLive(data.models, data.current_price, data.inference_running, data.iteration);
        }
    } catch { /* engine not running yet */ }
}

function updateModelCardsLive(models, goldPrice, inferenceRunning, iteration) {
    const icons = { wavelet: '🌊', hmm: '📊', lstm: '🧠', tft: '⚡', genetic: '🧬', ensemble: '🎯' };
    const colors = { wavelet: '#3b82f6', hmm: '#a855f7', lstm: '#06b6d4', tft: '#f59e0b', genetic: '#22c55e', ensemble: '#ef4444' };
    const signalColors = { LONG: 'var(--green)', SHORT: 'var(--red)', HOLD: 'var(--text-muted)', null: 'var(--text-muted)' };
    const signalBg = { LONG: 'var(--green-bg)', SHORT: 'var(--red-bg)', HOLD: 'rgba(100,116,139,.12)', null: 'transparent' };

    const grid = document.getElementById('modelsGrid');
    if (!grid) return;

    // Status badge
    const statusBadge = inferenceRunning
        ? `<span style="font-size:.65rem;color:var(--green);background:var(--green-bg);padding:.1rem .4rem;border-radius:4px;">● LIVE</span>`
        : `<span style="font-size:.65rem;color:var(--text-muted);background:var(--bg-input);padding:.1rem .4rem;border-radius:4px;">○ IDLE</span>`;

    grid.innerHTML = Object.entries(models).map(([name, data]) => {
        const sig = data.signal || 'IDLE';
        const conf = ((data.confidence || 0) * 100).toFixed(0);
        const updatedAgo = data.last_updated
            ? secondsAgo(data.last_updated) + 's ago'
            : 'never';
        const reasoning = (data.reasoning || '').slice(0, 90) || 'Awaiting first inference cycle...';
        const confBar = `<div style="height:3px;border-radius:2px;background:var(--border);margin-top:.4rem;">
            <div style="height:100%;border-radius:2px;width:${conf}%;background:${signalColors[sig]};transition:width .6s ease;"></div></div>`;

        return `<div class="model-card" style="border-color:${sig !== 'HOLD' && sig !== 'IDLE' ? signalColors[sig] + '60' : 'var(--border-light)'}">
            <div class="model-name">
                <div class="model-icon" style="background:${colors[name]}20;color:${colors[name]}">${icons[name] || '📈'}</div>
                <span>${name}</span>
                <span style="margin-left:auto;font-size:.7rem;font-weight:700;color:${signalColors[sig]};background:${signalBg[sig]};padding:.15rem .4rem;border-radius:4px;">${sig}</span>
            </div>
            <div class="model-stats">
                <div class="model-stat">
                    <span class="model-stat-label">Confidence</span>
                    <span class="model-stat-value" style="color:${signalColors[sig]}">${conf}%</span>
                </div>
                <div class="model-stat">
                    <span class="model-stat-label">Regime</span>
                    <span class="model-stat-value">${data.regime || '—'}</span>
                </div>
                <div class="model-stat">
                    <span class="model-stat-label">Updated</span>
                    <span class="model-stat-value" style="color:var(--text-muted);font-size:.7rem">${updatedAgo}</span>
                </div>
            </div>
            ${confBar}
            <div style="font-size:.68rem;color:var(--text-muted);margin-top:.5rem;line-height:1.3;font-style:italic">${reasoning}</div>
        </div>`;
    }).join('');

    // Update inference header info
    const header = document.querySelector('#section-models .section-header h2');
    if (header) {
        header.innerHTML = `Model Signals &nbsp;${statusBadge} &nbsp;<span style="font-size:.7rem;color:var(--text-muted);font-weight:400;">iter #${iteration} | Gold $${(goldPrice||0).toFixed(2)}</span>`;
    }

    // Update confidence radar chart
    if (modelConfChart) {
        const labels = Object.keys(models);
        const vals = Object.values(models).map(m => (m.confidence || 0) * 100);
        modelConfChart.data.labels = labels;
        modelConfChart.data.datasets[0].data = vals;
        modelConfChart.update('none');
    }
}

function secondsAgo(isoString) {
    if (!isoString) return '?';
    const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    return diff < 0 ? 0 : diff;
}

function updateModelCards(models) {
    // Legacy: called by /paper-trading/status — merge with live signal data
    // Only update signal counts; live confidence is from loadLiveSignals()
    const icons = { wavelet: '🌊', hmm: '📊', lstm: '🧠', tft: '⚡', genetic: '🧬', ensemble: '🎯' };
    const colors = { wavelet: '#3b82f6', hmm: '#a855f7', lstm: '#06b6d4', tft: '#f59e0b', genetic: '#22c55e', ensemble: '#ef4444' };
    const grid = document.getElementById('modelsGrid');
    if (!grid || grid.children.length > 0) return; // Don't overwrite live cards
    grid.innerHTML = Object.entries(models).map(([name, data]) => `
        <div class="model-card">
            <div class="model-name">
                <div class="model-icon" style="background:${colors[name]}20;color:${colors[name]}">${icons[name] || '📈'}</div>
                ${name}
            </div>
            <div class="model-stats">
                <div class="model-stat"><span class="model-stat-label">Last Signal</span><span class="model-stat-value">${data.last_signal || '—'}</span></div>
                <div class="model-stat"><span class="model-stat-label">Confidence</span><span class="model-stat-value">${(data.confidence * 100).toFixed(0)}%</span></div>
                <div class="model-stat"><span class="model-stat-label">Signals</span><span class="model-stat-value">${data.signal_count}</span></div>
            </div>
        </div>
    `).join('');

    // Update confidence chart
    if (modelConfChart) {
        const labels = Object.keys(models);
        const vals = Object.values(models).map(m => m.confidence * 100);
        modelConfChart.data.labels = labels;
        modelConfChart.data.datasets[0].data = vals;
        modelConfChart.update('none');
    }
}

async function loadModels() {
    try {
        const s = await apiFetch('/paper-trading/status');
        if (s.models) updateModelCards(s.models);
    } catch { /* engine not started */ }
}

// ============================================
// CHARTS
// ============================================
const chartDefaults = { responsive: true, maintainAspectRatio: false, animation: { duration: 300 } };
const gridColor = 'rgba(42,53,80,.5)';
const tickColor = '#64748b';

function initCharts() {
    // Equity curve
    equityChart = new Chart(document.getElementById('equityChart'), {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Portfolio Value', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,.08)', fill: true, tension: .4, pointRadius: 0, borderWidth: 2 }] },
        options: { ...chartDefaults, scales: { x: { display: true, grid: { color: gridColor }, ticks: { color: tickColor, maxTicksLimit: 8, font: { size: 10 } } }, y: { grid: { color: gridColor }, ticks: { color: tickColor, callback: v => '$' + (v/1000).toFixed(0) + 'k', font: { size: 10 } } } }, plugins: { legend: { display: false } } }
    });

    // Allocation donut
    allocationChart = new Chart(document.getElementById('allocationChart'), {
        type: 'doughnut',
        data: { labels: ['Cash', 'Position'], datasets: [{ data: [100, 0], backgroundColor: ['#3b82f6', '#f59e0b'], borderWidth: 0, hoverOffset: 4 }] },
        options: { ...chartDefaults, cutout: '72%', plugins: { legend: { display: false } } }
    });

    // P&L bar chart
    pnlChart = new Chart(document.getElementById('pnlChart'), {
        type: 'bar',
        data: { labels: [], datasets: [{ label: 'P&L', data: [], backgroundColor: [], borderRadius: 4 }] },
        options: { ...chartDefaults, scales: { x: { grid: { display: false }, ticks: { color: tickColor, font: { size: 10 } } }, y: { grid: { color: gridColor }, ticks: { color: tickColor, callback: v => '$' + v, font: { size: 10 } } } }, plugins: { legend: { display: false } } }
    });

    // Model confidence radar
    modelConfChart = new Chart(document.getElementById('modelConfChart'), {
        type: 'radar',
        data: { labels: ['wavelet', 'hmm', 'lstm', 'tft', 'genetic', 'ensemble'], datasets: [{ label: 'Confidence %', data: [0, 0, 0, 0, 0, 0], borderColor: '#a855f7', backgroundColor: 'rgba(168,85,247,.15)', pointBackgroundColor: '#a855f7', pointRadius: 4 }] },
        options: { ...chartDefaults, scales: { r: { beginAtZero: true, max: 100, grid: { color: gridColor }, angleLines: { color: gridColor }, pointLabels: { color: tickColor, font: { size: 11, weight: '600' } }, ticks: { color: tickColor, backdropColor: 'transparent', font: { size: 9 } } } }, plugins: { legend: { display: false } } }
    });
}

function updateEquityChart() {
    const labels = equityData.map(d => d.time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    const values = equityData.map(d => d.value);
    equityChart.data.labels = labels;
    equityChart.data.datasets[0].data = values;
    equityChart.update('none');
}

function updateAllocation(cash, positionValue) {
    allocationChart.data.datasets[0].data = [cash, positionValue];
    allocationChart.update('none');
}

function updatePnlChart(closedTrades) {
    if (!closedTrades.length) return;
    pnlChart.data.labels = closedTrades.map((_, i) => '#' + (i + 1));
    pnlChart.data.datasets[0].data = closedTrades.map(t => t.pnl);
    pnlChart.data.datasets[0].backgroundColor = closedTrades.map(t => t.pnl >= 0 ? 'rgba(34,197,94,.7)' : 'rgba(239,68,68,.7)');
    pnlChart.update('none');
}

function setEquityRange(range) {
    document.querySelectorAll('.card-actions .chip').forEach(c => c.classList.remove('active'));
    event.target.classList.add('active');
}

// ============================================
// GOLD CANDLESTICK CHART
// ============================================
async function loadGoldChart(interval = '15m', period = '5d') {
    // Track current selection for auto-refresh
    currentGoldInterval = interval;
    currentGoldPeriod = period;

    // Update active chip buttons
    document.querySelectorAll('#goldChartContainer').forEach(() => {});
    document.querySelectorAll('.card-header .chip[onclick*="loadGoldChart"]').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('onclick').includes(`'${interval}','${period}'`));
    });

    const container = document.getElementById('goldChartContainer');
    if (!container) return;

    try {
        const data = await apiFetch(`/gold-price?interval=${interval}&period=${period}`);

        // Update price display
        document.getElementById('goldCurrentPrice').textContent = '$' + data.current_price.toFixed(2);
        const changeEl = document.getElementById('goldPriceChange');
        const sign = data.change >= 0 ? '+' : '';
        changeEl.textContent = `${sign}${data.change.toFixed(2)} (${sign}${data.change_pct.toFixed(2)}%)`;
        changeEl.style.color = data.change >= 0 ? 'var(--green)' : 'var(--red)';

        // Convert timestamps to lightweight-charts format (seconds)
        const candles = data.candles.map(c => ({
            time: Math.floor(c.time / 1000),
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
        }));

        const volumeData = data.candles.map(c => ({
            time: Math.floor(c.time / 1000),
            value: c.volume,
            color: c.close >= c.open ? 'rgba(34,197,94,.3)' : 'rgba(239,68,68,.3)',
        }));

        // Destroy previous chart instance
        container.innerHTML = '';

        goldChart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 360,
            layout: {
                background: { type: 'solid', color: '#1a2235' },
                textColor: '#94a3b8',
                fontSize: 11,
                fontFamily: 'Inter, sans-serif',
            },
            grid: {
                vertLines: { color: 'rgba(42,53,80,.4)' },
                horzLines: { color: 'rgba(42,53,80,.4)' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: { color: 'rgba(245,158,11,.4)', labelBackgroundColor: '#f59e0b' },
                horzLine: { color: 'rgba(245,158,11,.4)', labelBackgroundColor: '#f59e0b' },
            },
            rightPriceScale: {
                borderColor: 'rgba(42,53,80,.6)',
            },
            timeScale: {
                borderColor: 'rgba(42,53,80,.6)',
                timeVisible: true,
                secondsVisible: false,
            },
            handleScroll: true,
            handleScale: true,
        });

        goldCandleSeries = goldChart.addCandlestickSeries({
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderDownColor: '#ef4444',
            borderUpColor: '#22c55e',
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });
        goldCandleSeries.setData(candles);

        // Volume histogram
        const volumeSeries = goldChart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: '',
        });
        volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.85, bottom: 0 },
        });
        volumeSeries.setData(volumeData);

        goldChart.timeScale().fitContent();

        // Resize observer to keep chart full width
        if (window.ResizeObserver) {
            const ro = new ResizeObserver(() => {
                if (goldChart) goldChart.applyOptions({ width: container.clientWidth });
            });
            ro.observe(container);
        }

        log(`Gold chart updated: ${data.count} candles · ${interval}/${period} · $${data.current_price.toFixed(2)}`, 'success');
    } catch (e) {
        container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:.9rem">Failed to load gold data: ${e.message}</div>`;
    }
}

// ============================================
// ENGINE CONTROLS
// ============================================
async function startEngine() {
    try {
        const body = {
            initial_capital: parseFloat(document.getElementById('ctrlCapital').value),
            kelly_fraction: parseFloat(document.getElementById('ctrlKelly').value),
            max_position_pct: parseFloat(document.getElementById('ctrlMaxPos').value) / 100,
            max_daily_loss_pct: parseFloat(document.getElementById('ctrlMaxDailyLoss').value) / 100,
            min_confidence: parseFloat(document.getElementById('ctrlMinConf').value),
        };
        const res = await apiPost('/paper-trading/start', body);
        log(`Engine started! Capital: $${body.initial_capital.toLocaleString()}`, 'success');
        setBanner('success', `Paper trading started with $${body.initial_capital.toLocaleString()} capital`);
        equityData = [];
        refreshAll();
    } catch (e) { log('Failed to start: ' + e.message, 'error'); }
}

async function stopEngine() {
    if (!confirm('Stop paper trading and close all positions?')) return;
    try {
        const res = await apiPost('/paper-trading/stop', {});
        log('Engine stopped. ' + JSON.stringify(res.details || {}), 'warn');
        refreshAll();
    } catch (e) { log('Failed to stop: ' + e.message, 'error'); }
}

async function injectSignal() {
    try {
        const body = {
            model_name: document.getElementById('sigModel').value,
            signal_type: document.getElementById('sigType').value,
            confidence: parseFloat(document.getElementById('sigConf').value),
            price: parseFloat(document.getElementById('sigPrice').value),
            regime: document.getElementById('sigRegime').value,
            reasoning: 'Manual dashboard injection',
        };
        const res = await apiPost('/paper-trading/signal', body);
        const traded = res.trade_executed ? `Trade executed: ${res.trade.trade_id}` : 'Signal skipped (below threshold)';
        log(`Signal injected: ${body.model_name} ${body.signal_type} @ $${body.price} — ${traded}`, res.trade_executed ? 'success' : 'warn');
        refreshAll();
    } catch (e) { log('Signal failed: ' + e.message, 'error'); }
}

async function resetDaily() {
    try {
        const res = await apiPost('/paper-trading/reset-daily', {});
        log(`Daily counters reset. Previous daily P&L: $${res.previous_daily_pnl?.toFixed(2) || 0}`, 'success');
        refreshAll();
    } catch (e) { log('Reset failed: ' + e.message, 'error'); }
}

// ============================================
// WEBSOCKET
// ============================================
function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/paper-trading/ws`;
    try {
        ws = new WebSocket(wsUrl);
        ws.onopen = () => {
            log('WebSocket connected', 'success');
            updateWSHealth(true);
        };
        ws.onmessage = (e) => {
            try {
                const msg = JSON.parse(e.data);
                if (msg.event === 'portfolio_update' && msg.data) {
                    equityData.push({ time: new Date(), value: msg.data.total_value });
                    if (equityData.length > 500) equityData.shift();
                    updateEquityChart();
                    setKPI('kpiTotalValue', formatCurrency(msg.data.total_value));
                    setKPI('kpiPnl', formatCurrency(msg.data.pnl_total), msg.data.pnl_total);
                }
                if (msg.event === 'trade_executed') {
                    log(`Trade: ${msg.data.signal_type} @ $${msg.data.entry_price}`, 'success');
                    loadTrades();
                }
                // Live model signals via WebSocket (faster than polling)
                if (msg.event === 'model_signals_update' && msg.data && msg.data.models) {
                    updateModelCardsLive(
                        msg.data.models,
                        msg.data.price,
                        true,
                        msg.data.iteration || 0
                    );
                }
            } catch { /* ignore parse errors */ }
        };
        ws.onclose = () => {
            updateWSHealth(false);
            setTimeout(connectWebSocket, 3000);
        };
        ws.onerror = () => { updateWSHealth(false); };
    } catch { setTimeout(connectWebSocket, 5000); }
}

function updateWSHealth(ok) {
    const items = document.querySelectorAll('#healthGrid .health-item');
    items.forEach(item => {
        if (item.textContent.includes('WebSocket')) {
            item.className = 'health-item ' + (ok ? 'ok' : 'fail');
        }
    });
}

// ============================================
// HELPERS
// ============================================
function formatCurrency(val) {
    if (val == null) return '$0.00';
    const sign = val < 0 ? '-' : (val > 0 ? '+' : '');
    return (val >= 0 ? '' : '-') + '$' + Math.abs(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDuration(seconds) {
    if (seconds < 60) return Math.round(seconds) + 's';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ' + Math.round(seconds % 60) + 's';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return h + 'h ' + m + 'm';
}

function setKPI(id, text, numVal) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
    if (numVal !== undefined) {
        el.style.color = numVal > 0 ? 'var(--green)' : numVal < 0 ? 'var(--red)' : '';
    }
}

function setConnection(state, text) {
    const el = document.getElementById('connectionStatus');
    el.className = 'connection-status ' + state;
    el.querySelector('.status-text').textContent = text;
}

function setBanner(type, text) {
    const banner = document.getElementById('systemBanner');
    banner.className = 'system-banner ' + type;
    document.getElementById('bannerText').textContent = text;
}

function log(msg, type = '') {
    const body = document.getElementById('logBody');
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    body.innerHTML = `<div class="log-entry ${type}"><span class="log-time">${time}</span>${msg}</div>` + body.innerHTML;
    // Keep max 100 entries
    while (body.children.length > 100) body.removeChild(body.lastChild);
}
