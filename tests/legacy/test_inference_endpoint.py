"""
Test the inference endpoint to see if federated training causes issues
"""
import requests
import json
from pathlib import Path

# Test parameters
API_URL = "https://localhost:8000"
LOGIN_URL = f"{API_URL}/api/v1/auth/login"
INFERENCE_URL = f"{API_URL}/api/v1/inference"  # JWT endpoint, not /predict

# Disable SSL warnings for self-signed cert
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Step 1: Login
print("Step 1: Logging in...")
login_data = {
    "hospital_id": "admin_user",
    "password": "Admin_SecurePass_2025!"
}
response = requests.post(LOGIN_URL, json=login_data, verify=False)
print(f"Login status: {response.status_code}")

if response.status_code != 200:
    print(f"Login failed: {response.text}")
    exit(1)

token = response.json()["access_token"]
print(f"✓ Got token: {token[:50]}...")

# Step 2: Prepare test image
print("\nStep 2: Preparing test image...")
test_image_path = Path("dataset images/2 NIH chest x-ray/normal")
if test_image_path.exists():
    # Get first image from normal folder
    image_files = list(test_image_path.glob("*.jpg")) + list(test_image_path.glob("*.jpeg")) + list(test_image_path.glob("*.png"))
    if image_files:
        test_image_path = image_files[0]
        with open(test_image_path, 'rb') as f:
            image_bytes = f.read()
        print(f"✓ Loaded real chest X-ray: {test_image_path.name} ({len(image_bytes)} bytes)")
    else:
        print("⚠ No images in normal folder")
        exit(1)
else:
    print("⚠ Dataset folder not found")
    exit(1)

# Step 3: Test inference
print("\nStep 3: Testing inference...")
files = {
    'file': ('test.jpg', image_bytes, 'image/jpeg')
}
data = {
    'disease_type': 'chest_xray',
    'patient_id': 'TEST-001'
}
headers = {
    'Authorization': f'Bearer {token}'
}

try:
    print("Sending inference request...")
    response = requests.post(
        INFERENCE_URL,
        files=files,
        data=data,
        headers=headers,
        verify=False,
        timeout=65  # Match our 60s backend timeout + buffer
    )
    
    print(f"\nResponse status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✓ SUCCESS!")
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✗ FAILED")
        print(f"Response: {response.text}")
        
except requests.exceptions.Timeout:
    print("\n✗ REQUEST TIMED OUT (>65 seconds)")
    print("This suggests the inference is taking too long or hanging")
except Exception as e:
    print(f"\n✗ ERROR: {e}")

print("\n" + "="*60)
print("Test complete. Check the server console for backend logs.")
