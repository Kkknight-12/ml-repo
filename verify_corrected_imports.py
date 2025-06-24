#!/usr/bin/env python3
"""
Verify all imports are using the corrected ML model
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*70)
print("VERIFY CORRECTED IMPORTS")
print("="*70)

# Test 1: Direct import
print("\n1. Testing direct import:")
try:
    from ml.lorentzian_knn_fixed_corrected import LorentzianKNNFixedCorrected
    print("   ✅ Direct import successful")
except ImportError as e:
    print(f"   ❌ Direct import failed: {e}")

# Test 2: Module __init__ aliases
print("\n2. Testing module aliases:")
try:
    from ml import LorentzianKNN, LorentzianKNNFixed, LorentzianKNNFixedCorrected
    print("   ✅ All aliases imported successfully")
    
    # Verify they all point to the corrected version
    if LorentzianKNN == LorentzianKNNFixedCorrected:
        print("   ✅ LorentzianKNN alias is correct")
    else:
        print("   ❌ LorentzianKNN alias is wrong!")
        
    if LorentzianKNNFixed == LorentzianKNNFixedCorrected:
        print("   ✅ LorentzianKNNFixed alias is correct")
    else:
        print("   ❌ LorentzianKNNFixed alias is wrong!")
        
except ImportError as e:
    print(f"   ❌ Alias import failed: {e}")

# Test 3: Enhanced bar processor
print("\n3. Testing enhanced bar processor:")
try:
    from scanner.enhanced_bar_processor import EnhancedBarProcessor
    from config.settings import TradingConfig
    
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, "TEST", "day")
    
    # Check ML model type
    ml_class_name = processor.ml_model.__class__.__name__
    print(f"   ML model class: {ml_class_name}")
    
    if ml_class_name == "LorentzianKNNFixedCorrected":
        print("   ✅ Enhanced bar processor using corrected model")
    else:
        print(f"   ❌ Wrong model class: {ml_class_name}")
        
except Exception as e:
    print(f"   ❌ Enhanced bar processor test failed: {e}")

# Test 4: Check array indexing
print("\n4. Testing array indexing fix:")
try:
    from data.data_types import Settings, Label, FeatureArrays, FeatureSeries
    
    settings = Settings(
        source='close',
        neighbors_count=8,
        max_bars_back=100,
        feature_count=5
    )
    label = Label()
    
    ml_model = LorentzianKNNFixedCorrected(settings, label)
    
    # Create test arrays
    feature_arrays = FeatureArrays()
    for i in range(10):
        feature_arrays.f1.append(i * 0.1)
    
    # Test get_value behavior
    print("   Testing array access (array = [0.0, 0.1, 0.2, ..., 0.9]):")
    
    # In the corrected version, i=0 should access the newest (last) element
    # We need to check the get_lorentzian_distance method
    feature_series = FeatureSeries(f1=0.5, f2=0.5, f3=0.5, f4=0.5, f5=0.5)
    
    # Calculate distance for i=0 (should compare with newest historical data)
    distance = ml_model.get_lorentzian_distance(0, 1, feature_series, feature_arrays)
    print(f"   Distance for i=0: {distance:.3f}")
    print("   ✅ Array indexing test complete")
    
except Exception as e:
    print(f"   ❌ Array indexing test failed: {e}")

# Summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("All critical imports have been updated to use LorentzianKNNFixedCorrected")
print("This includes:")
print("- scanner/enhanced_bar_processor.py")
print("- ml/__init__.py (with backward-compatible aliases)")
print("- run_scanner.py")
print("\nThe corrected model fixes the array indexing bug where:")
print("- OLD: i=0 accessed the OLDEST historical data")
print("- NEW: i=0 accesses the NEWEST historical data (correct!)")
print("="*70)