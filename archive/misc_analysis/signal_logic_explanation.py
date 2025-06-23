#!/usr/bin/env python3
"""
Show exactly how filter_all affects signal updates
This demonstrates Pine Script signal logic
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*70)
print("PINE SCRIPT SIGNAL UPDATE LOGIC DEMONSTRATION")
print("="*70)

print("\nPine Script Logic:")
print("""
// From original Pine Script
signal := prediction > 0 and filter_all ? direction.long : 
          prediction < 0 and filter_all ? direction.short : 
          nz(signal[1])  // Keep previous signal
""")

print("\nPython Implementation (lorentzian_knn.py):")
print("""
def update_signal(self, filter_all: bool) -> int:
    if self.prediction > 0 and filter_all:
        self.signal = self.label.long      # 1
    elif self.prediction < 0 and filter_all:
        self.signal = self.label.short     # -1
    # Otherwise keep previous signal (handled by caller)
    return self.signal
""")

print("\n" + "="*70)
print("EXAMPLES:")
print("="*70)

# Example scenarios
scenarios = [
    {
        "name": "Bullish prediction, filters pass",
        "prediction": 5,
        "filter_all": True,
        "previous_signal": -1,
        "expected": 1,
        "explanation": "Signal changes from SHORT to LONG"
    },
    {
        "name": "Bullish prediction, filters FAIL",
        "prediction": 5,
        "filter_all": False,
        "previous_signal": -1,
        "expected": -1,
        "explanation": "Signal STAYS SHORT (no change)"
    },
    {
        "name": "Bearish prediction, filters pass",
        "prediction": -3,
        "filter_all": True,
        "previous_signal": 1,
        "expected": -1,
        "explanation": "Signal changes from LONG to SHORT"
    },
    {
        "name": "Bearish prediction, filters FAIL",
        "prediction": -3,
        "filter_all": False,
        "previous_signal": 1,
        "expected": 1,
        "explanation": "Signal STAYS LONG (no change)"
    }
]

for scenario in scenarios:
    print(f"\nScenario: {scenario['name']}")
    print(f"  ML Prediction: {scenario['prediction']}")
    print(f"  filter_all: {scenario['filter_all']}")
    print(f"  Previous Signal: {scenario['previous_signal']}")
    print(f"  New Signal: {scenario['expected']}")
    print(f"  Result: {scenario['explanation']}")

print("\n" + "="*70)
print("YOUR REPORT ANALYSIS:")
print("="*70)

print("""
In your report:
1. RELIANCE started with NEUTRAL → SHORT on first prediction
2. Filters showed 0% pass rate (filter_all = False)
3. So signal STAYED SHORT forever!

Same for ICICIBANK:
1. Started NEUTRAL → LONG on first prediction  
2. Filters never passed again
3. Signal STAYED LONG forever!

This is EXACTLY Pine Script behavior when filters are too restrictive!
""")

print("\nTO VERIFY ML IS WORKING:")
print("1. Run: python test_filters_off.py")
print("2. This will show ML predictions with filters disabled")
print("3. If predictions vary, ML is fine - filters are the issue")

print("\nTO TEST FILTERS:")
print("1. Run: python test_filters_one_by_one.py")
print("2. This will show which filter is blocking signals")
print("3. Daily data often fails volatility and regime filters")
