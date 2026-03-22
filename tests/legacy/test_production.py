"""
Production Deployment Tests
Comprehensive integration testing for production system
"""
import asyncio
import time
import requests
import json
from pathlib import Path
from typing import Dict, Any

# Test configuration
BASE_URL = "https://localhost:8443"  # Production TLS endpoint
TEST_IMAGES_DIR = Path("static/test_images")

# Disable SSL verification for self-signed certificate testing
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ProductionTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.verify = False  # Accept self-signed cert
        self.access_token = None
        self.refresh_token = None
        self.test_results = []
        
    def log_test(self, name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            "test": name,
            "status": status,
            "details": details
        })
        print(f"{status}: {name}")
        if details:
            print(f"   {details}")
    
    def test_health_check(self):
        """Test basic health check"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            passed = response.status_code == 200
            self.log_test("Health Check", passed, f"Status: {response.status_code}")
            return passed
        except Exception as e:
            self.log_test("Health Check", False, str(e))
            return False
    
    def test_authentication(self):
        """Test JWT authentication flow"""
        # Test login
        try:
            login_data = {
                "hospital_id": "hosp_medora",
                "api_key": "jh_secure_key_2024"
            }
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=login_data,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.log_test("Authentication - Login", True, f"Token received: {self.access_token[:20]}...")
                
                # Update session headers
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                return True
            else:
                self.log_test("Authentication - Login", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Authentication - Login", False, str(e))
            return False
    
    def test_token_verification(self):
        """Test token verification endpoint"""
        if not self.access_token:
            self.log_test("Token Verification", False, "No access token available")
            return False
            
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/auth/verify",
                timeout=5
            )
            
            passed = response.status_code == 200
            if passed:
                data = response.json()
                self.log_test("Token Verification", True, f"Valid: {data.get('valid')}, Hospital: {data.get('hospital_id')}")
            else:
                self.log_test("Token Verification", False, f"Status: {response.status_code}")
            return passed
            
        except Exception as e:
            self.log_test("Token Verification", False, str(e))
            return False
    
    def test_rate_limiting(self):
        """Test rate limiting enforcement"""
        try:
            # Make rapid requests to trigger rate limit
            responses = []
            for i in range(10):
                response = self.session.get(f"{self.base_url}/health", timeout=1)
                responses.append(response.status_code)
            
            # Check for X-RateLimit headers
            last_response = self.session.get(f"{self.base_url}/health")
            headers = last_response.headers
            
            has_rate_limit_headers = (
                "X-RateLimit-Limit" in headers or
                "X-RateLimit-Remaining" in headers
            )
            
            self.log_test("Rate Limiting", has_rate_limit_headers, 
                         f"Headers: {dict(headers) if has_rate_limit_headers else 'No rate limit headers'}")
            return has_rate_limit_headers
            
        except Exception as e:
            self.log_test("Rate Limiting", False, str(e))
            return False
    
    def test_inference(self):
        """Test medical image inference"""
        if not self.access_token:
            self.log_test("Inference", False, "No access token available")
            return False
            
        # Find a test image
        test_images = list(TEST_IMAGES_DIR.glob("*.jpg")) + list(TEST_IMAGES_DIR.glob("*.png"))
        
        if not test_images:
            self.log_test("Inference", False, "No test images found")
            return False
            
        try:
            test_image = test_images[0]
            with open(test_image, 'rb') as f:
                files = {'file': (test_image.name, f, 'image/jpeg')}
                data = {'model_type': 'chest_xray'}
                
                response = self.session.post(
                    f"{self.base_url}/api/v1/predict",
                    files=files,
                    data=data,
                    timeout=10
                )
            
            if response.status_code == 200:
                result = response.json()
                self.log_test("Inference", True, 
                             f"Model: {result.get('model_type')}, Confidence: {result.get('confidence', 0):.2f}")
                return True
            else:
                self.log_test("Inference", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Inference", False, str(e))
            return False
    
    def test_federated_status(self):
        """Test federated learning status endpoint"""
        if not self.access_token:
            self.log_test("Federated Status", False, "No access token available")
            return False
            
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/federated/status",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Federated Status", True, 
                             f"Round: {data.get('current_round')}/{data.get('max_rounds')}, Participants: {data.get('participants_this_round')}")
                return True
            else:
                self.log_test("Federated Status", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Federated Status", False, str(e))
            return False
    
    def test_tls_security(self):
        """Test TLS configuration"""
        try:
            # Check if server enforces HTTPS
            import ssl
            import socket
            
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection(("localhost", 8443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname="localhost") as ssock:
                    protocol = ssock.version()
                    cipher = ssock.cipher()
                    
                    # Check for TLS 1.3 or TLS 1.2
                    tls_secure = protocol in ["TLSv1.3", "TLSv1.2"]
                    
                    self.log_test("TLS Security", tls_secure, 
                                 f"Protocol: {protocol}, Cipher: {cipher[0] if cipher else 'Unknown'}")
                    return tls_secure
                    
        except Exception as e:
            self.log_test("TLS Security", False, str(e))
            return False
    
    def test_audit_logging(self):
        """Test audit logging functionality"""
        import os
        audit_dir = Path("logs/audit")
        
        if audit_dir.exists():
            audit_files = list(audit_dir.glob("audit_*.log"))
            if audit_files:
                # Read last line of most recent log
                latest_log = max(audit_files, key=os.path.getmtime)
                with open(latest_log, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        try:
                            last_entry = json.loads(lines[-1])
                            self.log_test("Audit Logging", True, 
                                         f"Latest: {last_entry.get('event_type')} at {last_entry.get('timestamp')}")
                            return True
                        except:
                            pass
            
            self.log_test("Audit Logging", False, "No audit log entries found")
            return False
        else:
            self.log_test("Audit Logging", False, "Audit directory not found")
            return False
    
    def test_token_refresh(self):
        """Test token refresh endpoint"""
        if not self.refresh_token:
            self.log_test("Token Refresh", False, "No refresh token available")
            return False
            
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data.get("access_token")
                self.log_test("Token Refresh", True, f"New token: {new_token[:20]}...")
                return True
            else:
                self.log_test("Token Refresh", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Token Refresh", False, str(e))
            return False
    
    def run_all_tests(self):
        """Run all production tests"""
        print("\n" + "="*70)
        print("PRODUCTION DEPLOYMENT TESTS")
        print("="*70 + "\n")
        
        # Run tests in order
        tests = [
            ("Health Check", self.test_health_check),
            ("TLS Security", self.test_tls_security),
            ("Authentication", self.test_authentication),
            ("Token Verification", self.test_token_verification),
            ("Token Refresh", self.test_token_refresh),
            ("Rate Limiting", self.test_rate_limiting),
            ("Inference", self.test_inference),
            ("Federated Status", self.test_federated_status),
            ("Audit Logging", self.test_audit_logging),
        ]
        
        passed = 0
        total = len(tests)
        
        for name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ FAIL: {name} - {str(e)}")
            time.sleep(0.5)  # Small delay between tests
        
        # Print summary
        print("\n" + "="*70)
        print(f"TEST SUMMARY: {passed}/{total} PASSED ({passed/total*100:.1f}%)")
        print("="*70 + "\n")
        
        return passed == total

def main():
    """Main test runner"""
    tester = ProductionTester()
    
    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/health", verify=False, timeout=2)
    except:
        print("❌ Server not running. Start with: python run_production.py")
        return
    
    # Run tests
    success = tester.run_all_tests()
    
    if success:
        print("✅ All production tests passed! System ready for deployment.")
    else:
        print("⚠️  Some tests failed. Review logs before deployment.")

if __name__ == "__main__":
    main()
