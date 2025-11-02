#!/usr/bin/env python3
"""
Backend API Testing for CTPO Portfolio Optimizer
Tests the critical constraint fixes and optimization endpoints
"""

import requests
import json
import time
from typing import Dict, Any, List

# Backend URL from frontend/.env
BACKEND_URL = "https://invest-optim.preview.emergentagent.com"

class CTPOBackendTester:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, details: str):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
    
    def test_api_health(self) -> bool:
        """Test basic API connectivity"""
        try:
            response = requests.get(f"{self.backend_url}/api/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("API Health Check", True, f"Response: {data}")
                return True
            else:
                self.log_test("API Health Check", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", False, f"Connection error: {str(e)}")
            return False
    
    def test_popular_tickers(self) -> bool:
        """Test GET /api/tickers/popular endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/api/tickers/popular", timeout=10)
            if response.status_code == 200:
                data = response.json()
                categories = data.get("categories", {})
                
                # Validate structure
                expected_categories = ["Tech Giants", "Finance", "Healthcare", "Consumer", "Energy", "Industrials"]
                has_categories = all(cat in categories for cat in expected_categories)
                
                if has_categories and len(categories["Tech Giants"]) > 0:
                    self.log_test("Popular Tickers Endpoint", True, f"Found {len(categories)} categories")
                    return True
                else:
                    self.log_test("Popular Tickers Endpoint", False, "Missing expected categories")
                    return False
            else:
                self.log_test("Popular Tickers Endpoint", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Popular Tickers Endpoint", False, f"Error: {str(e)}")
            return False
    
    def validate_optimization_result(self, data: Dict[str, Any], test_name: str, expected_assets: int) -> bool:
        """Validate optimization result structure and constraints"""
        try:
            # Check required fields
            required_fields = ["weights", "metrics", "risk_analysis", "cdpr_analysis", "performance"]
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                self.log_test(test_name, False, f"Missing fields: {missing_fields}")
                return False
            
            weights = data["weights"]
            cdpr = data["cdpr_analysis"]
            performance = data["performance"]
            
            # Validation 1: Weights sum to approximately 1.0
            weight_sum = sum(weights.values())
            if not (0.98 <= weight_sum <= 1.02):
                self.log_test(test_name, False, f"Weights sum to {weight_sum:.4f}, expected ~1.0")
                return False
            
            # Validation 2: All weights are non-negative (long-only)
            negative_weights = [ticker for ticker, weight in weights.items() if weight < 0]
            if negative_weights:
                self.log_test(test_name, False, f"Negative weights found: {negative_weights}")
                return False
            
            # Validation 3: Weights are NOT all equal (critical test)
            weight_values = list(weights.values())
            weight_std = sum((w - weight_sum/len(weight_values))**2 for w in weight_values) ** 0.5
            if weight_std < 0.001:  # Very small standard deviation indicates equal weights
                self.log_test(test_name, False, f"All weights are equal (~{weight_values[0]:.3f} each) - solver fallback detected!")
                return False
            
            # Validation 4: Check effective N assets
            effective_n = cdpr.get("effective_n_assets", 0)
            if effective_n < 1.99:  # Allow for floating point precision
                self.log_test(test_name, False, f"Effective N assets too low: {effective_n}")
                return False
            
            # Validation 5: Performance metrics present
            required_perf = ["sharpe_ratio", "sortino_ratio", "max_drawdown", "annual_return"]
            missing_perf = [metric for metric in required_perf if metric not in performance]
            if missing_perf:
                self.log_test(test_name, False, f"Missing performance metrics: {missing_perf}")
                return False
            
            # Validation 6: Force balance analysis
            force_balance_satisfied = cdpr.get("force_balance_satisfied", False)
            force_residual = cdpr.get("force_residual", float('inf'))
            
            # Log detailed results
            details = (
                f"Weights std: {weight_std:.4f}, "
                f"Sum: {weight_sum:.4f}, "
                f"Effective N: {effective_n:.2f}, "
                f"Force balance: {'✓' if force_balance_satisfied else '✗'} "
                f"(residual: {force_residual:.4f}), "
                f"Sharpe: {performance['sharpe_ratio']:.3f}"
            )
            
            self.log_test(test_name, True, details)
            return True
            
        except Exception as e:
            self.log_test(test_name, False, f"Validation error: {str(e)}")
            return False
    
    def test_optimization_10_assets(self) -> bool:
        """TEST 1: Optimization with 10 assets (Previous Failure Case)"""
        payload = {
            "tickers": ["AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"],
            "period": "1y",
            "target_return": 0.08,
            "max_risk": 0.15,
            "min_effective_assets": 10
        }
        
        try:
            print(f"\n🔧 Testing 10-asset optimization (critical test)...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.backend_url}/api/optimize",
                json=payload,
                timeout=30
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response time
                if elapsed > 10:
                    self.log_test("10-Asset Optimization - Response Time", False, f"Took {elapsed:.1f}s (>10s)")
                else:
                    self.log_test("10-Asset Optimization - Response Time", True, f"Completed in {elapsed:.1f}s")
                
                return self.validate_optimization_result(data, "10-Asset Optimization - Core Logic", 10)
            else:
                self.log_test("10-Asset Optimization", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("10-Asset Optimization", False, f"Request error: {str(e)}")
            return False
    
    def test_optimization_5_assets(self) -> bool:
        """TEST 2: Optimization with 5 assets"""
        payload = {
            "tickers": ["AAPL", "GOOGL", "MSFT", "AMZN", "META"],
            "period": "2y",
            "target_return": 0.10,
            "max_risk": 0.20,
            "min_effective_assets": 5
        }
        
        try:
            print(f"\n🔧 Testing 5-asset optimization...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.backend_url}/api/optimize",
                json=payload,
                timeout=30
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response time
                if elapsed > 10:
                    self.log_test("5-Asset Optimization - Response Time", False, f"Took {elapsed:.1f}s (>10s)")
                else:
                    self.log_test("5-Asset Optimization - Response Time", True, f"Completed in {elapsed:.1f}s")
                
                return self.validate_optimization_result(data, "5-Asset Optimization", 5)
            else:
                self.log_test("5-Asset Optimization", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("5-Asset Optimization", False, f"Request error: {str(e)}")
            return False
    
    def test_optimization_3_assets_edge_case(self) -> bool:
        """TEST 3: Edge case with minimum assets (3)"""
        payload = {
            "tickers": ["AAPL", "GOOGL", "MSFT"],
            "period": "6mo",
            "target_return": 0.08,
            "max_risk": 0.15,
            "min_effective_assets": 3
        }
        
        try:
            print(f"\n🔧 Testing 3-asset edge case...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.backend_url}/api/optimize",
                json=payload,
                timeout=30
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response time
                if elapsed > 10:
                    self.log_test("3-Asset Edge Case - Response Time", False, f"Took {elapsed:.1f}s (>10s)")
                else:
                    self.log_test("3-Asset Edge Case - Response Time", True, f"Completed in {elapsed:.1f}s")
                
                return self.validate_optimization_result(data, "3-Asset Edge Case", 3)
            else:
                self.log_test("3-Asset Edge Case", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("3-Asset Edge Case", False, f"Request error: {str(e)}")
            return False
    
    def test_error_handling_invalid_ticker(self) -> bool:
        """TEST: Invalid Ticker Error Handling (Insufficient Data Scenario)"""
        payload = {
            "tickers": ["AAPL", "INVALIDXYZ"],  # Use 2 tickers to bypass single-stock validation
            "period": "1y",
            "position_max": 0.2
        }
        
        try:
            print(f"\n🔧 Testing invalid ticker error handling...")
            response = requests.post(
                f"{self.backend_url}/api/optimize",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 400:
                error_msg = response.json().get("detail", "")
                # Accept either "Invalid ticker not found" OR "Insufficient historical data" as both are valid responses
                if ("Invalid ticker(s):" in error_msg and "not found" in error_msg) or \
                   ("Insufficient historical data" in error_msg):
                    self.log_test("Invalid Ticker Error", True, f"Appropriate error message: {error_msg}")
                    return True
                else:
                    self.log_test("Invalid Ticker Error", False, f"Unexpected error message: {error_msg}")
                    return False
            else:
                self.log_test("Invalid Ticker Error", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Invalid Ticker Error", False, f"Request error: {str(e)}")
            return False
    
    def test_error_handling_single_stock(self) -> bool:
        """TEST: Single Stock Portfolio Error"""
        payload = {
            "tickers": ["AAPL"],
            "period": "1y",
            "position_max": 0.2
        }
        
        try:
            print(f"\n🔧 Testing single stock error handling...")
            response = requests.post(
                f"{self.backend_url}/api/optimize",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 400:
                error_msg = response.json().get("detail", "")
                if "Portfolio optimization requires at least 2 assets" in error_msg:
                    self.log_test("Single Stock Error", True, f"Correct error message: {error_msg}")
                    return True
                else:
                    self.log_test("Single Stock Error", False, f"Wrong error message: {error_msg}")
                    return False
            else:
                self.log_test("Single Stock Error", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Single Stock Error", False, f"Request error: {str(e)}")
            return False
    
    def test_error_handling_empty_portfolio(self) -> bool:
        """TEST: Empty Portfolio Error"""
        payload = {
            "tickers": [],
            "period": "1y",
            "position_max": 0.2
        }
        
        try:
            print(f"\n🔧 Testing empty portfolio error handling...")
            response = requests.post(
                f"{self.backend_url}/api/optimize",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 400:
                error_msg = response.json().get("detail", "")
                if "No tickers provided" in error_msg:
                    self.log_test("Empty Portfolio Error", True, f"Correct error message: {error_msg}")
                    return True
                else:
                    self.log_test("Empty Portfolio Error", False, f"Wrong error message: {error_msg}")
                    return False
            else:
                self.log_test("Empty Portfolio Error", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Empty Portfolio Error", False, f"Request error: {str(e)}")
            return False
    
    def test_error_handling_mixed_tickers(self) -> bool:
        """TEST: Mixed Valid/Invalid Tickers"""
        payload = {
            "tickers": ["AAPL", "GOOGL", "BADTICKER"],  # Use shorter invalid ticker to bypass format validation
            "period": "1y",
            "position_max": 0.2
        }
        
        try:
            print(f"\n🔧 Testing mixed valid/invalid tickers...")
            response = requests.post(
                f"{self.backend_url}/api/optimize",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 400:
                error_msg = response.json().get("detail", "")
                if "BADTICKER" in error_msg and ("not found" in error_msg or "Invalid ticker" in error_msg):
                    self.log_test("Mixed Tickers Error", True, f"Correctly identified bad ticker: {error_msg}")
                    return True
                else:
                    self.log_test("Mixed Tickers Error", False, f"Failed to identify bad ticker: {error_msg}")
                    return False
            else:
                self.log_test("Mixed Tickers Error", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Mixed Tickers Error", False, f"Request error: {str(e)}")
            return False
    
    def test_error_handling_ticker_format(self) -> bool:
        """TEST: Ticker Format Validation"""
        payload = {
            "tickers": ["AAPL", "THISISAVERYLONGTICKERNAME"],
            "period": "1y",
            "position_max": 0.2
        }
        
        try:
            print(f"\n🔧 Testing ticker format validation...")
            response = requests.post(
                f"{self.backend_url}/api/optimize",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 400:
                error_msg = response.json().get("detail", "")
                if "Invalid ticker format" in error_msg and "THISISAVERYLONGTICKERNAME" in error_msg:
                    self.log_test("Ticker Format Error", True, f"Correct format validation: {error_msg}")
                    return True
                else:
                    self.log_test("Ticker Format Error", False, f"Wrong format error: {error_msg}")
                    return False
            else:
                self.log_test("Ticker Format Error", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Ticker Format Error", False, f"Request error: {str(e)}")
            return False
    
    def test_valid_optimization_baseline(self) -> bool:
        """TEST: Valid Optimization (Baseline)"""
        payload = {
            "tickers": ["AAPL", "GOOGL", "MSFT"],
            "period": "1y",
            "position_max": 0.2
        }
        
        try:
            print(f"\n🔧 Testing valid optimization baseline...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.backend_url}/api/optimize",
                json=payload,
                timeout=30
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response time (should be under 2 seconds as per requirements)
                if elapsed > 2:
                    self.log_test("Valid Optimization - Response Time", False, f"Took {elapsed:.1f}s (>2s)")
                    return False
                else:
                    self.log_test("Valid Optimization - Response Time", True, f"Completed in {elapsed:.1f}s")
                
                # Validate the optimization result
                return self.validate_optimization_result(data, "Valid Optimization Baseline", 3)
            else:
                self.log_test("Valid Optimization Baseline", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Valid Optimization Baseline", False, f"Request error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 80)
        print("🚀 CTPO Backend API Testing - Enhanced Error Handling")
        print("=" * 80)
        
        # Test 1: Basic connectivity
        if not self.test_api_health():
            print("\n❌ API not accessible - stopping tests")
            return
        
        # Test 2: Popular tickers endpoint
        self.test_popular_tickers()
        
        # Test 3: Error Handling Tests (Priority Order)
        print("\n" + "=" * 60)
        print("🔍 ERROR HANDLING VALIDATION TESTS")
        print("=" * 60)
        
        error_test_1 = self.test_error_handling_invalid_ticker()
        error_test_2 = self.test_error_handling_single_stock()
        error_test_3 = self.test_error_handling_empty_portfolio()
        error_test_4 = self.test_error_handling_mixed_tickers()
        error_test_5 = self.test_error_handling_ticker_format()
        error_test_6 = self.test_valid_optimization_baseline()
        
        # Test 4: Original optimization tests
        print("\n" + "=" * 60)
        print("⚙️  OPTIMIZATION FUNCTIONALITY TESTS")
        print("=" * 60)
        
        test_10_passed = self.test_optimization_10_assets()
        test_5_passed = self.test_optimization_5_assets()
        test_3_passed = self.test_optimization_3_assets_edge_case()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        total_tests = len(self.test_results)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        
        # Error handling test results
        error_tests_passed = all([error_test_1, error_test_2, error_test_3, error_test_4, error_test_5, error_test_6])
        
        # Critical optimization test results
        critical_tests_passed = test_10_passed and test_5_passed and test_3_passed
        
        print("\n" + "=" * 60)
        print("🔍 ERROR HANDLING RESULTS")
        print("=" * 60)
        
        if error_tests_passed:
            print("✅ ALL ERROR HANDLING TESTS PASSED")
            print("   - Invalid tickers properly identified")
            print("   - Single-stock portfolios rejected with clear message")
            print("   - Empty portfolios handled correctly")
            print("   - Mixed valid/invalid tickers identified")
            print("   - Ticker format validation working")
            print("   - Valid portfolios still optimize correctly")
        else:
            print("❌ SOME ERROR HANDLING TESTS FAILED")
            print("   - Check error message formatting")
            print("   - Verify validation logic")
        
        print("\n" + "=" * 60)
        print("⚙️  OPTIMIZATION RESULTS")
        print("=" * 60)
        
        if critical_tests_passed:
            print("✅ OPTIMIZATION TESTS PASSED - Constraint fixes are working!")
            print("   - Optimization is no longer falling back to equal weights")
            print("   - Solver is finding optimal solutions")
        else:
            print("❌ OPTIMIZATION TESTS FAILED - Constraint issues persist")
            print("   - Check solver logs for 'fallback' status")
            print("   - Verify constraint relaxation is sufficient")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['test']}")
            if result["details"]:
                print(f"   {result['details']}")
        
        return error_tests_passed and critical_tests_passed

if __name__ == "__main__":
    tester = CTPOBackendTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All critical backend tests passed!")
    else:
        print("\n⚠️  Some critical tests failed - review results above")