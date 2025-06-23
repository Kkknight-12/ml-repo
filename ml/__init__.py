"""
Machine Learning module - Lorentzian Classification
"""

from .lorentzian_knn_fixed import LorentzianKNNFixed
# Alias for backward compatibility
LorentzianKNN = LorentzianKNNFixed

__all__ = ['LorentzianKNN', 'LorentzianKNNFixed']