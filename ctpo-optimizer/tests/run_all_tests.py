"""
Comprehensive test runner for CTPO system
"""

import pytest
import sys
from pathlib import Path

def main():
    """Run all test suites with reporting"""
    
    print("\n" + "="*70)
    print("🧪 CTPO COMPREHENSIVE TEST SUITE")
    print("="*70 + "\n")
    
    test_dir = Path(__file__).parent
    
    # Run different test categories
    print("\n📋 TEST PLAN:")
    print("  1. Unit Tests (fast component tests)")
    print("  2. Performance Tests (timing benchmarks)")
    print("  3. Integration Tests (crisis scenarios - SLOW)")
    print("\n")
    
    # Test configuration
    test_args = [
        '-v',  # Verbose
        '--tb=short',  # Short traceback
        '-s',  # Show print statements
        '--durations=10',  # Show 10 slowest tests
        str(test_dir)
    ]
    
    # Run tests
    print("🚀 Starting test execution...\n")
    exit_code = pytest.main(test_args)
    
    if exit_code == 0:
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("❌ SOME TESTS FAILED")
        print("="*70 + "\n")
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
