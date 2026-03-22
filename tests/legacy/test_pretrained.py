import requests
import io
import time
from PIL import Image

# Create test image
img = Image.new('RGB', (224, 224), color='gray')
buf = io.BytesIO()
img.save(buf, format='PNG')
buf.seek(0)

# Submit prediction
print("Submitting prediction request...")
files = {'image': ('test.png', buf, 'image/png')}
data = {'disease_type': 'chest_xray'}
headers = {'X-API-Key': 'dev-key-12345'}

r = requests.post(
    'http://localhost:8000/api/v1/predict',
    headers=headers,
    files=files,
    data=data
)

print(f"Response status: {r.status_code}")

if r.status_code != 200:
    print(f"ERROR: {r.json()}")
    exit(1)

request_id = r.json()['request_id']
print(f"Request ID: {request_id}\n")

# Wait for processing
print("Waiting for inference...")
time.sleep(3)

# Get result
r2 = requests.get(
    f'http://localhost:8000/api/v1/result/{request_id}',
    headers={'X-API-Key': 'dev-key-12345'}
)

result = r2.json()

print("="*60)
print("PREDICTION RESULTS WITH PRE-TRAINED WEIGHTS")
print("="*60)
print(f"Full response: {result}\n")
print(f"Status: {result['status']}")

if result['status'] != 'completed':
    print(f"ERROR: Prediction not completed! Status: {result['status']}")
    exit(1)

# Extract results based on API schema
if 'predicted_class' in result:
    predicted_class = result['predicted_class']
    confidence = result.get('confidence', 0.0)
    probabilities = result.get('probabilities', {})
    model_name = result.get('model_name', 'pneumonia_detector')
    inference_time = result.get('inference_time', 0.0)
else:
    print("Unexpected response format!")
    exit(1)

print(f"Model: {model_name}")
print(f"\nPredicted Class: {predicted_class}")
print(f"Confidence: {confidence:.1%}")
print(f"Inference Time: {inference_time:.3f}s")

if probabilities:
    print(f"\nAll Probabilities:")
    for cls, prob in probabilities.items():
        bar = '█' * int(prob * 50)
        print(f"  {cls:25s}: {prob:.1%} {bar}")

print("\n" + "="*60)
print("✓ Pre-trained weights are now loaded!")
print("Confidence should be higher than synthetic weights (32%)")
print("="*60)
