"""
Production Health Check Script
Run periodically to verify server health and alert on issues
"""
import requests
import sys
import time
import json
from typing import Dict, List, Tuple

# Configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = "dev-key-12345"  # Update for production
TIMEOUT = 10
CRITICAL_THRESHOLDS = {
    'queue_length': 800,          # Alert if queue > 80% capacity
    'error_rate': 0.05,           # Alert if error rate > 5%
    'latency_p95': 2.0,           # Alert if p95 latency > 2s
    'uptime_minutes': 1,          # Alert if uptime < 1 minute (recent restart)
}


class HealthCheckResult:
    def __init__(self):
        self.passed = []
        self.warnings = []
        self.critical = []
        self.info = {}
    
    def add_pass(self, check: str):
        self.passed.append(check)
    
    def add_warning(self, check: str, message: str):
        self.warnings.append(f"{check}: {message}")
    
    def add_critical(self, check: str, message: str):
        self.critical.append(f"{check}: {message}")
    
    def is_healthy(self) -> bool:
        return len(self.critical) == 0
    
    def print_report(self):
        """Print formatted health check report"""
        print("=" * 70)
        print("MEDICAL INFERENCE SERVER HEALTH CHECK")
        print("=" * 70)
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Info
        if self.info:
            print("SERVER INFO:")
            for key, value in self.info.items():
                print(f"  {key}: {value}")
            print()
        
        # Passed checks
        if self.passed:
            print(f"✓ PASSED CHECKS ({len(self.passed)}):")
            for check in self.passed:
                print(f"  ✓ {check}")
            print()
        
        # Warnings
        if self.warnings:
            print(f"⚠ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
            print()
        
        # Critical issues
        if self.critical:
            print(f"✗ CRITICAL ISSUES ({len(self.critical)}):")
            for critical in self.critical:
                print(f"  ✗ {critical}")
            print()
        
        # Summary
        print("=" * 70)
        if self.is_healthy():
            print("STATUS: HEALTHY ✓")
        else:
            print("STATUS: UNHEALTHY ✗")
        print("=" * 70)


def check_endpoint_reachable(result: HealthCheckResult) -> bool:
    """Check if server is reachable"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health", timeout=TIMEOUT)
        if response.status_code == 200:
            result.add_pass("Server reachable")
            return True
        else:
            result.add_critical("Server reachable", f"HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        result.add_critical("Server reachable", "Cannot connect to server")
        return False
    except requests.exceptions.Timeout:
        result.add_critical("Server reachable", "Connection timeout")
        return False
    except Exception as e:
        result.add_critical("Server reachable", str(e))
        return False


def check_health_endpoint(result: HealthCheckResult) -> Dict:
    """Check health endpoint and return data"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health", timeout=TIMEOUT)
        data = response.json()
        
        # Store info
        result.info['Status'] = data.get('status', 'unknown')
        result.info['Models Loaded'] = data.get('models_loaded', 0)
        result.info['Queue Length'] = data.get('queue_length', 0)
        result.info['Uptime'] = f"{data.get('uptime_seconds', 0):.1f}s"
        
        # Check status
        if data.get('status') == 'healthy':
            result.add_pass("Health status is healthy")
        else:
            result.add_critical("Health status", f"Status: {data.get('status')}")
        
        # Check models loaded
        if data.get('models_loaded', 0) > 0:
            result.add_pass(f"Models available ({data['models_loaded']})")
        else:
            result.add_warning("Models loaded", "No models loaded yet (lazy loading enabled)")
        
        # Check queue length
        queue_len = data.get('queue_length', 0)
        if queue_len < CRITICAL_THRESHOLDS['queue_length']:
            result.add_pass("Queue length normal")
        else:
            result.add_critical("Queue length", f"Queue at {queue_len} (threshold: {CRITICAL_THRESHOLDS['queue_length']})")
        
        # Check uptime
        uptime_seconds = data.get('uptime_seconds', 0)
        if uptime_seconds > CRITICAL_THRESHOLDS['uptime_minutes'] * 60:
            result.add_pass("Server uptime stable")
        else:
            result.add_warning("Server uptime", f"Recent restart detected ({uptime_seconds:.0f}s)")
        
        return data
        
    except Exception as e:
        result.add_critical("Health endpoint", str(e))
        return {}


def check_metrics_endpoint(result: HealthCheckResult):
    """Check Prometheus metrics"""
    try:
        response = requests.get(f"{API_BASE_URL}/metrics", timeout=TIMEOUT)
        if response.status_code == 200:
            result.add_pass("Metrics endpoint accessible")
            
            # Parse metrics
            metrics_text = response.text
            
            # Check error rate
            total_match = metrics_text.split('inference_requests_total ')
            if len(total_match) > 1:
                total = int(total_match[1].split('\n')[0])
                result.info['Total Requests'] = total
                
                # Calculate error rate
                failed_match = metrics_text.split('inference_failed_total ')
                if len(failed_match) > 1:
                    failed = int(failed_match[1].split('\n')[0])
                    error_rate = failed / total if total > 0 else 0
                    result.info['Error Rate'] = f"{error_rate * 100:.2f}%"
                    
                    if error_rate < CRITICAL_THRESHOLDS['error_rate']:
                        result.add_pass("Error rate acceptable")
                    else:
                        result.add_critical("Error rate", f"{error_rate * 100:.1f}% (threshold: {CRITICAL_THRESHOLDS['error_rate'] * 100}%)")
        else:
            result.add_warning("Metrics endpoint", f"HTTP {response.status_code}")
    
    except Exception as e:
        result.add_warning("Metrics endpoint", str(e))


def check_prediction_flow(result: HealthCheckResult):
    """Test end-to-end prediction flow"""
    try:
        # Create test image
        from PIL import Image
        import io
        
        img = Image.new('RGB', (224, 224), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # Submit prediction
        files = {'file': ('test.jpg', img_bytes, 'image/jpeg')}
        data = {'disease_type': 'chest_xray'}
        headers = {'X-API-Key': API_KEY}
        
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/api/v1/predict",
            files=files,
            data=data,
            headers=headers,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            request_id = response.json().get('request_id')
            
            # Check result
            max_retries = 10
            for _ in range(max_retries):
                result_response = requests.get(
                    f"{API_BASE_URL}/api/v1/result/{request_id}",
                    headers=headers,
                    timeout=TIMEOUT
                )
                
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    status = result_data.get('status')
                    
                    if status == 'completed':
                        latency = time.time() - start_time
                        result.info['Test Prediction Latency'] = f"{latency:.2f}s"
                        
                        if latency < CRITICAL_THRESHOLDS['latency_p95']:
                            result.add_pass("Prediction flow working")
                        else:
                            result.add_warning("Prediction latency", f"{latency:.2f}s (threshold: {CRITICAL_THRESHOLDS['latency_p95']}s)")
                        return
                    elif status == 'failed':
                        result.add_critical("Prediction flow", f"Prediction failed: {result_data.get('error')}")
                        return
                
                time.sleep(0.5)
            
            result.add_warning("Prediction flow", "Prediction timeout")
        else:
            result.add_critical("Prediction flow", f"Submit failed: HTTP {response.status_code}")
    
    except Exception as e:
        result.add_warning("Prediction flow", f"Test failed: {str(e)}")


def check_dashboard(result: HealthCheckResult):
    """Check dashboard accessibility"""
    try:
        response = requests.get(f"{API_BASE_URL}/dashboard", timeout=TIMEOUT)
        if response.status_code == 200 and 'Medical Inference Server' in response.text:
            result.add_pass("Dashboard accessible")
        else:
            result.add_warning("Dashboard", f"HTTP {response.status_code}")
    except Exception as e:
        result.add_warning("Dashboard", str(e))


def main():
    """Run all health checks"""
    result = HealthCheckResult()
    
    # Check 1: Server reachable
    if not check_endpoint_reachable(result):
        result.print_report()
        sys.exit(1)
    
    # Check 2: Health endpoint
    check_health_endpoint(result)
    
    # Check 3: Metrics endpoint
    check_metrics_endpoint(result)
    
    # Check 4: Dashboard
    check_dashboard(result)
    
    # Check 5: End-to-end prediction
    check_prediction_flow(result)
    
    # Print report
    result.print_report()
    
    # Exit code
    sys.exit(0 if result.is_healthy() else 1)


if __name__ == "__main__":
    main()
