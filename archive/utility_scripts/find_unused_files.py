#!/usr/bin/env python3
"""
Find unused Python files in the project
"""
import os
import re
from pathlib import Path

# Root directory
root_dir = Path(__file__).parent

# Core modules that are part of the main implementation
core_modules = {
    # Config
    'config/__init__.py',
    'config/settings.py',
    'config/constants.py',
    
    # Core functionality
    'core/__init__.py',
    'core/enhanced_indicators.py',
    'core/enhanced_ml_extensions.py',
    'core/stateful_ta.py',
    'core/indicator_state_manager.py',
    'core/kernel_functions.py',
    'core/pine_functions.py',
    'core/na_handling.py',
    'core/normalization.py',
    'core/history_referencing.py',
    'core/regime_filter_fix_v2.py',
    'core/math_helpers.py',
    
    # ML
    'ml/__init__.py',
    'ml/lorentzian_knn_fixed.py',
    
    # Scanner
    'scanner/__init__.py',
    'scanner/enhanced_bar_processor.py',
    'scanner/enhanced_bar_processor_debug.py',
    'scanner/signal_generator.py',
    'scanner/bar_processor.py',  # Base class
    
    # Data
    'data/__init__.py',
    'data/data_types.py',
    'data/bar_data.py',
    'data/zerodha_client.py',
    
    # Utils
    'utils/__init__.py',
    'utils/risk_management.py',
    
    # Key test files
    'test_comprehensive_fix_verification.py',
    'test_zerodha_comprehensive.py',
    'auth_helper.py',  # For Zerodha auth
    'run_scanner.py',  # Main scanner entry
}

# Old/deprecated modules (candidates for archiving)
deprecated_modules = {
    # Old implementations
    'ml/lorentzian_knn.py',  # Replaced by lorentzian_knn_fixed.py
    'ml/lorentzian_knn_debug.py',  # Debug version
    'core/indicators.py',  # Replaced by enhanced_indicators.py
    'core/ml_extensions.py',  # Replaced by enhanced_ml_extensions.py
    'core/regime_filter_fix.py',  # Replaced by regime_filter_fix_v2.py
    'data/enhanced_bar_data.py',  # Not used
    'data/data_manager.py',  # Not used
    'scanner/live_scanner.py',  # Not implemented
    'utils/notifications.py',  # Not implemented
    'utils/sample_data.py',  # Test data generation
    'utils/compatibility.py',  # Not used
}

# Test and debug files (many are one-off tests)
test_debug_files = set()
demo_files = set()
comparison_files = set()
validation_files = set()
phase_files = set()

# Scan all Python files
all_py_files = set()
for py_file in root_dir.glob('**/*.py'):
    if '__pycache__' not in str(py_file) and '.git' not in str(py_file):
        rel_path = str(py_file.relative_to(root_dir))
        all_py_files.add(rel_path)
        
        # Categorize files
        if rel_path.startswith('test_') or '_test' in rel_path:
            test_debug_files.add(rel_path)
        elif rel_path.startswith('debug_') or '_debug' in rel_path:
            test_debug_files.add(rel_path)
        elif rel_path.startswith('demo/'):
            demo_files.add(rel_path)
        elif 'compare' in rel_path or 'comparison' in rel_path:
            comparison_files.add(rel_path)
        elif rel_path.startswith('validate_') or 'validation' in rel_path:
            validation_files.add(rel_path)
        elif rel_path.startswith('phase_') or 'phase' in rel_path.lower():
            phase_files.add(rel_path)

# Files already in archive
already_archived = {f for f in all_py_files if f.startswith('archive_')}

# Calculate unused files
unused_files = all_py_files - core_modules - already_archived

# Print results
print("=" * 80)
print("FILE USAGE ANALYSIS")
print("=" * 80)

print(f"\n📊 STATISTICS:")
print(f"Total Python files: {len(all_py_files)}")
print(f"Core modules: {len(core_modules)}")
print(f"Already archived: {len(already_archived)}")
print(f"Potentially unused: {len(unused_files)}")

print(f"\n🗂️ DEPRECATED MODULES (should be archived):")
for f in sorted(deprecated_modules):
    if f in all_py_files:
        print(f"  - {f}")

print(f"\n🧪 TEST/DEBUG FILES: {len(test_debug_files)}")
print("  (One-off test files that can be archived)")
# Show first 10
for f in sorted(test_debug_files)[:10]:
    print(f"  - {f}")
print(f"  ... and {len(test_debug_files) - 10} more")

print(f"\n📊 COMPARISON FILES: {len(comparison_files)}")
for f in sorted(comparison_files):
    print(f"  - {f}")

print(f"\n✅ VALIDATION FILES: {len(validation_files)}")
for f in sorted(validation_files):
    print(f"  - {f}")

print(f"\n📝 PHASE FILES: {len(phase_files)}")
for f in sorted(phase_files):
    print(f"  - {f}")

print(f"\n🎯 DEMO FILES: {len(demo_files)}")
for f in sorted(demo_files):
    print(f"  - {f}")

# Other misc files
misc_files = unused_files - deprecated_modules - test_debug_files - demo_files - comparison_files - validation_files - phase_files
print(f"\n📌 OTHER MISC FILES: {len(misc_files)}")
for f in sorted(misc_files):
    if not f.endswith('find_unused_files.py'):
        print(f"  - {f}")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)
print("1. Archive deprecated modules first")
print("2. Archive old test/debug files")
print("3. Keep only essential test files (test_comprehensive_fix_verification.py, test_zerodha_comprehensive.py)")
print("4. Archive comparison/validation/phase files")
print("5. Review misc files individually")