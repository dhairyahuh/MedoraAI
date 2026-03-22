"""
Search HuggingFace for more real medical AI models
"""
import requests
import json
from pathlib import Path

def search_huggingface(query, task=None):
    """Search HuggingFace for medical models"""
    url = "https://huggingface.co/api/models"
    params = {
        "search": query,
        "filter": "image-classification",
        "sort": "downloads",
        "limit": 20
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Search error: {e}")
        return []

# Medical search terms
MEDICAL_SEARCHES = [
    "chest xray",
    "brain tumor",
    "brain mri",
    "diabetic retinopathy",
    "retinal",
    "mammogram",
    "breast cancer",
    "ct scan",
    "lung",
    "polyp",
    "colonoscopy",
    "pathology",
    "histopathology",
    "bone fracture",
    "kidney stone",
    "liver",
    "ultrasound",
    "cardiac",
    "heart disease",
]

print("="*80)
print("SEARCHING HUGGINGFACE FOR REAL MEDICAL AI MODELS")
print("="*80)

all_models = {}

for search_term in MEDICAL_SEARCHES:
    print(f"\nSearching: {search_term}...")
    models = search_huggingface(search_term)
    
    if models:
        print(f"  Found {len(models)} models")
        for model in models[:3]:  # Top 3 per search
            model_id = model.get('id', '')
            downloads = model.get('downloads', 0)
            tags = model.get('tags', [])
            
            # Filter for medical/clinical relevance
            medical_keywords = ['medical', 'clinical', 'xray', 'ct', 'mri', 'scan', 'disease', 
                              'cancer', 'tumor', 'diagnosis', 'pathology', 'retina', 'chest',
                              'brain', 'lung', 'skin', 'dermatology', 'radiology']
            
            is_medical = any(keyword in model_id.lower() or 
                           any(keyword in tag.lower() for tag in tags) 
                           for keyword in medical_keywords)
            
            if is_medical and downloads > 10:
                all_models[model_id] = {
                    'downloads': downloads,
                    'tags': tags,
                    'search_term': search_term
                }
                print(f"    ✓ {model_id} ({downloads} downloads)")

print("\n" + "="*80)
print(f"FOUND {len(all_models)} POTENTIAL MEDICAL MODELS")
print("="*80)

# Sort by downloads
sorted_models = sorted(all_models.items(), key=lambda x: x[1]['downloads'], reverse=True)

print("\nTop Medical AI Models by Downloads:\n")
for i, (model_id, info) in enumerate(sorted_models[:20], 1):
    print(f"{i:2d}. {model_id}")
    print(f"    Downloads: {info['downloads']:,}")
    print(f"    Search: {info['search_term']}")
    print(f"    Tags: {', '.join(info['tags'][:5])}")
    print()

# Save results
output = {
    'total_found': len(all_models),
    'models': {k: v for k, v in sorted_models}
}

output_file = Path("huggingface_medical_models.json")
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f"Results saved to: {output_file.absolute()}")
print("\nRecommended models to download:")

# Map to our model types
model_mapping = {
    'pneumonia': ['chest', 'xray', 'pneumonia', 'lung'],
    'brain_tumor': ['brain', 'tumor', 'mri', 'glioma'],
    'diabetic_retinopathy': ['retina', 'diabetic', 'fundus', 'eye'],
    'breast_cancer': ['breast', 'mammogram', 'mammography'],
    'skin_cancer': ['skin', 'melanoma', 'dermatology', 'lesion'],
    'polyp': ['polyp', 'colon', 'colonoscopy'],
    'pathology': ['pathology', 'histology', 'tissue'],
    'fracture': ['fracture', 'bone', 'xray'],
}

recommendations = {}
for our_model, keywords in model_mapping.items():
    for model_id, info in sorted_models:
        if any(keyword in model_id.lower() or keyword in info['search_term'].lower() 
               for keyword in keywords):
            if our_model not in recommendations:
                recommendations[our_model] = []
            if len(recommendations[our_model]) < 2:
                recommendations[our_model].append(model_id)

print("\nMapped to our models:")
for our_model, hf_models in recommendations.items():
    if hf_models:
        print(f"\n{our_model}:")
        for hf_model in hf_models:
            print(f"  • {hf_model}")

print("\n" + "="*80)
print("Next step: Use download_from_huggingface.py to download these models")
print("="*80)
