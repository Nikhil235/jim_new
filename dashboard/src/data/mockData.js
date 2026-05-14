// Mock data aligned with JIM backend (base.yaml + source code)

// Generate gold price data (2 years of daily bars)
function generatePriceData() {
  const data = [];
  let price = 1820;
  const start = new Date('2023-01-01');
  for (let i = 0; i < 500; i++) {
    const date = new Date(start);
    date.setDate(start.getDate() + i);
    if (date.getDay() === 0 || date.getDay() === 6) continue;
    const change = (Math.random() - 0.48) * 18;
    price = Math.max(1600, Math.min(2500, price + change));
    const vol = Math.random() * 8 + 2;
    data.push({
      date: date.toISOString().split('T')[0],
      open: +(price + (Math.random() - 0.5) * 6).toFixed(2),
      high: +(price + Math.random() * 12).toFixed(2),
      low: +(price - Math.random() * 12).toFixed(2),
      close: +price.toFixed(2),
      volume: Math.floor(Math.random() * 80000 + 20000),
      sma20: +(price - (Math.random() - 0.5) * 20).toFixed(2),
      sma50: +(price - (Math.random() - 0.5) * 40).toFixed(2),
      ema12: +(price - (Math.random() - 0.5) * 10).toFixed(2),
      rsi: +(Math.random() * 40 + 30).toFixed(1),
      volatility: +vol.toFixed(2),
      regime: Math.random() > 0.6 ? 'GROWTH' : Math.random() > 0.4 ? 'NORMAL' : 'CRISIS',
    });
  }
  return data;
}

export const priceData = generatePriceData();
export const recentPrices = priceData.slice(-90);
export const latestPrice = priceData[priceData.length - 1];

// Portfolio KPIs (backtest: initial_capital = $100,000)
export const portfolioKPIs = {
  portfolioValue: 127453.82,
  dailyPnL: 1243.56,
  dailyPnLPct: 0.98,
  totalReturn: 27.45,
  sharpeRatio: 2.34,
  winRate: 54.2,
  maxDrawdown: -6.8,
  totalTrades: 1247,
  openPositions: 3,
  goldPrice: latestPrice.close,
  goldChange: ((latestPrice.close - priceData[priceData.length - 2].close) / priceData[priceData.length - 2].close * 100),
  profitFactor: 1.67,
  commissionPerTrade: 2.50,
  slippageBps: 1.0,
};

// Regime detection — backend uses GROWTH / NORMAL / CRISIS
export const regimeData = {
  current: 'GROWTH',
  confidence: 0.73,
  probabilities: { GROWTH: 0.73, NORMAL: 0.19, CRISIS: 0.08 },
  history: priceData.slice(-30).map(d => ({
    date: d.date,
    GROWTH: +(Math.random() * 0.4 + 0.4).toFixed(2),
    NORMAL: +(Math.random() * 0.3 + 0.1).toFixed(2),
    CRISIS: +(Math.random() * 0.2 + 0.05).toFixed(2),
  })),
};

// Risk metrics — matches risk/manager.py & base.yaml
export const riskMetrics = {
  kellyFraction: 0.0312,
  kellyPositionSize: 3120,
  halfKelly: 1560,
  quarterKelly: 780,
  kellyConfig: { fraction: 0.5, maxPositionPct: 0.05, crisisFraction: 0.25 },
  dailyVaR95: -1842.50,
  dailyVaR99: -2891.30,
  cvar99: -3456.78,
  currentDrawdown: -2.3,
  maxDrawdownLimit: 10,
  dailyLossLimit: 2.0,
  currentDailyLoss: -0.45,
  circuitBreakers: {
    dailyLoss: { status: 'ok', value: -0.45, limit: -2.0 },
    drawdown: { status: 'ok', value: -2.3, limit: -10.0 },
    drawdownReduce: { status: 'ok', value: -2.3, limit: -5.0 },
    modelDisagreement: { status: 'warning', value: 0.62, limit: 0.70 },
    latency: { status: 'ok', value: 45, limit: 500 },
  },
  monteCarlo: {
    nSimulations: 100000,
    runFrequency: 'hourly',
    varConfidence: 0.95,
    cvarConfidence: 0.99,
  },
  monteCarloResults: Array.from({ length: 50 }, (_, i) => ({
    scenario: i,
    return: +(Math.random() * 60 - 15).toFixed(2),
    maxDD: +(Math.random() * -20).toFixed(2),
    sharpe: +(Math.random() * 3 + 0.5).toFixed(2),
  })),
};

// Model performance — matches base.yaml model configs
export const modelMetrics = {
  hmm: {
    accuracy: 0.681, lastTrained: '2026-05-14 08:00',
    regimeChanges: 14, logLikelihood: -234.5,
    config: { nRegimes: 3, covarianceType: 'full', nIter: 1000, retrainFrequency: 'daily' },
  },
  wavelet: {
    noiseRemoved: 34.2, bands: 5, snrImprovement: 8.4, family: 'db4',
    config: { family: 'db4', levels: 5, denoiseRemoveLevels: [1, 2] },
  },
  ensemble: {
    sharpe: 2.34, winRate: 0.542, profitFactor: 1.67, avgReturn: 0.12,
    config: { method: 'stacking', metaLearner: 'xgboost' },
  },
  lstm: {
    valLoss: 0.0023, epochs: 87, lr: 0.001, hiddenSize: 128,
    config: { hiddenSize: 128, numLayers: 3, bidirectional: true, dropout: 0.2, seqLength: 100, batchSize: 256, epochs: 100 },
  },
  genetic: {
    bestFitness: 2.87, generation: 412,
    config: { populationSize: 1000, generations: 500, crossoverProb: 0.7, mutationProb: 0.1, fitness: 'sharpe_adjusted', tournamentSize: 5 },
  },
};

// Trading signals
export const signals = [
  { id: 1, time: '14:32:05', type: 'LONG', source: 'HMM+Wavelet', confidence: 0.82, price: 2341.50, status: 'active' },
  { id: 2, time: '13:45:22', type: 'HOLD', source: 'Ensemble', confidence: 0.65, price: 2338.20, status: 'active' },
  { id: 3, time: '12:10:18', type: 'LONG', source: 'HMM', confidence: 0.71, price: 2335.80, status: 'filled' },
  { id: 4, time: '11:05:44', type: 'SHORT', source: 'Genetic', confidence: 0.58, price: 2340.10, status: 'expired' },
  { id: 5, time: '09:30:00', type: 'LONG', source: 'LSTM', confidence: 0.77, price: 2332.60, status: 'filled' },
];

// Trade history
export const tradeHistory = [
  { id: 'T-1247', date: '2026-05-14', side: 'BUY', qty: 2, entry: 2335.80, exit: 2341.50, pnl: 11.40, pnlPct: 0.49, model: 'HMM' },
  { id: 'T-1246', date: '2026-05-13', side: 'SELL', qty: 1, entry: 2348.20, exit: 2340.10, pnl: 8.10, pnlPct: 0.35, model: 'Ensemble' },
  { id: 'T-1245', date: '2026-05-13', side: 'BUY', qty: 3, entry: 2328.50, exit: 2342.30, pnl: 41.40, pnlPct: 0.59, model: 'Wavelet' },
  { id: 'T-1244', date: '2026-05-12', side: 'BUY', qty: 1, entry: 2320.00, exit: 2315.80, pnl: -4.20, pnlPct: -0.18, model: 'LSTM' },
  { id: 'T-1243', date: '2026-05-12', side: 'SELL', qty: 2, entry: 2345.60, exit: 2338.90, pnl: 13.40, pnlPct: 0.29, model: 'Genetic' },
  { id: 'T-1242', date: '2026-05-11', side: 'BUY', qty: 1, entry: 2310.20, exit: 2328.50, pnl: 18.30, pnlPct: 0.79, model: 'HMM' },
  { id: 'T-1241', date: '2026-05-11', side: 'SELL', qty: 2, entry: 2352.80, exit: 2345.60, pnl: 14.40, pnlPct: 0.31, model: 'Ensemble' },
  { id: 'T-1240', date: '2026-05-10', side: 'BUY', qty: 1, entry: 2305.00, exit: 2298.40, pnl: -6.60, pnlPct: -0.29, model: 'LSTM' },
];

// Equity curve
export const equityCurve = Array.from({ length: 180 }, (_, i) => {
  const date = new Date('2025-11-01');
  date.setDate(date.getDate() + i);
  return {
    date: date.toISOString().split('T')[0],
    equity: +(100000 + i * 150 + Math.sin(i / 10) * 2000 + Math.random() * 1500).toFixed(2),
    benchmark: +(100000 + i * 80 + Math.random() * 800).toFixed(2),
  };
});

// Feature importance — matches FeatureEngine output columns
export const featureImportance = [
  { name: 'rsi_14', importance: 0.142 },
  { name: 'macd_signal', importance: 0.128 },
  { name: 'wavelet_d1', importance: 0.115 },
  { name: 'volatility_20', importance: 0.098 },
  { name: 'sma_dist_20', importance: 0.087 },
  { name: 'corr_dxy_20', importance: 0.076 },
  { name: 'parkinson_vol_20', importance: 0.065 },
  { name: 'regime_prob', importance: 0.058 },
  { name: 'ema_dist_50', importance: 0.052 },
  { name: 'roc_50', importance: 0.045 },
  { name: 'position_in_range_20', importance: 0.041 },
  { name: 'atr_pct_14', importance: 0.038 },
];

// Feature engineering config
export const featureConfig = {
  lookbackWindows: [5, 10, 20, 50, 100, 200],
  volatilityWindows: [10, 20, 50],
  correlationWindows: [20, 50, 100],
  totalFeatures: 200,
  categories: [
    { name: 'Returns', count: 24, desc: 'Multi-horizon returns & log returns' },
    { name: 'Volatility', count: 18, desc: 'Realized & Parkinson volatility' },
    { name: 'Momentum', count: 42, desc: 'SMA, EMA, RSI, MACD, ROC' },
    { name: 'Price Levels', count: 24, desc: 'Support/resistance, ATR, ranges' },
    { name: 'Temporal', count: 6, desc: 'Cyclical hour/day/month encoding' },
    { name: 'Cross-Asset', count: 32, desc: 'DXY, VIX, TLT, TIPS correlations' },
    { name: 'Wavelet', count: 12, desc: 'Frequency band decomposition' },
  ],
};

// Infrastructure services — from docker-compose.yml
export const infraServices = [
  { name: 'QuestDB', port: '9000/9009', status: 'online', uptime: '99.9%', icon: '🗄️', bg: 'var(--blue-dim)', memory: '512 MB', detail: 'Time-series DB', version: '7.4.0' },
  { name: 'Redis', port: '6379', status: 'online', uptime: '99.9%', icon: '⚡', bg: 'var(--red-dim)', memory: '128 MB', detail: 'Feature Cache', version: '7.x' },
  { name: 'MinIO', port: '9100/9101', status: 'online', uptime: '99.8%', icon: '📦', bg: 'var(--orange-dim)', memory: '256 MB', detail: 'Object Storage (S3)', version: 'latest' },
  { name: 'MLflow', port: '5000', status: 'online', uptime: '99.7%', icon: '🧪', bg: 'var(--purple-dim)', memory: '384 MB', detail: 'Model Registry', version: '2.11.1' },
  { name: 'Prometheus', port: '9090', status: 'online', uptime: '99.9%', icon: '📊', bg: 'var(--green-dim)', memory: '192 MB', detail: 'Metrics (15s scrape)', version: '2.50.0' },
  { name: 'Grafana', port: '3000', status: 'online', uptime: '99.5%', icon: '📈', bg: 'var(--cyan)', memory: '256 MB', detail: 'Dashboards', version: '10.3.1' },
];

// GPU info — from src/utils/gpu.py detect_gpu()
export const gpuInfo = {
  name: 'RTX 3050 Laptop',
  vram: '4 GB',
  cudaVersion: '12.1',
  driver: '592.27',
  utilization: 34,
  temperature: 62,
  computeCapability: '8.6',
  rapids: false,
  cupy: false,
  cusignal: false,
  pytorch: true,
  cudnn: true,
};

// C++ Execution Engine — from src/execution/cpp/
export const executionEngine = {
  status: 'connected',
  broker: 'ibkr',
  mode: 'paper',
  orderType: 'limit',
  algo: 'twap',
  maxSlippageBps: 3.0,
  ibkr: { host: '127.0.0.1', port: 7497, clientId: 1 },
  cppEngine: {
    compiled: true,
    components: [
      { name: 'OrderRouter', status: 'active', desc: 'Smart venue routing + order management' },
      { name: 'LatencyMonitor', status: 'active', desc: 'p50/p95/p99 percentile tracking' },
      { name: 'OrderBook', status: 'active', desc: 'L3 order book with bid/ask levels' },
    ],
    latency: { p50: 12, p95: 45, p99: 89, unit: 'µs' },
  },
  recentOrders: [
    { id: 'ORD-4521', time: '14:32:05', symbol: 'XAU/USD', side: 'BUY', qty: 2, type: 'limit', price: 2341.50, status: 'filled', latency: 23 },
    { id: 'ORD-4520', time: '13:45:22', symbol: 'XAU/USD', side: 'SELL', qty: 1, type: 'limit', price: 2338.20, status: 'filled', latency: 18 },
    { id: 'ORD-4519', time: '12:10:18', symbol: 'XAU/USD', side: 'BUY', qty: 3, type: 'limit', price: 2335.80, status: 'filled', latency: 31 },
    { id: 'ORD-4518', time: '11:05:44', symbol: 'XAU/USD', side: 'SELL', qty: 2, type: 'limit', price: 2340.10, status: 'cancelled', latency: 15 },
  ],
};

// Phase tracking — from ROADMAP.md
export const phaseProgress = [
  { phase: 1, name: 'Infrastructure & Compute', status: 'complete', progress: 95, weeks: '1-3' },
  { phase: 2, name: 'Data Acquisition & Pipeline', status: 'in-progress', progress: 40, weeks: '2-5' },
  { phase: 3, name: 'Mathematical Modeling', status: 'not-started', progress: 0, weeks: '4-10' },
  { phase: 4, name: 'Risk Management & Meta-Label', status: 'not-started', progress: 0, weeks: '8-12' },
  { phase: 5, name: 'Backtesting & Validation', status: 'not-started', progress: 0, weeks: '10-14' },
  { phase: 6, name: 'Paper Trading & Deployment', status: 'not-started', progress: 0, weeks: '14-18' },
  { phase: 7, name: 'Team Culture & Operations', status: 'not-started', progress: 0, weeks: 'Ongoing' },
];

// Backtest config — from base.yaml
export const backtestConfig = {
  initialCapital: 100000,
  commissionPerTrade: 2.50,
  slippageBps: 1.0,
  walkForward: { trainYears: 3, testYears: 1 },
  targets: { minSharpe: 2.0, maxDrawdown: 0.10, minWinRate: 0.51, minProfitFactor: 1.5, dsrPvalue: 0.05 },
};

// Wavelet decomposition data
export const waveletBands = priceData.slice(-60).map(d => ({
  date: d.date,
  original: d.close,
  denoised: +(d.close + (Math.random() - 0.5) * 3).toFixed(2),
  d1: +(Math.random() * 4 - 2).toFixed(2),
  d2: +(Math.random() * 8 - 4).toFixed(2),
  d3: +(Math.random() * 12 - 6).toFixed(2),
  approximation: +(d.close + (Math.random() - 0.5) * 8).toFixed(2),
}));
