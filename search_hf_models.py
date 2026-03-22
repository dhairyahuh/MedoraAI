
from huggingface_hub import HfApi

api = HfApi()
models = api.list_models(search="bone fracture", sort="downloads", direction=-1, limit=10)

print("Top Bone Fracture Models:")
for model in models:
    print(f"- {model.modelId} ({model.downloads} downloads)")

print("\nTop MURA Models:")
models = api.list_models(search="MURA", sort="downloads", direction=-1, limit=5)
for model in models:
    print(f"- {model.modelId} ({model.downloads} downloads)")
