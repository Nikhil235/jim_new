# 📐 Mathematical Formulas & Algorithms Reference
### Mini-Medallion Gold Trading Engine

> Every formula here is a weapon. Combined, they form the arsenal.

---

## 1. Wavelet Transform (Signal De-noising)

### Discrete Wavelet Transform (DWT)

The DWT decomposes signal `x[n]` into approximation and detail coefficients:

```
Approximation:  cA[k] = Σ x[n] · φ(2^j · n - k)    (low-pass filter)
Detail:         cD[k] = Σ x[n] · ψ(2^j · n - k)    (high-pass filter)

Where:
  φ = scaling function (father wavelet)
  ψ = wavelet function (mother wavelet)
  j = decomposition level
  k = translation parameter
```

### De-noising Process
```
1. Decompose: x → [cA5, cD5, cD4, cD3, cD2, cD1]
2. Zero out noise: cD1 = 0, cD2 = 0  (high-frequency noise)
3. Reconstruct: x_clean = IDWT([cA5, cD5, cD4, cD3, 0, 0])
```

### Wavelet Choice for Gold
- **Daubechies-4 (db4)**: Best for financial time series (compact support, smooth)
- **Levels**: 5 (captures scales from minutes to days)

---

## 2. Hidden Markov Model (Regime Detection)

### Model Definition

```
λ = (A, B, π)

Where:
  A = State transition matrix [N × N]
      A[i][j] = P(state_t = j | state_{t-1} = i)

  B = Emission probability
      B[j](x) = P(observation = x | state = j)
      For Gaussian: B[j](x) = N(x | μ_j, Σ_j)

  π = Initial state distribution
      π[i] = P(state_0 = i)

  N = Number of hidden states (3 for gold: Crisis, Normal, Growth)
```

### Key Algorithms

**Forward Algorithm** (probability of observation sequence):
```
α_t(j) = [Σ_i α_{t-1}(i) · A[i][j]] · B[j](x_t)
P(observations | λ) = Σ_j α_T(j)
```

**Viterbi Algorithm** (most likely state sequence):
```
δ_t(j) = max_i [δ_{t-1}(i) · A[i][j]] · B[j](x_t)
Optimal path: backtrack from argmax δ_T(j)
```

**Baum-Welch** (parameter estimation via EM):
```
E-step: Compute γ_t(i) and ξ_t(i,j) using forward-backward
M-step: Update A, B, π to maximize expected log-likelihood
```

---

## 3. Genetic Algorithm (Strategy Evolution)

### Core Loop

```
INITIALIZE: Population P₀ of N random strategies
FOR generation g = 1 to G:
    1. EVALUATE: fitness(s) for each strategy s in P_g
    2. SELECT:   Top K strategies (tournament selection)
    3. CROSSOVER: Combine pairs → offspring
    4. MUTATE:   Random perturbation with probability p_m
    5. REPLACE:  P_{g+1} = offspring + elite survivors
```

### Fitness Function

```
fitness(strategy) = Sharpe × √(TradeCount) / (1 + MaxDrawdown)

Where:
  Sharpe = (mean_return - risk_free) / std_return × √252
  TradeCount penalizes strategies with too few trades
  MaxDrawdown penalizes large losses
```

### Crossover (Uniform)
```
Parent A: [a1, a2, a3, a4, a5]
Parent B: [b1, b2, b3, b4, b5]
Mask:     [ 1,  0,  1,  0,  1]
Child:    [a1, b2, a3, b4, a5]
```

### Mutation (Gaussian)
```
param_new = param_old + N(0, σ_mutation)
σ_mutation decreases over generations (simulated annealing)
```

---

## 4. Kelly Criterion (Position Sizing)

### Basic Kelly
```
f* = (p · b - q) / b

Where:
  f* = optimal fraction of capital to risk
  p  = probability of winning
  q  = 1 - p (probability of losing)
  b  = win/loss ratio (average win / average loss)
```

### Half-Kelly (Practical)
```
f_actual = f* / 2

Rationale: Full Kelly is optimal but has HUGE variance.
Half-Kelly sacrifices ~25% of growth for ~50% less volatility.
```

### Dynamic Kelly with Meta-Label
```
f_dynamic = (p_critic · b_rolling - q_critic) / (2 · b_rolling)

Where:
  p_critic  = Meta-Label Critic's confidence score
  b_rolling = Win/loss ratio from last 100 trades
  Divided by 2 = Half-Kelly safety
```

### Hard Constraints
```
f_final = min(f_dynamic, 0.05)     # Never exceed 5% of portfolio
if regime == CRISIS:
    f_final = f_final / 2           # Quarter-Kelly in crisis
```

---

## 5. Value at Risk (VaR) & Conditional VaR

### Parametric VaR
```
VaR_α = μ + z_α · σ

Where:
  α  = confidence level (0.95 or 0.99)
  z_α = standard normal quantile (-1.645 for 95%, -2.326 for 99%)
  μ  = portfolio mean return
  σ  = portfolio standard deviation
```

### Monte Carlo VaR (GPU-accelerated)
```
FOR i = 1 to 100,000:
    scenario_i = sample from multivariate return distribution
    pnl_i = portfolio · scenario_i
SORT all pnl values
VaR_95 = pnl at 5th percentile
CVaR_99 = mean of pnl values below 1st percentile
```

### CVaR (Expected Shortfall)
```
CVaR_α = E[Loss | Loss > VaR_α]
       = (1 / (1-α)) · ∫_{α}^{1} VaR_u · du

CVaR is ALWAYS worse than VaR — it tells you
"when things go bad, HOW bad on average?"
```

---

## 6. Deflated Sharpe Ratio (Anti-Overfitting)

```
DSR = Φ[(SR_observed - SR_expected) / σ_SR]

Where:
  SR_observed = Sharpe of your best strategy
  SR_expected = E[max(SR)] given N trials
              ≈ √(2 · ln(N)) · (1 - γ/ln(N)) + γ/√(2·ln(N))
  σ_SR = √((1 - γ₃·SR + (γ₄-1)/4·SR²) / T)
  γ₃ = skewness of returns
  γ₄ = kurtosis of returns
  T  = number of observations
  N  = number of strategies tested
  γ  = Euler-Mascheroni constant ≈ 0.5772
  Φ  = standard normal CDF

Rule: Deploy ONLY if DSR p-value < 0.05
```

---

## 7. Sharpe Ratio

```
SR = (R_p - R_f) / σ_p × √(252)

Where:
  R_p = mean daily portfolio return
  R_f = daily risk-free rate
  σ_p = standard deviation of daily returns
  √252 = annualization factor (trading days)
```

---

## 8. Sortino Ratio

```
Sortino = (R_p - R_f) / σ_downside × √(252)

Where:
  σ_downside = √(mean(min(R_i - R_f, 0)²))
  Only counts NEGATIVE deviations (ignores upside volatility)
```

---

## 9. Order Flow Imbalance (Microstructure)

```
OFI_t = Σ (bid_volume_change - ask_volume_change)

At each tick:
  If bid_price increases: bid_volume_change = +new_bid_size
  If bid_price decreases: bid_volume_change = -old_bid_size
  If bid_price unchanged: bid_volume_change = new_bid_size - old_bid_size
  (Mirror logic for ask side)

Interpretation:
  OFI > 0 → Buying pressure (bullish)
  OFI < 0 → Selling pressure (bearish)
```

---

## 10. Kyle's Lambda (Price Impact)

```
λ = ΔP / ΔV

Where:
  ΔP = price change
  ΔV = signed volume (positive for buys, negative for sells)

Estimated via regression:
  ΔP_t = α + λ · ΔV_t + ε_t

High λ = illiquid market (each trade moves price a lot)
Low λ  = liquid market (trades absorbed easily)
```

---

## Quick Reference Card

| Formula | Use | When |
|---------|-----|------|
| DWT | Clean price signal | Every tick |
| HMM | Detect market regime | Every hour |
| GA | Evolve strategy params | Weekly retraining |
| Kelly | Size positions | Every trade |
| VaR/CVaR | Risk budget | Every hour |
| DSR | Validate strategies | Before deployment |
| OFI | Read order flow | Every tick |
| Kyle's λ | Measure liquidity | Every 5 minutes |

---

*Back to [ROADMAP](../ROADMAP.md)*
