#!/usr/bin/env python3
"""
Quick validation of filter calculation logic
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*70)
print("FILTER CALCULATION VALIDATION")
print("="*70)

# Test the exact calculation used in comprehensive test
def test_filter_calculation():
    # Simulate results from comprehensive test
    results = {
        'filter_states': {
            'volatility_passes': 95,  # Example counts
            'regime_passes': 160,
            'adx_passes': 198,
            'all_pass': 75
        },
        'bars_processed': 198
    }
    
    print(f"\nInput data:")
    print(f"  Filter counts: {results['filter_states']}")
    print(f"  Bars processed: {results['bars_processed']}")
    
    # Apply the exact calculation from _calculate_metrics
    if results['bars_processed'] > 0:
        for filter_name in ['volatility', 'regime', 'adx', 'all']:
            key = f"{filter_name}_passes"
            if key in results['filter_states']:
                pass_rate = results['filter_states'][key] / results['bars_processed'] * 100
                results['filter_states'][f"{filter_name}_pass_rate"] = pass_rate
                print(f"  Calculated {filter_name}_pass_rate: {pass_rate:.1f}%")
    
    # Check what avg_filter_pass would be
    avg_filter_pass = results['filter_states'].get('all_pass_rate', 0)
    print(f"\nAverage filter pass rate (all_pass_rate): {avg_filter_pass:.1f}%")
    
    # Print final filter_states
    print(f"\nFinal filter_states dict:")
    for key, value in results['filter_states'].items():
        print(f"  {key}: {value}")

# Test with zero counts (what we're seeing)
def test_zero_counts():
    print("\n" + "="*50)
    print("Testing with ZERO counts (current issue):")
    
    results = {
        'filter_states': {
            'volatility_passes': 0,
            'regime_passes': 0,
            'adx_passes': 0,
            'all_pass': 0
        },
        'bars_processed': 198
    }
    
    print(f"\nInput data:")
    print(f"  Filter counts: {results['filter_states']}")
    print(f"  Bars processed: {results['bars_processed']}")
    
    # Calculate
    if results['bars_processed'] > 0:
        for filter_name in ['volatility', 'regime', 'adx', 'all']:
            key = f"{filter_name}_passes"
            if key in results['filter_states']:
                pass_rate = results['filter_states'][key] / results['bars_processed'] * 100
                results['filter_states'][f"{filter_name}_pass_rate"] = pass_rate
                print(f"  Calculated {filter_name}_pass_rate: {pass_rate:.1f}%")
    
    avg_filter_pass = results['filter_states'].get('all_pass_rate', 0)
    print(f"\nThis gives avg_filter_pass: {avg_filter_pass:.1f}%")

# Run tests
test_filter_calculation()
test_zero_counts()

print("\n" + "="*50)
print("CONCLUSION:")
print("If filter counts are 0, then pass rates will be 0%")
print("The issue is that filter counts are not being incremented!")
print("Need to check if result.filter_states is None or empty")
