
from transformers import DetrImageProcessor, DetrForObjectDetection
import torch
from PIL import Image
import requests
from pathlib import Path

# Load model
model_id = "Judy07/bone-fracture-DETA"
print(f"Loading {model_id}...")
try:
    processor = DetrImageProcessor.from_pretrained(model_id)
    model = DetrForObjectDetection.from_pretrained(model_id)
except Exception as e:
    print(f"Failed to load model: {e}")
    exit(1)

# Load user image
user_xray_path = Path.home() / "debug_xray.png"
if not user_xray_path.exists():
    print("User xray not found")
    exit(1)

image = Image.open(user_xray_path).convert("RGB")
print("Running inference...")

inputs = processor(images=image, return_tensors="pt")
outputs = model(**inputs)

# Convert outputs (bounding boxes and class logits) to COCO API
# Let's just look at logits
target_sizes = torch.tensor([image.size[::-1]])
results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.5)[0]

print(f"Detections: {len(results['scores'])}")
for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
    box = [round(i, 2) for i in box.tolist()]
    print(f"Detected {model.config.id2label[label.item()]} with confidence {round(score.item(), 3)} at location {box}")

if len(results['scores']) == 0:
    print("No fractures detected (Pass).")
else:
    print("Fractures detected (Fail if normal).")
