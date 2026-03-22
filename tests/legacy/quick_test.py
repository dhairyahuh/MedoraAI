"""
Quick test script to verify the Medical Inference Server is working
"""
import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"
API_KEY = "dev-key-12345"

def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("1. Testing Health Endpoint")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_models():
    """Test models listing"""
    print("\n" + "="*60)
    print("2. Testing Models Endpoint")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/v1/models")
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Total Models: {data['total_models']}")
    print(f"\nAvailable Disease Types:")
    for model in data['models'][:5]:  # Show first 5
        print(f"  - {model['disease_type']}: {model['model_name']} ({model['architecture']})")
    print(f"  ... and {data['total_models'] - 5} more")
    return response.status_code == 200

def test_prediction():
    """Test prediction endpoint"""
    print("\n" + "="*60)
    print("3. Testing Prediction Endpoint (with GPU acceleration!)")
    print("="*60)
    
    # Use the sample image we created
    image_path = Path("static/test_images/sample_chest_xray.jpg")
    
    if not image_path.exists():
        print(f"Error: Test image not found at {image_path}")
        return False
    
    with open(image_path, 'rb') as f:
        files = {'image': ('test.jpg', f, 'image/jpeg')}
        data = {'disease_type': 'chest_xray'}
        headers = {'X-API-Key': API_KEY}
        
        response = requests.post(
            f"{BASE_URL}/api/v1/predict",
            files=files,
            data=data,
            headers=headers
        )
    
    print(f"Status Code: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if response.status_code == 200:
        request_id = result['request_id']
        print(f"\n✓ Prediction queued with ID: {request_id}")
        
        # Wait a moment and check result
        import time
        print("\nWaiting 3 seconds for inference to complete...")
        time.sleep(3)
        
        print("\n" + "="*60)
        print("4. Checking Prediction Result")
        print("="*60)
        
        response = requests.get(
            f"{BASE_URL}/api/v1/result/{request_id}",
            headers=headers
        )
        
        result = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Status: {result['status']}")
        
        if result['status'] == 'completed':
            print(f"\n✓ INFERENCE COMPLETED!")
            print(f"  Model: {result['model']}")
            print(f"  Predicted Class: {result['predicted_class']}")
            print(f"  Confidence: {result['confidence']:.3f}")
            print(f"  Inference Time: {result['inference_time']:.3f}s")
            print(f"\n  All Probabilities:")
            for cls, prob in result['all_probabilities'].items():
                print(f"    {cls}: {prob:.3f}")
            return True
        elif result['status'] == 'processing':
            print(f"  Still processing... (check /result/{request_id} again)")
        else:
            print(f"  Status: {result['status']}")
            if 'error' in result:
                print(f"  Error: {result['error']}")
    
    return response.status_code == 200

def main():
    print("\n" + "="*60)
    print("MEDICAL INFERENCE SERVER - VERIFICATION TEST")
    print("="*60)
    print(f"Server URL: {BASE_URL}")
    print(f"API Key: {API_KEY}")
    
    tests = [
        ("Health Check", test_health),
        ("List Models", test_models),
        ("Submit & Check Prediction", test_prediction),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ Error in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nNext steps:")
        print("  - Access API docs: http://localhost:8000/docs")
        print("  - View dashboard: http://localhost:8000/dashboard")
        print("  - Run load test: locust -f tests/locustfile.py --host=http://localhost:8000")
    else:
        print("\n⚠ Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()
