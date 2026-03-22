"""
Locust load testing script for simulating 1000+ concurrent users
"""
from locust import HttpUser, task, between, events
import random
import io
from PIL import Image
import numpy as np
import time

# API Key for authentication
API_KEY = "dev-key-12345"

# Disease types to test
DISEASE_TYPES = [
    'chest_xray',
    'fundus',
    'dermoscopy',
    'mammogram',
    'brain_mri',
    'ct_scan',
    'colonoscopy',
    'cardiac_mri',
    'pathology',
    'orthopedic'
]


def create_test_image(size=(224, 224)):
    """Create a random test image"""
    img_array = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes


class MedicalImageUser(HttpUser):
    """
    Simulates a user uploading medical images for inference
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts"""
        self.request_ids = []
    
    @task(5)  # Higher weight - submit more predictions
    def upload_chest_xray(self):
        """Upload chest X-ray for pneumonia detection"""
        img_bytes = create_test_image()
        
        with self.client.post(
            "/api/v1/predict",
            files={'image': ('chest_xray.jpg', img_bytes, 'image/jpeg')},
            data={'disease_type': 'chest_xray'},
            headers={'X-API-Key': API_KEY},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.request_ids.append(data.get('request_id'))
                response.success()
            elif response.status_code == 503:
                response.failure("Server at capacity")
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(3)
    def upload_skin_image(self):
        """Upload dermoscopy image for skin cancer detection"""
        img_bytes = create_test_image()
        
        with self.client.post(
            "/api/v1/predict",
            files={'image': ('skin_lesion.jpg', img_bytes, 'image/jpeg')},
            data={'disease_type': 'dermoscopy'},
            headers={'X-API-Key': API_KEY},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.request_ids.append(data.get('request_id'))
                response.success()
            elif response.status_code == 503:
                response.failure("Server at capacity")
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(2)
    def upload_random_image(self):
        """Upload random medical image type"""
        img_bytes = create_test_image()
        disease_type = random.choice(DISEASE_TYPES)
        
        with self.client.post(
            "/api/v1/predict",
            files={'image': (f'{disease_type}.jpg', img_bytes, 'image/jpeg')},
            data={'disease_type': disease_type},
            headers={'X-API-Key': API_KEY},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.request_ids.append(data.get('request_id'))
                response.success()
            elif response.status_code == 503:
                response.failure("Server at capacity")
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(1)
    def check_result(self):
        """Check result of previous request"""
        if not self.request_ids:
            return
        
        request_id = random.choice(self.request_ids[-10:])  # Check recent requests
        
        with self.client.get(
            f"/api/v1/result/{request_id}",
            headers={'X-API-Key': API_KEY},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                
                if status == 'completed':
                    # Record inference time if available
                    inference_time = data.get('inference_time', 0)
                    if inference_time > 0:
                        events.request.fire(
                            request_type="inference",
                            name="inference_latency",
                            response_time=inference_time * 1000,  # Convert to ms
                            response_length=0,
                            exception=None,
                            context={}
                        )
                    response.success()
                elif status == 'failed':
                    response.failure(f"Inference failed: {data.get('error')}")
                else:
                    response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(0.5)
    def check_health(self):
        """Check server health"""
        self.client.get("/api/v1/health")
    
    @task(0.2)
    def list_models(self):
        """List available models"""
        self.client.get("/api/v1/models")


# Custom load test shape for ramping up to 1000 users
class StagesShape:
    """
    Custom load test with stages:
    1. Ramp up to 100 users in 1 minute
    2. Ramp up to 500 users in 2 minutes
    3. Ramp up to 1000 users in 3 minutes
    4. Hold at 1000 users for 5 minutes
    5. Ramp down to 0 users in 1 minute
    """
    
    stages = [
        {"duration": 60, "users": 100, "spawn_rate": 10},
        {"duration": 120, "users": 500, "spawn_rate": 20},
        {"duration": 180, "users": 1000, "spawn_rate": 30},
        {"duration": 480, "users": 1000, "spawn_rate": 0},
        {"duration": 540, "users": 0, "spawn_rate": 50},
    ]


# Event handlers for custom metrics
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics"""
    print("=" * 60)
    print("MEDICAL INFERENCE SERVER LOAD TEST")
    print("=" * 60)
    print(f"Target: {environment.host}")
    print("Simulating 1000+ concurrent users")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary when test stops"""
    stats = environment.stats
    
    print("\n" + "=" * 60)
    print("LOAD TEST SUMMARY")
    print("=" * 60)
    
    total_requests = stats.total.num_requests
    failed_requests = stats.total.num_failures
    success_rate = ((total_requests - failed_requests) / total_requests * 100) if total_requests > 0 else 0
    
    print(f"Total Requests: {total_requests:,}")
    print(f"Successful: {total_requests - failed_requests:,}")
    print(f"Failed: {failed_requests:,}")
    print(f"Success Rate: {success_rate:.2f}%")
    print(f"Median Response Time: {stats.total.median_response_time:.0f}ms")
    print(f"95th Percentile: {stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"99th Percentile: {stats.total.get_response_time_percentile(0.99):.0f}ms")
    print(f"Average Response Time: {stats.total.avg_response_time:.0f}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    
    print("=" * 60)
    
    # Check if performance targets were met
    print("\nPERFORMANCE VALIDATION:")
    
    if success_rate >= 99.9:
        print("✓ Success rate >= 99.9%")
    else:
        print(f"✗ Success rate {success_rate:.2f}% < 99.9%")
    
    p95_time = stats.total.get_response_time_percentile(0.95)
    if p95_time <= 2000:
        print(f"✓ P95 response time {p95_time:.0f}ms <= 2000ms")
    else:
        print(f"✗ P95 response time {p95_time:.0f}ms > 2000ms")
    
    if failed_requests <= total_requests * 0.001:
        print("✓ Failed requests <= 0.1%")
    else:
        print(f"✗ Failed requests {failed_requests/total_requests*100:.2f}% > 0.1%")
    
    print("=" * 60)


if __name__ == "__main__":
    print("""
    Usage:
    
    # Run with default settings (headless mode)
    locust -f locustfile.py --host=http://localhost:8000 --users=1000 --spawn-rate=10 --run-time=10m --headless
    
    # Run with web UI
    locust -f locustfile.py --host=http://localhost:8000
    
    # Quick test
    locust -f locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=5 --run-time=2m --headless
    """)
