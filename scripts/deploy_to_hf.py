from huggingface_hub import login, create_repo, upload_folder, HfApi
import os
import sys

# Token provided by user
TOKEN = "None"
SPACE_NAME = "medora-ai"

print(f"🔑 Logging in...")
login(token=TOKEN)

api = HfApi()
user = api.whoami(token=TOKEN)['name']
repo_id = f"{user}/{SPACE_NAME}"

print(f"🏗️  Creating/Checking Space: {repo_id}")
try:
    # Create public space with Docker SDK
    create_repo(repo_id, repo_type="space", space_sdk="docker", private=False)
    print("   Space created successfully!")
except Exception as e:
    if "409" in str(e):
        print(f"   Space already exists, updating it...")
    else:
        print(f"   Error creating space: {e}")
        # Proceeding anyway as upload might work if it exists

    print(f"🚀 Uploading project files to {repo_id}...")
    
    api.upload_folder(
        folder_path=".",
        repo_id=repo_id,
        repo_type="space",
        ignore_patterns=[
            ".git", ".venv", "venv", "__pycache__", "federated_data", 
            "logs", "uploads", "*.DS_Store", "labeled_data.db", 
            "tests/legacy", "docs/archive", "scripts/deploy_to_azure.sh",
            "models/weights",  # Don't upload weights
            "model_pneumonia",  # Exclude large local test folders (~1GB)
            "model_pneumonia/medical-model-inference-test"
        ]
    )
    print(f"\n✅ Deployment Complete!")
    print(f"🔗 View your Space: https://huggingface.co/spaces/{repo_id}")
except Exception as e:
    print(f"\n❌ Upload failed: {e}")
    sys.exit(1)
