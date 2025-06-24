"""
Machine Learning module - Lorentzian Classification
"""

from .lorentzian_knn_fixed_corrected import LorentzianKNNFixedCorrected
# Alias for backward compatibility
LorentzianKNN = LorentzianKNNFixedCorrected
LorentzianKNNFixed = LorentzianKNNFixedCorrected

__all__ = ['LorentzianKNN', 'LorentzianKNNFixed', 'LorentzianKNNFixedCorrected']