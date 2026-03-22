import requests

print("Testing pending-reviews API...")
try:
    response = requests.get('http://127.0.0.1:8000/api/radiologist/pending-reviews?limit=1')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

print("\nTesting stats API...")
try:
    response = requests.get('http://127.0.0.1:8000/api/radiologist/stats')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
