#!/usr/bin/env python3
"""
Organize unused files into archive folders
"""
import os
import shutil
from pathlib import Path

# Define what to archive
TO_ARCHIVE = {
    'archive/deprecated_modules': [
        'core/indicators.py',
        'core/ml_extensions.py', 
        'core/regime_filter_fix.py',
        'data/data_manager.py',
        'data/enhanced_bar_data.py',
        'ml/lorentzian_knn.py',
        'ml/lorentzian_knn_debug.py',
        'scanner/live_scanner.py',
        'utils/compatibility.py',
        'utils/notifications.py',
        'utils/sample_data.py',
    ],
    
    'archive/test_debug_files': [
        # Debug files
        'debug_enhanced_filters.py',
        'debug_filter_tracking.py',
        'debug_filter_tracking_minimal.py',
        'debug_filters_comprehensive.py',
        'debug_find_instrument.py',
        'debug_ml_internals.py',
        'debug_ml_predictions.py',
        'debug_ml_with_filters.py',
        'debug_ml_zero.py',
        'debug_regime_filter.py',
        'debug_regime_zerodha.py',
        'debug_signal_transitions.py',
        'debug_signals_detailed.py',
        'comprehensive_ml_debug.py',
        'component_testing.py',
        'quick_filter_test.py',
        'quick_ml_test.py',
        'regime_debug_internal.py',
        
        # Old test files
        'test_adx_filter.py',
        'test_adx_pine_comparison.py',
        'test_all_fixes.py',
        'test_array_fix.py',
        'test_bar_index_fix.py',
        'test_bug_fix.py',
        'test_compatibility.py',
        'test_comprehensive_debug.py',
        'test_comprehensive_filter_debug.py',
        'test_correct_logic.py',
        'test_crossover_functions.py',
        'test_daily_data.py',
        'test_daily_multi_stocks.py',
        'test_debug_ml.py',
        'test_debug_processor.py',
        'test_enhanced_comprehensive.py',
        'test_enhanced_current_conditions.py',
        'test_enhanced_filters.py',
        'test_enhanced_fixes.py',
        'test_filter_behavior.py',
        'test_filter_comparison.py',
        'test_filter_configurations.py',
        'test_filter_fix.py',
        'test_filters_off.py',
        'test_filters_one_by_one.py',
        'test_filters_simple.py',
        'test_fixed_implementation.py',
        'test_fixed_logic.py',
        'test_icici_daily.py',
        'test_icici_enhanced.py',
        'test_kernel_quick.py',
        'test_kernel_validation.py',
        'test_ml_fix_final.py',
        'test_ml_prediction_fix.py',
        'test_na_handling.py',
        'test_neutral_signal.py',
        'test_new_functions.py',
        'test_phase3_quick.py',
        'test_phase4_icici.py',
        'test_phase4_integration.py',
        'test_pine_functions.py',
        'test_pinescript_style.py',
        'test_processor_filter_states.py',
        'test_real_market_data.py',
        'test_realistic_market_data.py',
        'test_regime_comparison.py',
        'test_regime_real_data.py',
        'test_regime_simple.py',
        'test_regime_v2.py',
        'test_sliding_window_fix.py',
        'test_system.py',
        'test_with_2000_bars.py',
        'test_with_fixes.py',
        'test_zerodha_filters_off.py',
        'run_kernel_test.py',
    ],
    
    'archive/comparison_files': [
        'bar_by_bar_comparison.py',
        'compare_csv_zerodha.py',
        'compare_full_daily_data.py',
        'compare_kernel_values.py',
        'compare_signal_timing.py',
        'compare_tv_zerodha_daily.py',
        'fetch_comparison_data.py',
        'filter_comparison.py',
        'fix_and_compare.py',
        'pine_python_comparison.py',
        'realistic_comparison.py',
        'tradingview_comparison.py',
    ],
    
    'archive/validation_phase_files': [
        'final_validation.py',
        'validate_filter_calc.py',
        'validate_multiple_stocks.py',
        'validate_scanner.py',
        'validate_with_zerodha.py',
        'phase_2_validate_all.py',
        'phase_3_bar_processor_patch.py',
        'phase_3_verification.py',
    ],
    
    'archive/misc_analysis': [
        'check_distance_issue.py',
        'count_pine_signals.py',
        'demonstrate_bar_index_issue.py',
        'diagnose_regime_difference.py',
        'diagnose_signals.py',
        'diagnose_training_labels.py',
        'example_parameter_passing.py',
        'fetch_2000_bars.py',
        'fetch_pinescript_style_data.py',
        'find_icici_symbols.py',
        'prepare_csv_data.py',
        'regime_diagnostic.py',
        'signal_logic_explanation.py',
        'verify_array_indices.py',
        'verify_data_match.py',
        'verify_enhanced_processor.py',
        'verify_filter_tracking.py',
        'verify_sliding_window.py',
    ],
}

# Files to keep in root
KEEP_IN_ROOT = {
    'auth_helper.py',  # Needed for Zerodha auth
    'test_comprehensive_fix_verification.py',  # Main test
    'test_zerodha_comprehensive.py',  # Live data test
    'check_api_status.py',  # Useful utility
    'check_zerodha_access.py',  # Useful utility
    'run_scanner.py',  # Main scanner
    'main.py',  # Entry point
    'find_unused_files.py',  # This script
    'organize_archive.py',  # This script
}

def create_archive():
    """Create archive folders and move files"""
    root = Path(__file__).parent
    moved_count = 0
    
    print("🗂️  ORGANIZING FILES INTO ARCHIVE...")
    print("=" * 80)
    
    for archive_dir, files in TO_ARCHIVE.items():
        archive_path = root / archive_dir
        
        # Create archive directory if needed
        if files:  # Only create if we have files to move
            archive_path.mkdir(parents=True, exist_ok=True)
            print(f"\n📁 {archive_dir}/")
        
        for file in files:
            src = root / file
            if src.exists():
                # Preserve directory structure in archive
                if '/' in file:
                    # Create subdirectory in archive
                    subdir = archive_path / Path(file).parent
                    subdir.mkdir(parents=True, exist_ok=True)
                    dst = archive_path / file
                else:
                    dst = archive_path / file
                
                try:
                    shutil.move(str(src), str(dst))
                    print(f"   ✓ Moved: {file}")
                    moved_count += 1
                except Exception as e:
                    print(f"   ✗ Error moving {file}: {e}")
    
    # Also move existing archive folders
    old_archives = ['archive_old', 'archive_wrong_approach', 'demo', 'debug']
    for old_dir in old_archives:
        old_path = root / old_dir
        if old_path.exists() and old_path.is_dir():
            new_path = root / 'archive' / old_dir
            try:
                shutil.move(str(old_path), str(new_path))
                print(f"\n📁 Moved entire folder: {old_dir} → archive/{old_dir}")
                moved_count += 1
            except Exception as e:
                print(f"   ✗ Error moving {old_dir}: {e}")
    
    print("\n" + "=" * 80)
    print(f"✅ COMPLETE: Moved {moved_count} items to archive")
    print("\n📋 Files kept in root:")
    for f in sorted(KEEP_IN_ROOT):
        if (root / f).exists():
            print(f"   - {f}")
    
    return moved_count

if __name__ == "__main__":
    moved = create_archive()
    
    if moved > 0:
        print("\n💡 Next steps:")
        print("1. Review the archive folder structure")
        print("2. Commit these changes: git add -A && git commit -m 'Organize unused files into archive'")
        print("3. Push to GitHub: git push")