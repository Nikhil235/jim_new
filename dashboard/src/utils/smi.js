/**
 * Calculates the Exponential Moving Average (EMA) of a data array.
 * @param {Array<number|null>} data - Input data series (can contain nulls for warmup)
 * @param {number} period - EMA period
 * @returns {Array<number|null>} EMA data series of the same length
 */
export function calculateEMA(data, period) {
  const alpha = 2 / (period + 1);
  const ema = new Array(data.length).fill(null);
  
  // Find the first index with a valid number
  let firstNonNullIdx = -1;
  for (let i = 0; i < data.length; i++) {
    if (data[i] !== null && data[i] !== undefined) {
      firstNonNullIdx = i;
      break;
    }
  }
  
  if (firstNonNullIdx === -1) return ema;
  
  // Initialize first EMA with the first available data point
  ema[firstNonNullIdx] = data[firstNonNullIdx];
  
  // Compute subsequent EMA values
  for (let i = firstNonNullIdx + 1; i < data.length; i++) {
    if (data[i] === null || data[i] === undefined) {
      ema[i] = null;
    } else {
      ema[i] = data[i] * alpha + ema[i - 1] * (1 - alpha);
    }
  }
  
  return ema;
}

/**
 * Applies double EMA smoothing to a data series.
 * @param {Array<number|null>} data - Input data series
 * @param {number} period - Smoothing period
 * @returns {Array<number|null>} Double smoothed data series
 */
export function doubleSmooth(data, period) {
  const ema1 = calculateEMA(data, period);
  return calculateEMA(ema1, period);
}

/**
 * Calculates the Stochastic Momentum Index (SMI) and Signal Line for a series of OHLC candles.
 * @param {Array<object>} ohlcData - Array of candles containing open, high, low, close
 * @param {number} kPeriod - Lookback period for highest high / lowest low (default: 13)
 * @param {number} dSmooth - Double smoothing period for D and range (default: 2)
 * @param {number} signalPeriod - Signal line EMA period (default: 3)
 * @returns {Array<object>} Original data array combined with calculated 'smi' and 'signal' values
 */
export function calculateSMI(ohlcData, kPeriod, dSmooth, signalPeriod) {
  const n = ohlcData.length;
  const highestHighs = new Array(n).fill(null);
  const lowestLows = new Array(n).fill(null);
  const D = new Array(n).fill(null);
  const range = new Array(n).fill(null);
  
  for (let i = 0; i < n; i++) {
    if (i < kPeriod - 1) {
      continue;
    }
    
    // Get lookback window [i - kPeriod + 1 ... i]
    let hh = -Infinity;
    let ll = Infinity;
    for (let j = i - kPeriod + 1; j <= i; j++) {
      const candle = ohlcData[j];
      if (candle.high > hh) hh = candle.high;
      if (candle.low < ll) ll = candle.low;
    }
    
    highestHighs[i] = hh;
    lowestLows[i] = ll;
    
    // Midpoint: M = (HH + LL) / 2
    const midpoint = (hh + ll) / 2;
    // Momentum: D = Close - M
    D[i] = ohlcData[i].close - midpoint;
    // Range: HH - LL
    range[i] = hh - ll;
  }
  
  // Apply double EMA smoothing to D and range
  const doubleSmoothed_D = doubleSmooth(D, dSmooth);
  const doubleSmoothed_range = doubleSmooth(range, dSmooth);
  
  const SMI = new Array(n).fill(null);
  for (let i = 0; i < n; i++) {
    const dsD = doubleSmoothed_D[i];
    const dsR = doubleSmoothed_range[i];
    
    if (dsD === null || dsR === null || dsR === 0) {
      SMI[i] = null;
    } else {
      // SMI formula: SMI = (doubleSmoothed_D / (doubleSmoothed_range / 2)) * 100
      SMI[i] = (dsD / (dsR / 2)) * 100;
    }
  }
  
  // Calculate Signal Line: EMA of SMI using Signal Period
  const signalLine = calculateEMA(SMI, signalPeriod);
  
  // Return original ohlcData mapped with smi and signal
  return ohlcData.map((candle, idx) => ({
    ...candle,
    smi: SMI[idx] !== null ? parseFloat(SMI[idx].toFixed(4)) : null,
    signal: signalLine[idx] !== null ? parseFloat(signalLine[idx].toFixed(4)) : null,
  }));
}
