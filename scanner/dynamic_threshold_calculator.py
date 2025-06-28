"""
Dynamic ML Threshold Calculator
===============================

Calculates optimal ML threshold based on historical prediction distribution
during warmup period and updates it as new data comes in.
"""

import numpy as np
from typing import List, Tuple, Optional
from collections import deque


class DynamicThresholdCalculator:
    """
    Calculates dynamic ML threshold based on prediction distribution
    """
    
    def __init__(self, lookback_period: int = 500, percentile: float = 85.0):
        """
        Initialize dynamic threshold calculator
        
        Args:
            lookback_period: Number of predictions to consider
            percentile: Percentile for threshold (75 = top 25% of signals)
        """
        self.lookback_period = lookback_period
        self.percentile = percentile
        
        # Store predictions for analysis
        self.predictions = deque(maxlen=lookback_period)
        self.winning_predictions = deque(maxlen=lookback_period)
        self.losing_predictions = deque(maxlen=lookback_period)
        
        # Threshold tracking
        self.current_threshold = 3.0  # Default fallback
        self.threshold_history = []
        
        # Statistics
        self.updates = 0
        self.min_samples = 100  # Minimum samples before calculating
        
    def add_prediction(self, prediction: float, was_profitable: Optional[bool] = None):
        """
        Add a new prediction to the calculator
        
        Args:
            prediction: ML prediction value
            was_profitable: Whether this prediction led to profit (if known)
        """
        self.predictions.append(abs(prediction))
        
        if was_profitable is not None:
            if was_profitable:
                self.winning_predictions.append(abs(prediction))
            else:
                self.losing_predictions.append(abs(prediction))
    
    def calculate_threshold(self) -> float:
        """
        Calculate optimal threshold based on prediction distribution
        
        Returns:
            Calculated threshold value
        """
        if len(self.predictions) < self.min_samples:
            return self.current_threshold
        
        # Method 1: Percentile-based (simple and robust)
        threshold_percentile = np.percentile(list(self.predictions), self.percentile)
        
        # Method 2: Statistical-based (mean + std)
        predictions_array = np.array(list(self.predictions))
        mean_pred = np.mean(predictions_array)
        std_pred = np.std(predictions_array)
        threshold_statistical = mean_pred + std_pred
        
        # Method 3: Profitability-based (if we have win/loss data)
        threshold_profit = self.current_threshold
        if len(self.winning_predictions) > 20 and len(self.losing_predictions) > 20:
            # Find threshold that maximizes win rate
            win_array = np.array(list(self.winning_predictions))
            lose_array = np.array(list(self.losing_predictions))
            
            # Find point where win rate is highest
            thresholds_to_test = np.linspace(0, 10, 50)
            best_score = -1
            best_threshold = self.current_threshold
            
            for t in thresholds_to_test:
                wins_above = np.sum(win_array >= t)
                losses_above = np.sum(lose_array >= t)
                total_above = wins_above + losses_above
                
                if total_above > 10:  # Minimum trades
                    win_rate = wins_above / total_above
                    score = win_rate * np.sqrt(total_above)  # Balance win rate and sample size
                    
                    if score > best_score:
                        best_score = score
                        best_threshold = t
            
            threshold_profit = best_threshold
        
        # Combine methods with weights
        if len(self.winning_predictions) > 20:
            # If we have profitability data, weight it more
            self.current_threshold = (
                0.3 * threshold_percentile +
                0.2 * threshold_statistical +
                0.5 * threshold_profit
            )
        else:
            # Otherwise use statistical methods
            self.current_threshold = (
                0.6 * threshold_percentile +
                0.4 * threshold_statistical
            )
        
        # Apply bounds to prevent extreme values
        # Minimum of 2.5 to ensure quality signals
        self.current_threshold = np.clip(self.current_threshold, 2.5, 5.0)
        
        # Smooth changes to prevent jumps
        if self.threshold_history:
            last_threshold = self.threshold_history[-1]
            max_change = 0.5  # Maximum change per update
            if abs(self.current_threshold - last_threshold) > max_change:
                if self.current_threshold > last_threshold:
                    self.current_threshold = last_threshold + max_change
                else:
                    self.current_threshold = last_threshold - max_change
        
        self.threshold_history.append(self.current_threshold)
        self.updates += 1
        
        return self.current_threshold
    
    def get_adaptive_threshold(self, volatility: Optional[float] = None) -> float:
        """
        Get threshold adapted to current market conditions
        
        Args:
            volatility: Current market volatility (optional)
            
        Returns:
            Adapted threshold
        """
        base_threshold = self.calculate_threshold()
        
        # Adjust for volatility if provided
        if volatility is not None:
            if volatility > 2.0:  # High volatility
                # Be more selective in volatile markets
                return base_threshold * 1.2
            elif volatility < 0.5:  # Low volatility  
                # Can be less selective in calm markets
                return base_threshold * 0.8
        
        return base_threshold
    
    def get_statistics(self) -> dict:
        """
        Get calculator statistics
        
        Returns:
            Dictionary with statistics
        """
        predictions_array = np.array(list(self.predictions)) if self.predictions else np.array([])
        
        stats = {
            'current_threshold': self.current_threshold,
            'total_predictions': len(self.predictions),
            'winning_predictions': len(self.winning_predictions),
            'losing_predictions': len(self.losing_predictions),
            'updates': self.updates,
            'avg_prediction': np.mean(predictions_array) if len(predictions_array) > 0 else 0,
            'std_prediction': np.std(predictions_array) if len(predictions_array) > 0 else 0,
            'percentile_threshold': np.percentile(predictions_array, self.percentile) if len(predictions_array) > 0 else 0
        }
        
        if len(self.winning_predictions) > 0 and len(self.losing_predictions) > 0:
            win_array = np.array(list(self.winning_predictions))
            lose_array = np.array(list(self.losing_predictions))
            stats['avg_winning_prediction'] = np.mean(win_array)
            stats['avg_losing_prediction'] = np.mean(lose_array)
            
            # Calculate win rate at current threshold
            wins_above = np.sum(win_array >= self.current_threshold)
            losses_above = np.sum(lose_array >= self.current_threshold)
            total_above = wins_above + losses_above
            stats['win_rate_at_threshold'] = wins_above / total_above if total_above > 0 else 0
            stats['signals_above_threshold'] = total_above
        
        return stats
    
    def reset(self):
        """Reset calculator to initial state"""
        self.predictions.clear()
        self.winning_predictions.clear()
        self.losing_predictions.clear()
        self.current_threshold = 3.0
        self.threshold_history = []
        self.updates = 0


def calculate_optimal_threshold_from_warmup(predictions: List[float], 
                                          outcomes: Optional[List[bool]] = None,
                                          method: str = 'percentile') -> float:
    """
    Calculate optimal threshold from warmup period data
    
    Args:
        predictions: List of ML predictions from warmup
        outcomes: List of trade outcomes (profitable or not)
        method: 'percentile', 'statistical', or 'adaptive'
        
    Returns:
        Optimal threshold value
    """
    predictions = np.array([abs(p) for p in predictions])
    
    if method == 'percentile':
        # Use 75th percentile - only top 25% of signals
        return np.percentile(predictions, 75)
    
    elif method == 'statistical':
        # Mean + 1 standard deviation
        return np.mean(predictions) + np.std(predictions)
    
    elif method == 'adaptive' and outcomes is not None:
        # Find threshold that maximizes profitability
        thresholds = np.linspace(0, np.max(predictions), 100)
        best_threshold = 3.0
        best_score = -1
        
        for threshold in thresholds:
            mask = predictions >= threshold
            if np.sum(mask) < 10:  # Need minimum trades
                continue
                
            win_rate = np.sum(np.array(outcomes)[mask]) / np.sum(mask)
            num_trades = np.sum(mask)
            
            # Score combines win rate and number of trades
            score = win_rate * np.sqrt(num_trades)
            
            if score > best_score:
                best_score = score
                best_threshold = threshold
        
        return best_threshold
    
    else:
        # Default to percentile method
        return np.percentile(predictions, 75)