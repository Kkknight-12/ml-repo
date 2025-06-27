"""
ML Quality Filter - Filters signals based on ML prediction strength
===================================================================

Only allows high-confidence trades and tracks ML accuracy
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import json
import os


@dataclass
class MLSignal:
    """Container for ML signal with quality metrics"""
    timestamp: pd.Timestamp
    signal: int  # 1 for long, -1 for short
    ml_prediction: float
    confidence_score: float
    filters_passed: Dict[str, bool]
    features: Dict[str, float]
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if this is a high confidence signal"""
        return abs(self.ml_prediction) >= 5
    
    @property
    def is_valid_entry(self) -> bool:
        """Check if this signal qualifies for entry"""
        return abs(self.ml_prediction) >= 3 and self.signal != 0
    
    @property
    def position_size_multiplier(self) -> float:
        """
        Get position size multiplier based on ML strength
        Higher confidence = larger position
        """
        abs_pred = abs(self.ml_prediction)
        
        if abs_pred >= 7:
            return 1.5  # 150% position
        elif abs_pred >= 5:
            return 1.0  # 100% position
        elif abs_pred >= 3:
            return 0.5  # 50% position
        else:
            return 0.0  # No position


class MLQualityFilter:
    """
    Filters and tracks ML signal quality
    """
    
    def __init__(self, min_confidence: float = 3.0,
                 high_confidence: float = 5.0,
                 track_accuracy: bool = True):
        """
        Initialize ML quality filter
        
        Args:
            min_confidence: Minimum ML prediction for entry consideration
            high_confidence: ML prediction for full position size
            track_accuracy: Whether to track ML prediction accuracy
        """
        self.min_confidence = min_confidence
        self.high_confidence = high_confidence
        self.track_accuracy = track_accuracy
        
        # Accuracy tracking
        self.accuracy_tracker = defaultdict(lambda: {
            'total_signals': 0,
            'correct_predictions': 0,
            'ml_buckets': defaultdict(lambda: {'total': 0, 'correct': 0})
        })
        
        # Load saved accuracy data if exists
        self.accuracy_file = 'ml_accuracy_data.json'
        self._load_accuracy_data()
    
    def filter_signal(self, signal: Dict, symbol: str = None) -> Optional[MLSignal]:
        """
        Filter and enhance ML signal
        
        Args:
            signal: Raw signal from bar processor
            symbol: Stock symbol for tracking
            
        Returns:
            MLSignal object if passes filter, None otherwise
        """
        # Extract components
        ml_prediction = signal.get('prediction', 0)
        trading_signal = signal.get('signal', 0)
        
        # Check minimum confidence
        if abs(ml_prediction) < self.min_confidence:
            return None
        
        # Check for zero predictions (ML uncertainty)
        if ml_prediction == 0.0:
            return None
        
        # Create ML signal object
        ml_signal = MLSignal(
            timestamp=signal.get('timestamp', pd.Timestamp.now()),
            signal=trading_signal,
            ml_prediction=ml_prediction,
            confidence_score=self._calculate_confidence(ml_prediction, signal),
            filters_passed=signal.get('filter_states', {}),
            features=signal.get('features', {})
        )
        
        # Additional quality checks
        if not self._quality_check(ml_signal, symbol):
            return None
        
        return ml_signal
    
    def update_accuracy(self, symbol: str, ml_prediction: float, 
                       actual_outcome: float):
        """
        Update ML accuracy tracking
        
        Args:
            symbol: Stock symbol
            ml_prediction: Original ML prediction
            actual_outcome: Actual price movement (positive for profit)
        """
        if not self.track_accuracy:
            return
        
        # Determine if prediction was correct
        correct = False
        if ml_prediction > 0 and actual_outcome > 0:  # Long prediction, profit
            correct = True
        elif ml_prediction < 0 and actual_outcome < 0:  # Short prediction, profit
            correct = True
        
        # Update trackers
        tracker = self.accuracy_tracker[symbol]
        tracker['total_signals'] += 1
        if correct:
            tracker['correct_predictions'] += 1
        
        # Track by ML strength bucket
        bucket = int(abs(ml_prediction))
        tracker['ml_buckets'][bucket]['total'] += 1
        if correct:
            tracker['ml_buckets'][bucket]['correct'] += 1
        
        # Save periodically
        if tracker['total_signals'] % 10 == 0:
            self._save_accuracy_data()
    
    def get_accuracy_stats(self, symbol: str = None) -> Dict:
        """
        Get ML accuracy statistics
        
        Args:
            symbol: Specific symbol or None for all
            
        Returns:
            Dictionary of accuracy statistics
        """
        if symbol:
            tracker = self.accuracy_tracker[symbol]
            if tracker['total_signals'] == 0:
                return {'accuracy': 0, 'total_signals': 0}
            
            accuracy = tracker['correct_predictions'] / tracker['total_signals'] * 100
            
            # Accuracy by ML strength
            bucket_stats = {}
            for bucket, data in tracker['ml_buckets'].items():
                if data['total'] > 0:
                    bucket_stats[f'ml_{bucket}'] = {
                        'accuracy': data['correct'] / data['total'] * 100,
                        'count': data['total']
                    }
            
            return {
                'symbol': symbol,
                'overall_accuracy': accuracy,
                'total_signals': tracker['total_signals'],
                'bucket_stats': bucket_stats
            }
        else:
            # Aggregate stats
            all_stats = []
            for sym in self.accuracy_tracker:
                stats = self.get_accuracy_stats(sym)
                if stats['total_signals'] > 0:
                    all_stats.append(stats)
            
            return all_stats
    
    def get_confidence_threshold(self, symbol: str) -> float:
        """
        Get dynamic confidence threshold based on historical accuracy
        
        Adjusts threshold based on ML performance for the symbol
        """
        stats = self.get_accuracy_stats(symbol)
        
        if stats['total_signals'] < 50:
            # Not enough data, use default
            return self.min_confidence
        
        # Find the ML strength with best accuracy
        best_bucket = self.min_confidence
        best_accuracy = 0
        
        for bucket_name, bucket_data in stats.get('bucket_stats', {}).items():
            if bucket_data['count'] >= 10:  # Minimum sample size
                if bucket_data['accuracy'] > best_accuracy:
                    best_accuracy = bucket_data['accuracy']
                    best_bucket = int(bucket_name.split('_')[1])
        
        # Adjust threshold based on best performing bucket
        if best_accuracy > 60:  # Good accuracy
            return min(best_bucket, self.min_confidence)
        else:
            # Poor accuracy, be more selective
            return max(best_bucket, self.high_confidence)
    
    def _calculate_confidence(self, ml_prediction: float, signal: Dict) -> float:
        """
        Calculate overall confidence score
        
        Combines ML prediction strength with filter agreement
        """
        # Base confidence from ML
        ml_confidence = min(abs(ml_prediction) / 8.0, 1.0)  # Normalize to 0-1
        
        # Filter agreement bonus
        filters = signal.get('filter_states', {})
        active_filters = sum(1 for v in filters.values() if v)
        total_filters = len(filters) if filters else 1
        filter_confidence = active_filters / total_filters
        
        # Feature strength (if available)
        features = signal.get('features', {})
        feature_confidence = 0.5  # Default
        
        if features:
            # Check if features are aligned (all pointing same direction)
            feature_signs = [1 if v > 0 else -1 for v in features.values() if v != 0]
            if feature_signs:
                alignment = abs(sum(feature_signs)) / len(feature_signs)
                feature_confidence = alignment
        
        # Weighted combination
        confidence = (
            0.5 * ml_confidence +
            0.3 * filter_confidence +
            0.2 * feature_confidence
        )
        
        return confidence
    
    def _quality_check(self, ml_signal: MLSignal, symbol: str = None) -> bool:
        """
        Additional quality checks beyond ML strength
        """
        # Check if too many filters are failing
        filters_passed = sum(1 for v in ml_signal.filters_passed.values() if v)
        total_filters = len(ml_signal.filters_passed)
        
        if total_filters > 0 and filters_passed / total_filters < 0.5:
            # Less than 50% of filters passing
            return False
        
        # Check historical performance for this ML strength
        if symbol and self.track_accuracy:
            stats = self.get_accuracy_stats(symbol)
            bucket = int(abs(ml_signal.ml_prediction))
            
            bucket_stats = stats.get('bucket_stats', {}).get(f'ml_{bucket}', {})
            if bucket_stats.get('count', 0) >= 20:
                # We have enough data for this ML strength
                if bucket_stats.get('accuracy', 0) < 40:
                    # This ML strength has poor historical accuracy
                    return False
        
        return True
    
    def _load_accuracy_data(self):
        """Load saved accuracy data"""
        if os.path.exists(self.accuracy_file):
            try:
                with open(self.accuracy_file, 'r') as f:
                    data = json.load(f)
                    # Convert back to defaultdict structure
                    for symbol, tracker in data.items():
                        self.accuracy_tracker[symbol] = {
                            'total_signals': tracker.get('total_signals', 0),
                            'correct_predictions': tracker.get('correct_predictions', 0),
                            'ml_buckets': defaultdict(
                                lambda: {'total': 0, 'correct': 0},
                                tracker.get('ml_buckets', {})
                            )
                        }
            except Exception as e:
                print(f"Error loading accuracy data: {e}")
    
    def _save_accuracy_data(self):
        """Save accuracy data to file"""
        try:
            # Convert defaultdict to regular dict for JSON serialization
            data = {}
            for symbol, tracker in self.accuracy_tracker.items():
                data[symbol] = {
                    'total_signals': tracker['total_signals'],
                    'correct_predictions': tracker['correct_predictions'],
                    'ml_buckets': dict(tracker['ml_buckets'])
                }
            
            with open(self.accuracy_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving accuracy data: {e}")
    
    def get_signal_strength_distribution(self, signals: List[Dict]) -> pd.DataFrame:
        """
        Analyze distribution of ML signal strengths
        
        Useful for understanding signal quality patterns
        """
        ml_predictions = [s.get('prediction', 0) for s in signals]
        
        df = pd.DataFrame({
            'ml_prediction': ml_predictions,
            'abs_prediction': [abs(p) for p in ml_predictions]
        })
        
        # Group by strength buckets
        df['strength_bucket'] = pd.cut(
            df['abs_prediction'], 
            bins=[0, 1, 3, 5, 7, 9],
            labels=['0-1', '1-3', '3-5', '5-7', '7+']
        )
        
        # Calculate distribution
        distribution = df['strength_bucket'].value_counts(normalize=True).sort_index()
        
        return distribution