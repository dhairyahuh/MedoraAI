"""
Integration tests for API endpoints
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
import io
from PIL import Image
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

client = TestClient(app)


def create_test_image(size=(224, 224)):
    """Create a test image"""
    img_array = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Medical Inference Server" in response.text


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "queue_length" in data
    assert "models_loaded" in data
    
    print(f"✓ Health check passed: {data}")


def test_models_endpoint():
    """Test models listing endpoint"""
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_models" in data
    assert "models" in data
    assert data["total_models"] > 0
    
    print(f"✓ Found {data['total_models']} available models")


def test_predict_without_api_key():
    """Test predict endpoint without API key (should fail)"""
    img_bytes = create_test_image()
    
    response = client.post(
        "/api/v1/predict",
        files={"image": ("test.jpg", img_bytes, "image/jpeg")},
        data={"disease_type": "chest_xray"}
    )
    
    assert response.status_code == 403
    print("✓ API key validation working")


def test_predict_with_api_key():
    """Test predict endpoint with valid API key"""
    img_bytes = create_test_image()
    
    response = client.post(
        "/api/v1/predict",
        files={"image": ("test.jpg", img_bytes, "image/jpeg")},
        data={"disease_type": "chest_xray"},
        headers={"X-API-Key": "dev-key-12345"}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "request_id" in data
    assert "status" in data
    assert data["status"] == "queued"
    
    print(f"✓ Prediction queued: {data['request_id']}")
    
    return data["request_id"]


def test_predict_invalid_disease_type():
    """Test predict with invalid disease type"""
    img_bytes = create_test_image()
    
    response = client.post(
        "/api/v1/predict",
        files={"image": ("test.jpg", img_bytes, "image/jpeg")},
        data={"disease_type": "invalid_type"},
        headers={"X-API-Key": "dev-key-12345"}
    )
    
    assert response.status_code == 400
    print("✓ Invalid disease type validation working")


def test_predict_invalid_file_type():
    """Test predict with invalid file type"""
    # Create a text file instead of image
    text_file = io.BytesIO(b"This is not an image")
    
    response = client.post(
        "/api/v1/predict",
        files={"image": ("test.txt", text_file, "text/plain")},
        data={"disease_type": "chest_xray"},
        headers={"X-API-Key": "dev-key-12345"}
    )
    
    assert response.status_code == 400
    print("✓ File type validation working")


def test_result_endpoint():
    """Test result retrieval endpoint"""
    # First submit a prediction
    request_id = test_predict_with_api_key()
    
    # Try to get result
    import time
    time.sleep(2)  # Wait a bit for processing
    
    response = client.get(
        f"/api/v1/result/{request_id}",
        headers={"X-API-Key": "dev-key-12345"}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert data["status"] in ["queued", "processing", "completed", "failed"]
    
    print(f"✓ Result status: {data['status']}")


def test_result_not_found():
    """Test result endpoint with invalid request ID"""
    response = client.get(
        "/api/v1/result/invalid-request-id",
        headers={"X-API-Key": "dev-key-12345"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"
    
    print("✓ Not found handling working")


def test_concurrent_requests():
    """Test multiple concurrent requests"""
    request_ids = []
    
    for i in range(5):
        img_bytes = create_test_image()
        
        response = client.post(
            "/api/v1/predict",
            files={"image": (f"test_{i}.jpg", img_bytes, "image/jpeg")},
            data={"disease_type": "chest_xray"},
            headers={"X-API-Key": "dev-key-12345"}
        )
        
        assert response.status_code == 200
        data = response.json()
        request_ids.append(data["request_id"])
    
    print(f"✓ Submitted {len(request_ids)} concurrent requests")
    
    # Check results
    import time
    time.sleep(3)
    
    completed = 0
    for request_id in request_ids:
        response = client.get(
            f"/api/v1/result/{request_id}",
            headers={"X-API-Key": "dev-key-12345"}
        )
        data = response.json()
        if data["status"] == "completed":
            completed += 1
    
    print(f"✓ {completed}/{len(request_ids)} requests completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
