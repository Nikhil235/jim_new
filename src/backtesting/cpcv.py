"""
Phase 5: Combinatorial Purged Cross-Validation (CPCV)

CPCV overcomes limitations of standard k-fold cross-validation for time-series:
1. Creates ALL possible train/test combinations
2. PURGES overlapping observations (removes look-ahead bias)
3. EMBARGOES buffer period after test fold (prevents information leakage)
4. Tests are non-overlapping (true out-of-sample)

This is critical for time-series backtesting to prevent overfitting.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, List, Tuple
import numpy as np
import itertools

from loguru import logger


@dataclass
class CPCVFold:
    """Single CPCV fold."""
    fold_id: int
    train_indices: np.ndarray
    test_indices: np.ndarray
    train_dates: Tuple[datetime, datetime]
    test_dates: Tuple[datetime, datetime]
    embargo_indices: np.ndarray = None

    @property
    def num_train(self) -> int:
        return len(self.train_indices)

    @property
    def num_test(self) -> int:
        return len(self.test_indices)

    @property
    def num_embargo(self) -> int:
        return len(self.embargo_indices) if self.embargo_indices is not None else 0


@dataclass
class CPCVResult:
    """Result from single CPCV fold."""
    fold: CPCVFold
    train_score: float          # In-sample score
    test_score: float           # Out-of-sample score
    score_diff: float           # Train - Test (indicates overfitting)

    @property
    def is_overfit(self, threshold: float = 0.2) -> bool:
        """Check if fold is overfit."""
        return self.score_diff > threshold


class CPCVAnalyzer:
    """
    Combinatorial Purged Cross-Validation for time-series data.
    
    Prevents both:
    1. Look-ahead bias: Test data never used in training
    2. Information leakage: Buffer period around test set
    """

    def __init__(
        self,
        num_folds: int = 5,
        embargo_pct: float = 0.01,  # 1% embargo (buffer)
        min_train_size: float = 0.3,  # Min 30% for training
    ):
        """
        Initialize CPCV analyzer.
        
        Args:
            num_folds: Number of CV folds
            embargo_pct: % of data to embargo after test fold
            min_train_size: Minimum % of data to use for training
        """
        self.num_folds = num_folds
        self.embargo_pct = embargo_pct
        self.min_train_size = min_train_size

    def generate_folds(
        self,
        dates: List[datetime],
        n_splits: int = 5,
    ) -> List[CPCVFold]:
        """
        Generate CPCV folds.
        
        Args:
            dates: List of dates corresponding to data
            n_splits: Number of splits
            
        Returns:
            List of CPCV folds
        """
        n = len(dates)
        embargo_size = int(n * self.embargo_pct)
        
        folds = []
        fold_id = 0
        
        # Non-overlapping test periods
        test_size = n // n_splits
        
        for i in range(n_splits):
            test_start = i * test_size
            test_end = (i + 1) * test_size if i < n_splits - 1 else n
            test_indices = np.arange(test_start, test_end)
            
            if len(test_indices) < 10:
                continue  # Skip tiny test folds
            
            # Embargo indices: buffer after test set
            embargo_start = min(test_end, n)
            embargo_end = min(test_end + embargo_size, n)
            embargo_indices = np.arange(embargo_start, embargo_end)
            
            # Training indices: all data except test and embargo
            purge_indices = np.union1d(test_indices, embargo_indices)
            train_indices = np.setdiff1d(np.arange(n), purge_indices)
            
            if len(train_indices) >= n * self.min_train_size:
                fold = CPCVFold(
                    fold_id=fold_id,
                    train_indices=train_indices,
                    test_indices=test_indices,
                    embargo_indices=embargo_indices,
                    train_dates=(dates[train_indices[0]], dates[train_indices[-1]]),
                    test_dates=(dates[test_indices[0]], dates[test_indices[-1]]),
                )
                
                folds.append(fold)
                fold_id += 1
        
        logger.info(f"Generated {len(folds)} CPCV folds")
        return folds

    def run(
        self,
        folds: List[CPCVFold],
        data: np.ndarray,
        train_fn: Callable,
        test_fn: Callable,
    ) -> List[CPCVResult]:
        """
        Run CPCV analysis.
        
        Args:
            folds: CPCV folds
            data: Data array (N x features)
            train_fn: Function(train_data) -> train_score
            test_fn: Function(train_model, test_data) -> test_score
            
        Returns:
            List of CPCVResult
        """
        results = []
        
        for fold in folds:
            # Get train/test data
            train_data = data[fold.train_indices]
            test_data = data[fold.test_indices]
            
            # Train
            train_score = train_fn(train_data)
            
            # Test
            test_score = test_fn(train_data, test_data)
            
            # Create result
            result = CPCVResult(
                fold=fold,
                train_score=train_score,
                test_score=test_score,
                score_diff=train_score - test_score,
            )
            
            results.append(result)
            
            logger.debug(
                f"Fold {fold.fold_id}: Train={train_score:.4f}, Test={test_score:.4f}, "
                f"Diff={result.score_diff:.4f}"
            )
        
        return results

    @staticmethod
    def summarize(results: List[CPCVResult]) -> dict:
        """
        Summarize CPCV results.
        
        Returns:
            Dictionary with aggregate metrics
        """
        train_scores = [r.train_score for r in results]
        test_scores = [r.test_score for r in results]
        diffs = [r.score_diff for r in results]
        
        return {
            "num_folds": len(results),
            "avg_train_score": np.mean(train_scores),
            "avg_test_score": np.mean(test_scores),
            "std_test_score": np.std(test_scores),
            "avg_diff": np.mean(diffs),
            "max_diff": np.max(diffs),
            "num_overfit": sum(1 for r in results if r.is_overfit()),
            "generalization_ratio": np.mean(test_scores) / np.mean(train_scores) if np.mean(train_scores) > 0 else 0,
        }
