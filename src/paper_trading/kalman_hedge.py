import numpy as np
from loguru import logger

class KalmanHedgeEngine:
    """
    Maintains a rolling hedge ratio (β) using a Kalman Filter to track 
    the dynamic relationship between Gold (XAUUSD) and Silver (XAGUSD).
    
    If we go LONG 1 lot of Gold, we SHORT β lots of Silver.
    """
    def __init__(self, delta=1e-4, vt=1e-3, min_beta=0.5, max_beta=1.5):
        # State vector: [beta (slope), alpha (intercept)]
        self.theta = np.zeros(2)
        # Covariance matrix
        self.P = np.zeros((2, 2))
        
        # Process noise (how fast beta/alpha can change)
        self.Q = np.eye(2) * delta
        # Measurement noise (variance of observation)
        self.R = vt
        
        # Constraints
        self.min_beta = min_beta
        self.max_beta = max_beta
        
        # To handle uninitialized state
        self.is_initialized = False

    def update(self, x_price: float, y_price: float) -> float:
        """
        Update the Kalman filter with new prices.
        We treat Gold (XAU) as y and Silver (XAG) as x.
        Or, typically, we use normalized price returns or contract-value adjusted prices
        so that beta naturally floats around 1.0.
        
        For simplicity, let's assume the inputs are pre-scaled (e.g., $ value of 1 Lot of Gold vs 1 Lot of Silver).
        y_t = x_t * beta + alpha + noise
        """
        # If using raw prices (Gold=$2000, Silver=$25), a pure beta is ~80.
        # To output a beta in [0.5, 1.5] corresponding to "lots", we assume
        # x_price and y_price passed here are the nominal values of 1 contract of each.
        
        F = np.array([x_price, 1.0])
        
        if not self.is_initialized:
            # First observation: initialize beta directly to y/x
            self.theta[0] = y_price / x_price if x_price != 0 else 1.0
            self.theta[1] = 0.0
            self.P = np.eye(2)
            self.is_initialized = True
            return self._clip_beta(self.theta[0])

        # Prediction Step
        # theta(t|t-1) = theta(t-1|t-1)
        # P(t|t-1) = P(t-1|t-1) + Q
        R_pred = self.P + self.Q
        
        # Measurement Prediction
        y_pred = F.dot(self.theta)
        
        # Innovation (Prediction Error)
        e = y_price - y_pred
        
        # Innovation Variance
        S = F.dot(R_pred).dot(F) + self.R
        
        # Kalman Gain
        K = R_pred.dot(F) / S
        
        # Update Step
        self.theta = self.theta + K * e
        self.P = R_pred - np.outer(K, F).dot(R_pred)
        
        raw_beta = self.theta[0]
        return self._clip_beta(raw_beta)

    def _clip_beta(self, beta: float) -> float:
        """Enforces the user-defined bounds on the hedge ratio."""
        return max(self.min_beta, min(self.max_beta, beta))

    def get_hedge_size(self, gold_size: float, raw_beta: float, regime: str) -> float:
        """
        Calculates the final Silver hedge size based on the current regime.
        - NORMAL/RANGING: 100% hedge
        - GROWTH/NEUTRAL: 50% hedge
        - CRISIS/TRENDING: 0% hedge (let the gold trade run)
        """
        # Regime scaling
        regime_upper = regime.upper()
        if regime_upper in ["CRISIS", "TRENDING"]:
            scale = 0.0
        elif regime_upper in ["GROWTH", "NEUTRAL"]:
            scale = 0.5
        else:
            scale = 1.0
            
        final_beta = raw_beta * scale
        
        logger.debug(f"Kalman Hedge: raw_β={raw_beta:.3f} | regime={regime} | scale={scale:.1f}x | final_β={final_beta:.3f}")
        return gold_size * final_beta
