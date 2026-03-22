
import torch
from transformers import DetrImageProcessor, DetrForObjectDetection
from PIL import Image
from pathlib import Path

# Mock setup
model_dir = "/var/www/medora/models/weights/bone_fracture_detr"
device = "cpu"

print(f"Loading model from {model_dir}...")
processor = DetrImageProcessor.from_pretrained(model_dir, local_files_only=True)
model = DetrForObjectDetection.from_pretrained(model_dir, local_files_only=True)
model.to(device)
model.eval()

# Load image
img_path = Path.home() / "debug_xray.png"
image = Image.open(img_path).convert("RGB")

print("Running inference...")
with torch.no_grad():
    inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    outputs = model(**inputs)
    
    # EXACT LOGIC FROM model_manager.py
    logits = outputs.logits[0]
    print(f"Logits shape: {logits.shape}")
    
    probas = logits.softmax(-1)
    print(f"Probas shape: {probas.shape}")
    
    keep = probas[:, 0] > 0.5
    print(f"Keep shape: {keep.shape}, Sum: {keep.sum()}")
    
    fracture_count = keep.sum().item()
    print(f"Fracture count: {fracture_count}")
    
    if fracture_count > 0:
        print("Fractures detected branch")
        # Reproduce the suspect line
        val = probas[keep][:, 0].max()
        print(f"Max value tensor shape: {val.shape}")
        print(f"Max value: {val}")
        confidence = float(val.item())
        print(f"Confidence: {confidence}")
        pidx = 1
    else:
        print("No fractures branch")
        val = probas[:, 0].max()
        print(f"Max value tensor shape: {val.shape}")
        print(f"Max value: {val}")
        confidence = 1.0 - float(val.item())
        print(f"Confidence: {confidence}")
        pidx = 0

    probs_array = [0.0, 0.0]
    probs_array[pidx] = confidence
    probs_array[1-pidx] = 1.0 - confidence
    probabilities = torch.tensor(probs_array)
    print(f"Final probabilities: {probabilities}")
