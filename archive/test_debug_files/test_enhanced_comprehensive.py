"""
Run comprehensive filter test with enhanced processors
"""
import sys
sys.path.append('.')

from test_zerodha_comprehensive import ComprehensiveMarketTest

def main():
    """Run comprehensive test with enhanced processors"""
    print("\n" + "="*70)
    print("🚀 COMPREHENSIVE ENHANCED PROCESSOR TEST")
    print("="*70)
    
    # Test ICICIBANK with 1 year data
    symbols = ['ICICIBANK']
    
    # Create and run test
    tester = ComprehensiveMarketTest()
    
    # Note: The comprehensive test automatically uses EnhancedBarProcessor
    # since bar_processor.py has use_enhanced=True by default
    
    tester.run_comprehensive_test(symbols)
    
    print("\n✅ Enhanced processor comprehensive test complete!")

if __name__ == "__main__":
    main()
