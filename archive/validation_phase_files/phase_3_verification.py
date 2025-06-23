"""
Phase 3 Verification Script - NA/None Handling
Tests all NA handling fixes across the system
"""
import os
import sys
import math
from typing import List, Optional

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from core.indicators import n_rsi, n_wt, n_cci, n_adx, calculate_rsi
from core.na_handling import (
    validate_ohlcv, filter_none_values, safe_divide, 
    safe_log, safe_sqrt, interpolate_missing_values
)


class TestNAHandling:
    """Comprehensive tests for NA/None handling"""
    
    def __init__(self):
        self.config = TradingConfig()
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        
        self.tests.append({
            "name": test_name,
            "passed": passed,
            "message": message
        })
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def test_validate_ohlcv(self):
        """Test OHLCV validation"""
        print("\n🔍 Testing OHLCV Validation...")
        
        # Test 1: Valid data
        valid, msg = validate_ohlcv(100, 105, 95, 102, 1000)
        self.log_result("Valid OHLCV", valid and msg == "")
        
        # Test 2: None values
        valid, msg = validate_ohlcv(None, 105, 95, 102, 1000)
        self.log_result("None in open", not valid and "Missing" in msg)
        
        # Test 3: NaN values
        valid, msg = validate_ohlcv(100, float('nan'), 95, 102, 1000)
        self.log_result("NaN in high", not valid and "NaN" in msg)
        
        # Test 4: Infinity
        valid, msg = validate_ohlcv(100, float('inf'), 95, 102, 1000)
        self.log_result("Infinity in high", not valid and "Infinity" in msg)
        
        # Test 5: Negative prices
        valid, msg = validate_ohlcv(100, 105, -95, 102, 1000)
        self.log_result("Negative low", not valid and "Negative" in msg)
        
        # Test 6: Illogical data (high < low)
        valid, msg = validate_ohlcv(100, 95, 105, 102, 1000)
        self.log_result("High < Low", not valid and "High is less than low" in msg)
        
        # Test 7: Volume can be None
        valid, msg = validate_ohlcv(100, 105, 95, 102, None)
        self.log_result("None volume allowed", valid)
    
    def test_filter_none_values(self):
        """Test None/NaN filtering"""
        print("\n🔍 Testing None/NaN Filtering...")
        
        # Test 1: Mixed values
        values = [100, None, 102, float('nan'), 104, float('inf'), 106]
        filtered = filter_none_values(values)
        expected = [100, 102, 104, 106]
        self.log_result("Filter mixed values", filtered == expected, 
                       f"Got {filtered}, expected {expected}")
        
        # Test 2: All None
        values = [None, None, None]
        filtered = filter_none_values(values)
        self.log_result("All None values", filtered == [])
        
        # Test 3: Empty list
        filtered = filter_none_values([])
        self.log_result("Empty list", filtered == [])
    
    def test_safe_math_operations(self):
        """Test safe mathematical operations"""
        print("\n🔍 Testing Safe Math Operations...")
        
        # Test safe_divide
        self.log_result("Safe divide normal", safe_divide(10, 2) == 5.0)
        self.log_result("Safe divide by zero", safe_divide(10, 0, -1) == -1)
        self.log_result("Safe divide None", safe_divide(None, 2, -1) == -1)
        
        # Test safe_log
        self.log_result("Safe log normal", abs(safe_log(10) - math.log(10)) < 0.0001)
        self.log_result("Safe log negative", safe_log(-10, -1) == -1)
        self.log_result("Safe log zero", safe_log(0, -1) == -1)
        self.log_result("Safe log None", safe_log(None, -1) == -1)
        
        # Test safe_sqrt
        self.log_result("Safe sqrt normal", safe_sqrt(16) == 4.0)
        self.log_result("Safe sqrt negative", safe_sqrt(-16, -1) == -1)
        self.log_result("Safe sqrt None", safe_sqrt(None, -1) == -1)
    
    def test_interpolation(self):
        """Test missing value interpolation"""
        print("\n🔍 Testing Value Interpolation...")
        
        # Test 1: Simple interpolation
        values = [100, None, 104]
        interpolated = interpolate_missing_values(values)
        expected = [100, 102, 104]  # Linear interpolation
        self.log_result("Simple interpolation", interpolated == expected,
                       f"Got {interpolated}, expected {expected}")
        
        # Test 2: Multiple missing
        values = [100, None, None, 106]
        interpolated = interpolate_missing_values(values)
        expected = [100, 102, 104, 106]
        self.log_result("Multiple missing", interpolated == expected,
                       f"Got {interpolated}, expected {expected}")
        
        # Test 3: Missing at start
        values = [None, None, 104]
        interpolated = interpolate_missing_values(values)
        self.log_result("Missing at start", interpolated[2] == 104)
        
        # Test 4: Missing at end
        values = [100, 102, None]
        interpolated = interpolate_missing_values(values)
        self.log_result("Missing at end", interpolated[0] == 100 and interpolated[1] == 102)
    
    def test_indicators_with_none(self):
        """Test indicators with None values"""
        print("\n🔍 Testing Indicators with None Values...")
        
        # Test RSI with None
        close_values = [100, None, 102, float('nan'), 104, 105, 106, 107, 108, 109, 110]
        try:
            rsi = calculate_rsi(close_values, 14)
            self.log_result("RSI with None values", True, f"RSI = {rsi:.2f}")
        except Exception as e:
            self.log_result("RSI with None values", False, str(e))
        
        # Test normalized RSI
        try:
            n_rsi_val = n_rsi(close_values, 14, 1)
            self.log_result("Normalized RSI with None", True, f"n_RSI = {n_rsi_val:.4f}")
        except Exception as e:
            self.log_result("Normalized RSI with None", False, str(e))
        
        # Test other indicators with minimal data
        high_values = [105, None, 107, float('nan'), 109, 110, 111, 112, 113, 114, 115]
        low_values = [95, None, 97, float('nan'), 99, 100, 101, 102, 103, 104, 105]
        
        try:
            # Test n_cci
            n_cci_val = n_cci(close_values, high_values, low_values, 20, 1)
            self.log_result("n_CCI with None values", True, f"n_CCI = {n_cci_val:.4f}")
        except Exception as e:
            self.log_result("n_CCI with None values", False, str(e))
        
        try:
            # Test n_adx
            n_adx_val = n_adx(high_values, low_values, close_values, 14)
            self.log_result("n_ADX with None values", True, f"n_ADX = {n_adx_val:.4f}")
        except Exception as e:
            self.log_result("n_ADX with None values", False, str(e))
    
    def test_bar_processor_with_invalid_data(self):
        """Test BarProcessor with invalid data"""
        print("\n🔍 Testing BarProcessor with Invalid Data...")
        
        # Create processor with proper total_bars
        processor = BarProcessor(self.config, total_bars=100)
        
        # Test 1: None values in OHLCV
        result = processor.process_bar(None, 105, 95, 102, 1000)
        self.log_result("BarProcessor with None open", result is None)
        
        # Test 2: NaN values
        result = processor.process_bar(100, float('nan'), 95, 102, 1000)
        self.log_result("BarProcessor with NaN high", result is None)
        
        # Test 3: Negative prices
        result = processor.process_bar(100, 105, -95, 102, 1000)
        self.log_result("BarProcessor with negative low", result is None)
        
        # Test 4: Valid data should work
        result = processor.process_bar(100, 105, 95, 102, 1000)
        self.log_result("BarProcessor with valid data", result is not None)
        
        # Test 5: Process multiple bars with some invalid
        valid_count = 0
        for i in range(10):
            if i % 3 == 0:
                # Insert invalid bar
                result = processor.process_bar(None, 105, 95, 102, 1000)
            else:
                # Valid bar
                result = processor.process_bar(100 + i, 105 + i, 95 + i, 102 + i, 1000)
                if result:
                    valid_count += 1
        
        self.log_result("Mixed valid/invalid bars", valid_count > 0,
                       f"Processed {valid_count} valid bars out of 10")
    
    def test_edge_cases(self):
        """Test edge cases"""
        print("\n🔍 Testing Edge Cases...")
        
        # Empty data
        empty_list: List[float] = []
        filtered = filter_none_values(empty_list)
        self.log_result("Empty list handling", filtered == [])
        
        # All invalid data
        all_invalid = [None, float('nan'), float('inf'), float('-inf')]
        filtered = filter_none_values(all_invalid)
        self.log_result("All invalid values", filtered == [])
        
        # Very large dataset with sparse valid data
        large_data = [None] * 1000
        large_data[500] = 100.0
        large_data[501] = 101.0
        interpolated = interpolate_missing_values(large_data)
        self.log_result("Large sparse data", len(interpolated) == 1000)
    
    def run_all_tests(self):
        """Run all NA handling tests"""
        print("=" * 60)
        print("🚀 PHASE 3 VERIFICATION: NA/None Handling")
        print("=" * 60)
        
        self.test_validate_ohlcv()
        self.test_filter_none_values()
        self.test_safe_math_operations()
        self.test_interpolation()
        self.test_indicators_with_none()
        self.test_bar_processor_with_invalid_data()
        self.test_edge_cases()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        
        if self.failed > 0:
            print("\n❌ Failed Tests:")
            for test in self.tests:
                if not test["passed"]:
                    print(f"  - {test['name']}: {test['message']}")
        
        print("\n" + "=" * 60)
        
        if self.failed == 0:
            print("✅ PHASE 3 NA HANDLING: ALL TESTS PASSED! 🎉")
            print("The system now handles None/NaN values gracefully.")
        else:
            print("⚠️  PHASE 3 NA HANDLING: Some tests failed.")
            print("Please review the failed tests above.")
        
        print("=" * 60)
        
        return self.failed == 0


def main():
    """Main entry point"""
    tester = TestNAHandling()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
