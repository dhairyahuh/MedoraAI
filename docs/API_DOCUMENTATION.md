# 🔌 Medical AI Inference Server - API Documentation

**Version**: 2.0  
**Base URL**: `http://localhost:8000`  
**Interactive Docs**: `http://localhost:8000/docs`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Inference Endpoints](#inference-endpoints)
3. [Radiologist Review Endpoints](#radiologist-review-endpoints)
4. [User Management](#user-management)
5. [Model Management](#model-management)
6. [Monitoring & Health](#monitoring--health)
7. [Error Codes](#error-codes)
8. [Rate Limiting](#rate-limiting)
9. [Python Client Examples](#python-client-examples)

---

## Authentication

All API requests require JWT authentication (except `/auth/login` and `/health`).

### POST `/auth/login`

Authenticate user and receive JWT token.

**Request**:
```http
POST /auth/login HTTP/1.1
Content-Type: application/json

{
  "hospital_id": "hospital_001",
  "password": "user_password"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJob3NwaXRhbF8wMDEiLCJyb2xlIjoicmFkaW9sb2dpc3QiLCJleHAiOjE3MDA1NzYwMDB9.signature",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_info": {
    "user_id": 123,
    "username": "dr.smith",
    "role": "radiologist",
    "hospital_id": "hospital_001",
    "full_name": "Dr. Jane Smith"
  }
}
```

**Errors**:
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: Account locked
- `429 Too Many Requests`: Rate limit exceeded

---

### Using the Token

Include token in `Authorization` header for all authenticated requests:

```http
GET /models/list HTTP/1.1
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token Expiration**:
- Default: 1 hour (3600 seconds)
- Refresh: Login again to get new token
- Auto-logout: Frontend should refresh before expiration

---

## Inference Endpoints

### POST `/inference/{model_name}`

Run AI inference on medical image.

**Parameters**:
- `model_name` (path): Model to use (e.g., `pneumonia_detector`, `skin_cancer_classifier`)

**Request** (multipart/form-data):
```http
POST /inference/pneumonia_detector HTTP/1.1
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

file: <binary image data>
hospital_id: "hospital_001"
metadata: {
  "patient_id": "P12345",
  "study_date": "2025-11-23",
  "modality": "chest_xray"
}
```

**Supported Image Formats**:
- JPEG (.jpg, .jpeg)
- PNG (.png)
- DICOM (.dcm)
- Max size: 50 MB

**Response** (200 OK):
```json
{
  "inference_id": "inf_abc123def456",
  "model_name": "pneumonia_detector",
  "prediction": "Pneumonia",
  "confidence": 0.873,
  "probabilities": {
    "Pneumonia": 0.873,
    "Normal": 0.127
  },
  "processing_time_seconds": 0.124,
  "timestamp": "2025-11-23T14:35:12.123456Z",
  "requires_review": true,
  "metadata": {
    "model_version": "2.1",
    "device": "cuda",
    "image_size": [224, 224]
  }
}
```

**Errors**:
- `400 Bad Request`: Invalid image format or corrupted file
- `404 Not Found`: Model not found
- `413 Payload Too Large`: Image exceeds 50 MB
- `500 Internal Server Error`: Inference failed
- `503 Service Unavailable`: Model temporarily unavailable

**Example (Python)**:
```python
import requests

url = "http://localhost:8000/inference/pneumonia_detector"
headers = {"Authorization": "Bearer YOUR_TOKEN"}
files = {"file": open("chest_xray.jpg", "rb")}
data = {
    "hospital_id": "hospital_001",
    "metadata": '{"patient_id": "P12345"}'
}

response = requests.post(url, headers=headers, files=files, data=data)
result = response.json()
print(f"Prediction: {result['prediction']} ({result['confidence']:.1%})")
```

---

### POST `/inference/batch`

Run inference on multiple images (async processing).

**Request**:
```json
{
  "model_name": "pneumonia_detector",
  "images": [
    {"url": "s3://bucket/image1.jpg", "patient_id": "P001"},
    {"url": "s3://bucket/image2.jpg", "patient_id": "P002"}
  ],
  "hospital_id": "hospital_001"
}
```

**Response** (202 Accepted):
```json
{
  "batch_id": "batch_xyz789",
  "status": "processing",
  "total_images": 2,
  "estimated_completion": "2025-11-23T14:40:12Z"
}
```

**Check Status**:
```http
GET /inference/batch/batch_xyz789
```

**Response** (200 OK):
```json
{
  "batch_id": "batch_xyz789",
  "status": "completed",
  "total_images": 2,
  "completed": 2,
  "failed": 0,
  "results": [
    {"patient_id": "P001", "prediction": "Pneumonia", "confidence": 0.87},
    {"patient_id": "P002", "prediction": "Normal", "confidence": 0.92}
  ]
}
```

---

## Radiologist Review Endpoints

### GET `/radiologist/pending-reviews`

Get list of AI predictions awaiting radiologist confirmation.

**Query Parameters**:
- `hospital_id` (required): Filter by hospital
- `limit` (optional): Max results (default: 50, max: 200)
- `offset` (optional): Pagination offset (default: 0)

**Request**:
```http
GET /radiologist/pending-reviews?hospital_id=hospital_001&limit=20 HTTP/1.1
Authorization: Bearer YOUR_TOKEN
```

**Response** (200 OK):
```json
{
  "total": 150,
  "pending": [
    {
      "review_id": "review_abc123",
      "inference_id": "inf_abc123def456",
      "patient_id": "P12345",
      "image_url": "/images/chest_xray_001.jpg",
      "model_prediction": "Pneumonia",
      "confidence": 0.873,
      "timestamp": "2025-11-23T14:35:12Z",
      "priority": "high"
    },
    {
      "review_id": "review_def456",
      "inference_id": "inf_def456ghi789",
      "patient_id": "P67890",
      "image_url": "/images/chest_xray_002.jpg",
      "model_prediction": "Normal",
      "confidence": 0.652,
      "timestamp": "2025-11-23T14:30:45Z",
      "priority": "medium"
    }
  ],
  "has_more": true,
  "next_offset": 20
}
```

**Priority Levels**:
- **high**: Confidence < 70% OR abnormal finding
- **medium**: 70% ≤ Confidence < 90%
- **low**: Confidence ≥ 90% AND normal finding

---

### POST `/radiologist/submit-review`

Submit radiologist review (confirm or correct AI prediction).

**Request**:
```json
{
  "review_id": "review_abc123",
  "radiologist_id": "radiologist_001",
  "radiologist_label": "Pneumonia",
  "action": "confirm",
  "confidence_level": "high",
  "comments": "Right lower lobe infiltrate clearly visible",
  "time_spent_seconds": 45
}
```

**Fields**:
- `review_id` (required): ID from pending reviews
- `radiologist_id` (required): Your user ID
- `radiologist_label` (required): Your diagnosis
- `action` (required): `"confirm"` (agree with AI) or `"correct"` (disagree)
- `confidence_level` (optional): `"high"`, `"medium"`, `"low"`
- `comments` (optional): Free text notes
- `time_spent_seconds` (optional): Review duration

**Response** (200 OK):
```json
{
  "status": "success",
  "review_id": "review_abc123",
  "training_triggered": true,
  "message": "Review submitted successfully. Model will be retrained.",
  "agreement": true,
  "reward": {
    "radiologist": 1.0,
    "local_model": 0.1
  }
}
```

**Training Behavior**:
- **Confirm**: Positive reinforcement (model rewarded)
- **Correct**: Supervised learning (model learns from mistake)
- **Auto-trigger**: Training starts after review submission

---

### GET `/radiologist/review-history`

Get radiologist's past reviews and performance metrics.

**Query Parameters**:
- `radiologist_id` (required): Your user ID
- `start_date` (optional): ISO format (e.g., `2025-01-01`)
- `end_date` (optional): ISO format
- `limit` (optional): Max results (default: 100)

**Response** (200 OK):
```json
{
  "radiologist_id": "radiologist_001",
  "statistics": {
    "total_reviews": 1247,
    "agreement_rate": 0.847,
    "average_time_seconds": 42.3,
    "reviews_this_week": 135,
    "reviews_this_month": 587
  },
  "recent_reviews": [
    {
      "review_id": "review_xyz789",
      "patient_id": "P12345",
      "model_prediction": "Pneumonia",
      "radiologist_label": "Pneumonia",
      "action": "confirm",
      "timestamp": "2025-11-23T14:35:12Z",
      "time_spent_seconds": 38
    }
  ],
  "performance_trend": {
    "daily_reviews": [45, 52, 48, 50, 47],
    "daily_agreement_rates": [0.85, 0.87, 0.84, 0.86, 0.83]
  }
}
```

---

## User Management

### POST `/users/create`

Create new user account (admin only).

**Request**:
```json
{
  "username": "dr.smith",
  "email": "smith@hospital.com",
  "password": "TempPass123!",
  "role": "radiologist",
  "hospital_id": "hospital_001",
  "full_name": "Dr. Jane Smith",
  "department": "Radiology",
  "license_number": "RAD12345"
}
```

**Roles**:
- `admin`: Full system access
- `radiologist`: Review cases, train models
- `hospital_admin`: Manage hospital users
- `viewer`: Read-only access

**Response** (201 Created):
```json
{
  "user_id": 456,
  "username": "dr.smith",
  "email": "smith@hospital.com",
  "role": "radiologist",
  "hospital_id": "hospital_001",
  "created_at": "2025-11-23T14:35:12Z",
  "temporary_password": "TempPass123!",
  "requires_password_change": true
}
```

**Errors**:
- `400 Bad Request`: Invalid input (weak password, missing fields)
- `403 Forbidden`: Not authorized (not admin)
- `409 Conflict`: Username/email already exists

---

### GET `/users/list`

List all users (with filtering).

**Query Parameters** (admin only):
- `hospital_id` (optional): Filter by hospital
- `role` (optional): Filter by role
- `active` (optional): `true` (default) or `false`

**Response** (200 OK):
```json
{
  "total": 47,
  "users": [
    {
      "user_id": 123,
      "username": "dr.jones",
      "email": "jones@hospital.com",
      "role": "radiologist",
      "hospital_id": "hospital_001",
      "active": true,
      "last_login": "2025-11-23T10:15:30Z"
    }
  ]
}
```

---

### PATCH `/users/{user_id}`

Update user information.

**Request**:
```json
{
  "email": "newemail@hospital.com",
  "full_name": "Dr. Jane Smith-Jones",
  "active": false
}
```

**Response** (200 OK):
```json
{
  "user_id": 123,
  "username": "dr.smith",
  "email": "newemail@hospital.com",
  "updated_at": "2025-11-23T14:35:12Z"
}
```

---

### POST `/users/{user_id}/change-password`

Change user password.

**Request**:
```json
{
  "old_password": "OldPass123!",
  "new_password": "NewSecurePass456!"
}
```

**Password Requirements**:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character (optional)

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Password changed successfully"
}
```

---

## Model Management

### GET `/models/list`

List all available AI models.

**Response** (200 OK):
```json
{
  "models": [
    {
      "model_name": "pneumonia_detector",
      "version": "2.1",
      "modality": "chest_xray",
      "classes": ["Normal", "Pneumonia"],
      "accuracy": 0.847,
      "status": "active",
      "last_updated": "2025-11-20T10:00:00Z",
      "total_inferences": 15423,
      "average_inference_time": 0.124
    },
    {
      "model_name": "skin_cancer_classifier",
      "version": "1.3",
      "modality": "dermatology",
      "classes": ["Benign", "Malignant", "Melanoma"],
      "accuracy": 0.912,
      "status": "active",
      "last_updated": "2025-11-15T14:30:00Z",
      "total_inferences": 8734,
      "average_inference_time": 0.087
    }
  ]
}
```

---

### GET `/models/{model_name}/metrics`

Get detailed performance metrics for a model.

**Response** (200 OK):
```json
{
  "model_name": "pneumonia_detector",
  "version": "2.1",
  "metrics": {
    "accuracy": 0.847,
    "precision": 0.863,
    "recall": 0.829,
    "f1_score": 0.845,
    "auc_roc": 0.921
  },
  "confusion_matrix": [
    [450, 50],
    [75, 425]
  ],
  "class_metrics": {
    "Normal": {"precision": 0.857, "recall": 0.900, "f1": 0.878},
    "Pneumonia": {"precision": 0.895, "recall": 0.850, "f1": 0.872}
  },
  "recent_performance": {
    "last_7_days": {"accuracy": 0.852, "samples": 342},
    "last_30_days": {"accuracy": 0.847, "samples": 1523}
  }
}
```

---

### POST `/models/upload`

Upload new model weights (admin only).

**Request** (multipart/form-data):
```http
POST /models/upload HTTP/1.1
Authorization: Bearer ADMIN_TOKEN
Content-Type: multipart/form-data

file: <binary model file>
model_name: "pneumonia_detector"
version: "2.2"
description: "Improved accuracy with additional training data"
```

**Validation**:
- File format: `.pth`, `.pt`, `.safetensors`
- Max size: 500 MB
- Automatic validation tests (see Model Validator)

**Response** (201 Created):
```json
{
  "model_name": "pneumonia_detector",
  "version": "2.2",
  "status": "uploaded",
  "validation_status": "pending",
  "message": "Model uploaded successfully. Validation in progress."
}
```

**Validation Process**:
1. Format check (extension, size)
2. Loading test (verify model loads)
3. Speed test (inference time < 5 sec)
4. Accuracy test (on validation set, ≥70%)
5. Robustness test (edge cases)
6. GPU compatibility check

**Validation Complete**:
```http
GET /models/pneumonia_detector/validation-status
```

```json
{
  "model_name": "pneumonia_detector",
  "version": "2.2",
  "validation_status": "passed",
  "validation_report": {
    "format": {"passed": true, "size_mb": 243.5},
    "loading": {"passed": true},
    "speed": {"passed": true, "avg_time_seconds": 0.118},
    "accuracy": {"passed": true, "accuracy": 0.871, "samples": 150},
    "robustness": {"passed": true},
    "gpu": {"passed": true, "cuda_available": true}
  },
  "deployment_ready": true
}
```

---

### POST `/models/{model_name}/activate`

Activate uploaded model (make it default for inference).

**Request**:
```json
{
  "version": "2.2",
  "rollback_on_failure": true
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "model_name": "pneumonia_detector",
  "active_version": "2.2",
  "previous_version": "2.1",
  "message": "Model activated successfully"
}
```

---

## Monitoring & Health

### GET `/health`

Health check endpoint (no authentication required).

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-11-23T14:35:12Z",
  "uptime_seconds": 345678,
  "version": "2.0",
  "components": {
    "database": "healthy",
    "models": "healthy",
    "gpu": "available",
    "disk_space": "healthy"
  }
}
```

---

### GET `/monitoring/system-stats`

Get system performance metrics (admin/hospital_admin only).

**Response** (200 OK):
```json
{
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 62.3,
    "disk_usage_percent": 38.7,
    "disk_free_gb": 234.5,
    "gpu_memory_used_gb": 8.2,
    "gpu_memory_total_gb": 24.0
  },
  "application": {
    "total_inferences": 24567,
    "inferences_today": 342,
    "active_users": 12,
    "pending_reviews": 87,
    "average_response_time_ms": 124.3
  },
  "models": {
    "pneumonia_detector": {
      "status": "active",
      "accuracy": 0.847,
      "inferences_today": 156,
      "avg_inference_time_ms": 124
    }
  }
}
```

---

### GET `/monitoring/alerts`

Get recent system alerts.

**Query Parameters**:
- `level` (optional): `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `category` (optional): `system`, `model`, `security`, `performance`
- `start_date` (optional): ISO format
- `end_date` (optional): ISO format
- `limit` (optional): Max results (default: 50)

**Response** (200 OK):
```json
{
  "alerts": [
    {
      "alert_id": "alert_123",
      "level": "WARNING",
      "category": "system",
      "message": "Disk space below 20%",
      "details": {
        "disk_free_gb": 45.2,
        "threshold_gb": 50.0
      },
      "timestamp": "2025-11-23T14:35:12Z",
      "resolved": false
    },
    {
      "alert_id": "alert_124",
      "level": "ERROR",
      "category": "model",
      "message": "Model accuracy dropped below threshold",
      "details": {
        "model_name": "pneumonia_detector",
        "current_accuracy": 0.652,
        "threshold": 0.700,
        "samples": 150
      },
      "timestamp": "2025-11-23T13:20:45Z",
      "resolved": false
    }
  ]
}
```

---

### POST `/monitoring/alerts/{alert_id}/resolve`

Mark alert as resolved (admin only).

**Request**:
```json
{
  "resolution_notes": "Freed up disk space by removing old logs"
}
```

**Response** (200 OK):
```json
{
  "alert_id": "alert_123",
  "resolved": true,
  "resolved_at": "2025-11-23T15:00:00Z",
  "resolved_by": "admin"
}
```

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created (user, model) |
| 202 | Accepted | Async processing started (batch inference) |
| 400 | Bad Request | Invalid input, missing fields |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource (username exists) |
| 413 | Payload Too Large | Image/model file too big |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server bug/crash |
| 503 | Service Unavailable | Model loading, maintenance |

---

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid username or password",
    "details": {
      "field": "password",
      "reason": "incorrect"
    },
    "timestamp": "2025-11-23T14:35:12Z",
    "request_id": "req_abc123"
  }
}
```

---

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_CREDENTIALS` | 401 | Wrong username/password |
| `TOKEN_EXPIRED` | 401 | JWT token expired, login again |
| `INSUFFICIENT_PERMISSIONS` | 403 | User role lacks access |
| `ACCOUNT_LOCKED` | 403 | Too many failed login attempts |
| `MODEL_NOT_FOUND` | 404 | Model doesn't exist |
| `USER_NOT_FOUND` | 404 | User doesn't exist |
| `DUPLICATE_USER` | 409 | Username/email already taken |
| `IMAGE_TOO_LARGE` | 413 | Image exceeds 50 MB |
| `INVALID_IMAGE_FORMAT` | 400 | Unsupported file type |
| `INFERENCE_FAILED` | 500 | Model inference error |
| `DATABASE_ERROR` | 500 | Database query failed |
| `MODEL_LOADING` | 503 | Model still loading |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

---

## Rate Limiting

**Limits**:
- **Login**: 5 requests per minute per IP
- **Inference**: 100 requests per minute per user
- **API calls**: 1000 requests per hour per user

**Rate Limit Headers**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1700576000
```

**Exceeded Response** (429):
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Try again in 42 seconds.",
    "retry_after": 42
  }
}
```

---

## Python Client Examples

### Complete Client Class

```python
import requests
from typing import Dict, List, Optional
from pathlib import Path

class MedicalAIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def login(self, hospital_id: str, password: str) -> Dict:
        """Authenticate and get token"""
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"hospital_id": hospital_id, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        return data
    
    def run_inference(self, model_name: str, image_path: Path, 
                     hospital_id: str, metadata: Optional[Dict] = None) -> Dict:
        """Run AI inference on image"""
        files = {"file": open(image_path, "rb")}
        data = {"hospital_id": hospital_id}
        if metadata:
            data["metadata"] = str(metadata)
        
        response = self.session.post(
            f"{self.base_url}/inference/{model_name}",
            files=files,
            data=data
        )
        response.raise_for_status()
        return response.json()
    
    def get_pending_reviews(self, hospital_id: str, limit: int = 50) -> List[Dict]:
        """Get pending radiologist reviews"""
        response = self.session.get(
            f"{self.base_url}/radiologist/pending-reviews",
            params={"hospital_id": hospital_id, "limit": limit}
        )
        response.raise_for_status()
        return response.json()["pending"]
    
    def submit_review(self, review_id: str, radiologist_id: str,
                     radiologist_label: str, action: str,
                     comments: str = "", time_spent: int = 0) -> Dict:
        """Submit radiologist review"""
        response = self.session.post(
            f"{self.base_url}/radiologist/submit-review",
            json={
                "review_id": review_id,
                "radiologist_id": radiologist_id,
                "radiologist_label": radiologist_label,
                "action": action,
                "comments": comments,
                "time_spent_seconds": time_spent
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_model_metrics(self, model_name: str) -> Dict:
        """Get model performance metrics"""
        response = self.session.get(
            f"{self.base_url}/models/{model_name}/metrics"
        )
        response.raise_for_status()
        return response.json()
    
    def get_system_stats(self) -> Dict:
        """Get system performance statistics"""
        response = self.session.get(
            f"{self.base_url}/monitoring/system-stats"
        )
        response.raise_for_status()
        return response.json()


# Usage Example
if __name__ == "__main__":
    # Initialize client
    client = MedicalAIClient("http://localhost:8000")
    
    # Login
    auth = client.login("hospital_001", "your_password")
    print(f"✓ Logged in as {auth['user_info']['username']}")
    
    # Run inference
    result = client.run_inference(
        model_name="pneumonia_detector",
        image_path=Path("chest_xray.jpg"),
        hospital_id="hospital_001",
        metadata={"patient_id": "P12345"}
    )
    print(f"Prediction: {result['prediction']} ({result['confidence']:.1%})")
    
    # Get pending reviews
    reviews = client.get_pending_reviews("hospital_001", limit=10)
    print(f"Pending reviews: {len(reviews)}")
    
    # Submit review (radiologist confirms AI)
    if reviews:
        review = reviews[0]
        response = client.submit_review(
            review_id=review["review_id"],
            radiologist_id="radiologist_001",
            radiologist_label=review["model_prediction"],
            action="confirm",
            comments="Clear presentation",
            time_spent=45
        )
        print(f"✓ Review submitted: {response['message']}")
    
    # Get model metrics
    metrics = client.get_model_metrics("pneumonia_detector")
    print(f"Model accuracy: {metrics['metrics']['accuracy']:.1%}")
```

---

### Batch Processing Example

```python
import asyncio
from pathlib import Path
from typing import List

async def process_batch(client: MedicalAIClient, image_dir: Path, 
                       model_name: str, hospital_id: str):
    """Process all images in directory"""
    images = list(image_dir.glob("*.jpg"))
    print(f"Processing {len(images)} images...")
    
    results = []
    for image_path in images:
        try:
            result = client.run_inference(
                model_name=model_name,
                image_path=image_path,
                hospital_id=hospital_id,
                metadata={"filename": image_path.name}
            )
            results.append({
                "filename": image_path.name,
                "prediction": result["prediction"],
                "confidence": result["confidence"]
            })
            print(f"✓ {image_path.name}: {result['prediction']} ({result['confidence']:.1%})")
        except Exception as e:
            print(f"✗ {image_path.name}: {e}")
            results.append({
                "filename": image_path.name,
                "error": str(e)
            })
    
    return results

# Usage
client = MedicalAIClient()
client.login("hospital_001", "your_password")
results = asyncio.run(process_batch(
    client,
    Path("./chest_xrays/"),
    "pneumonia_detector",
    "hospital_001"
))
```

---

**Document Version**: 2.0  
**Last Updated**: November 23, 2025  
**Interactive API Docs**: http://localhost:8000/docs
