"""
Integration Tests: Phase 4 Position Lifecycle
==============================================
Tests complete workflow: Signal → Critic → Kelly → Risk → VaR → Execute → Monitor → Exit
"""

import pytest
import numpy as np
from src.risk.meta_labeler import MetaLabeler, TraderSignal, CriticInput
from src.risk.gpu_var import GPUVaRCalculator
from src.risk.position_manager import PositionManager
from src.risk.manager import RiskManager


class TestPositionLifecycleIntegration:
    """Integration tests for full position lifecycle."""

    @pytest.fixture
    def setup(self):
        """Setup all components."""
        config = {
            "risk": {
                "kelly": {"fraction": 0.5, "max_position_pct": 0.05},
                "circuit_breakers": {
                    "daily_loss_limit": 0.02,
                    "drawdown_reduce": 0.05,
                    "drawdown_stop": 0.10,
                },
            },
            "position_manager": {
                "max_positions": 5,
                "trailing_stop_pct": 0.02,
                "profit_target_pct": 0.05,
                "time_stop_hours": 24,
            },
        }
        
        return {
            "critic": MetaLabeler(threshold=0.65),
            "var_calc": GPUVaRCalculator(use_gpu=False),
            "position_mgr": PositionManager(config),
            "risk_mgr": RiskManager(config),
            "portfolio_value": 100000,
            "current_price": 2000,
        }

    def test_workflow_signal_to_execution(self, setup):
        """Test complete workflow from signal to execution."""
        c = setup["critic"]
        pm = setup["position_mgr"]
        rm = setup["risk_mgr"]
        portfolio = setup["portfolio_value"]
        price = setup["current_price"]
        
        # Step 1: Create a trader signal
        trader_signal = TraderSignal(
            direction=1,
            confidence=0.75,
            raw_scores={"ensemble": 0.75},
        )
        
        # Step 2: Prepare critic input
        critic_input = CriticInput(
            trader_signal=1,
            trader_confidence=0.75,
            trader_raw_scores=np.array([0.75]),
            current_regime="NORMAL",
            regime_probability=0.85,
            volatility=1.0,
            spread_pct=0.0015,
            hour_of_day=10,
            day_of_week=2,
            trader_recent_accuracy=0.55,
            trader_recent_profit_factor=1.2,
            regime_in_sample_accuracy=0.58,
            liquidity_score=0.8,
        )
        
        # Step 3: Critic evaluation
        execute, critic_conf = c.should_trade(trader_signal, critic_input)
        assert execute == True
        assert critic_conf > 0
        
        # Step 4: Kelly sizing
        win_prob = critic_conf
        avg_win = 100
        avg_loss = 100
        kelly_size = rm.calculate_kelly_size(win_prob, avg_win, avg_loss, portfolio)
        assert kelly_size > 0
        assert kelly_size <= portfolio * 0.05  # Max 5%
        
        # Step 5: Risk checks
        can_trade, reason = rm.check_circuit_breakers(portfolio)
        assert can_trade == True
        
        # Step 6: VaR check
        var_result = setup["var_calc"].monte_carlo_var(
            current_position=kelly_size / price,
            current_price=price,
            returns_mean=0.0005,
            returns_std=0.02,
            n_scenarios=10000,
        )
        assert var_result.var_95 > 0
        
        # Step 7: Position execution
        signal = pm.open_position(
            direction=trader_signal.direction,
            size=kelly_size / price,
            entry_price=price,
            trader_confidence=trader_signal.confidence,
            critic_confidence=critic_conf,
            kelly_fraction=kelly_size / portfolio,
            reason=f"Signal from ensemble + Critic approval ({critic_conf:.2%})",
        )
        
        assert signal.approved == True
        assert len(pm.positions) == 1

    def test_multiple_signals_workflow(self, setup):
        """Test handling multiple signals."""
        c = setup["critic"]
        pm = setup["position_mgr"]
        rm = setup["risk_mgr"]
        portfolio = setup["portfolio_value"]
        price = setup["current_price"]
        
        # Execute 3 different signals
        signals_data = [
            (1, 0.75),   # Long, high confidence
            (1, 0.70),   # Long, medium confidence
            (-1, 0.65),  # Short, threshold confidence
        ]
        
        for direction, confidence in signals_data:
            trader_signal = TraderSignal(
                direction=direction,
                confidence=confidence,
                raw_scores={"ensemble": confidence},
            )
            
            critic_input = CriticInput(
                trader_signal=direction,
                trader_confidence=confidence,
                trader_raw_scores=np.array([confidence]),
                current_regime="NORMAL",
                regime_probability=0.85,
                volatility=1.0,
                spread_pct=0.0015,
                hour_of_day=10 + len(pm.positions),
                day_of_week=2,
                trader_recent_accuracy=0.55,
                trader_recent_profit_factor=1.2,
                regime_in_sample_accuracy=0.58,
                liquidity_score=0.8,
            )
            
            execute, critic_conf = c.should_trade(trader_signal, critic_input)
            
            if execute:
                kelly_size = rm.calculate_kelly_size(
                    critic_conf, 100, 100, portfolio
                )
                
                signal = pm.open_position(
                    direction=direction,
                    size=kelly_size / price,
                    entry_price=price,
                    trader_confidence=confidence,
                    critic_confidence=critic_conf,
                    kelly_fraction=kelly_size / portfolio,
                )
                
                assert signal.approved == True
        
        assert len(pm.positions) >= 2

    def test_position_monitoring_and_exit(self, setup):
        """Test position monitoring through various exit conditions."""
        pm = setup["position_mgr"]
        price = setup["current_price"]
        
        # Open a position
        signal = pm.open_position(
            direction=1,
            size=50,
            entry_price=price,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        pos_id = signal.position_id
        
        # Monitor: Price moves up
        pm.update_position(pos_id, price + 10)
        pos = pm.positions[0]
        assert pos.pnl > 0
        
        # Monitor: Price moves up more
        pm.update_position(pos_id, price + 50)
        assert pos.max_profit > 0
        
        # Monitor: Price pulls back
        pm.update_position(pos_id, price + 30)
        
        # Check if trailing stop would trigger
        # With 2% trailing stop on $50 profit: stop at 2030 * 0.98 = 1989.4
        # Current price at 2030, so no stop yet
        
        # Exit: Manual close at profit
        closed = pm.close_position(pos_id, price + 40, reason="Manual exit")
        
        assert closed is not None
        assert closed.pnl > 0
        assert closed.status == "CLOSED"

    def test_crisis_regime_position_sizing(self, setup):
        """Test reduced sizing in crisis regime."""
        rm = setup["risk_mgr"]
        portfolio = setup["portfolio_value"]
        
        # NORMAL regime
        kelly_normal = rm.calculate_kelly_size(
            win_prob=0.55,
            avg_win=100,
            avg_loss=100,
            portfolio_value=portfolio,
            regime="NORMAL",
        )
        
        # CRISIS regime (should be <= half)
        kelly_crisis = rm.calculate_kelly_size(
            win_prob=0.55,
            avg_win=100,
            avg_loss=100,
            portfolio_value=portfolio,
            regime="CRISIS",
        )
        
        assert kelly_crisis <= kelly_normal
        # Allow small tolerance for floating-point precision
        assert kelly_crisis / kelly_normal <= 0.5 + 1e-9

    def test_circuit_breaker_halts_trading(self, setup):
        """Test circuit breaker stops trading."""
        rm = setup["risk_mgr"]
        portfolio = setup["portfolio_value"]
        
        # Simulate daily loss
        rm.risk_state.daily_pnl = -portfolio * 0.03  # 3% loss
        
        # Check circuit breaker
        can_trade, reason = rm.check_circuit_breakers(portfolio)
        
        assert can_trade == False
        assert rm.risk_state.is_halted == True

    def test_consecutive_loss_tracking(self, setup):
        """Test consecutive loss tracking affects Kelly sizing."""
        rm = setup["risk_mgr"]
        portfolio = setup["portfolio_value"]
        
        # Record 3 consecutive losses
        for _ in range(3):
            rm.record_trade(pnl=-100)
        
        # Kelly sizing should be reduced
        kelly_reduced = rm.calculate_kelly_size(
            win_prob=0.55,
            avg_win=100,
            avg_loss=100,
            portfolio_value=portfolio,
        )
        
        # Reset and get unreduced sizing
        rm.risk_state.consecutive_losses = 0
        kelly_normal = rm.calculate_kelly_size(
            win_prob=0.55,
            avg_win=100,
            avg_loss=100,
            portfolio_value=portfolio,
        )
        
        assert kelly_reduced <= kelly_normal

    def test_var_constrains_position_size(self, setup):
        """Test that VaR limits inform position sizing."""
        var_calc = setup["var_calc"]
        portfolio = setup["portfolio_value"]
        price = setup["current_price"]
        
        # Small position
        result_small = var_calc.monte_carlo_var(
            current_position=10,
            current_price=price,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=10000,
        )
        
        # Large position
        result_large = var_calc.monte_carlo_var(
            current_position=100,
            current_price=price,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=10000,
        )
        
        # Larger position has larger VaR
        assert result_large.var_95 > result_small.var_95

    def test_profit_target_exit(self, setup):
        """Test profit target causes position exit."""
        pm = setup["position_mgr"]
        price = setup["current_price"]
        
        signal = pm.open_position(
            direction=1,
            size=100,
            entry_price=price,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        pos_id = signal.position_id
        target = price * (1 + pm.profit_target_pct)
        
        # Update to target price
        exit_cond = pm.update_position(pos_id, target)
        
        assert exit_cond is not None
        assert exit_cond[0] == "profit_target_hit"

    def test_rolling_statistics_update(self, setup):
        """Test rolling statistics track performance."""
        rm = setup["risk_mgr"]
        
        # Simulate trades
        trades = [100, -50, 150, -30, 200]
        
        for pnl in trades:
            rm.record_trade(pnl)
        
        stats = rm.get_rolling_stats()
        
        assert stats["trade_count"] == 5
        assert stats["win_rate"] == 0.6  # 3 wins, 2 losses
        assert stats["avg_win"] > 0
        assert stats["avg_loss"] > 0
        assert stats["profit_factor"] > 1
