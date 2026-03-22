"""
Radiologist Review API - Enable supervised learning for federated models
Provides endpoints for radiologists to review, confirm, or correct AI predictions
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import os
import logging
import json

# SQLAlchemy
from sqlalchemy import (
    Table, Column, String, Boolean, DateTime, Integer, Float, Text,
    select, insert, update, func, text, desc, case
)
from utils.database import engine, metadata


def get_db_connection():
    """Get raw database connection from engine"""
    return engine.connect()

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Database Schema ---
labeled_data = Table(
    'labeled_data', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('review_id', String, unique=True),
    Column('patient_id', String),
    Column('disease_type', String, nullable=False),
    Column('image_path', String, nullable=False),
    Column('image_hash', String),
    Column('ai_prediction', String, nullable=False),
    Column('ai_confidence', Float, nullable=False),
    Column('radiologist_label', String),
    Column('agrees_with_ai', Boolean),
    Column('notes', Text),
    Column('radiologist_id', String),
    Column('status', String, default='pending'),
    Column('created_at', DateTime, server_default=func.now()),
    Column('reviewed_at', DateTime),
    extend_existing=True
)

review_audit = Table(
    'review_audit', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('review_id', String, nullable=False),
    Column('action', String, nullable=False),
    Column('radiologist_id', String, nullable=False),
    Column('timestamp', DateTime, server_default=func.now()),
    Column('details', Text),
    extend_existing=True
)

model_performance = Table(
    'model_performance', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('disease_type', String, nullable=False),
    Column('date', String, nullable=False), # storing date as string YYYY-MM-DD
    Column('total_predictions', Integer, default=0),
    Column('correct_predictions', Integer, default=0),
    Column('accuracy', Float),
    Column('avg_confidence', Float),
    # Unique constraint handled by logic or DB constraint
    extend_existing=True
)

def init_database():
    """Initialize database tables"""
    try:
        metadata.create_all(engine)
        logger.info("Radiologist tables verified/created")
    except Exception as e:
        logger.error(f"DB Init Error: {e}")

init_database()

# --- Models ---
class ReviewRequest(BaseModel):
    patient_id: Optional[str] = "Anonymous"
    disease_type: str
    image_path: str
    image_hash: Optional[str]
    ai_prediction: str
    confidence: float

class ReviewSubmission(BaseModel):
    review_id: str
    action: str  # 'confirm', 'correct', 'skip'
    radiologist_label: Optional[str]
    notes: Optional[str]
    ai_prediction: str
    confidence: float
    agrees_with_ai: bool

# --- Routes ---

@router.post("/create-review")
async def create_review(request: ReviewRequest):
    import uuid
    import hashlib
    
    review_id = str(uuid.uuid4())
    
    # Generate hash if missing
    if not request.image_hash and os.path.exists(request.image_path):
        with open(request.image_path, 'rb') as f:
            request.image_hash = hashlib.md5(f.read()).hexdigest()
    
    try:
        with engine.begin() as conn:
            # Insert review
            stmt = insert(labeled_data).values(
                review_id=review_id,
                patient_id=request.patient_id,
                disease_type=request.disease_type,
                image_path=request.image_path,
                image_hash=request.image_hash,
                ai_prediction=request.ai_prediction,
                ai_confidence=request.confidence,
                status='pending'
            )
            conn.execute(stmt)
            
            # Audit log
            audit = insert(review_audit).values(
                review_id=review_id,
                action='created',
                radiologist_id='system',
                details=f"AI predicted: {request.ai_prediction} ({request.confidence:.2%})"
            )
            conn.execute(audit)
            
        logger.info(f"Created review {review_id} for {request.disease_type}")
        return {
            "success": True,
            "review_id": review_id,
            "message": "Review created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create review: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending-reviews")
async def get_pending_reviews(
    disease_type: Optional[str] = None,
    limit: int = 20,
    authorization: Optional[str] = Header(None)
):
    try:
        with engine.connect() as conn:
            # Build query
            stmt = select(
                labeled_data.c.review_id.label('id'),
                labeled_data.c.patient_id,
                labeled_data.c.disease_type,
                labeled_data.c.image_path,
                labeled_data.c.ai_prediction,
                labeled_data.c.ai_confidence.label('confidence'),
                labeled_data.c.created_at.label('timestamp')
            ).where(labeled_data.c.status == 'pending')
            
            if disease_type:
                stmt = stmt.where(labeled_data.c.disease_type == disease_type)
            
            # Active learning sort (low confidence first)
            stmt = stmt.order_by(labeled_data.c.ai_confidence.asc(), labeled_data.c.created_at.asc()).limit(limit)
            
            result = conn.execute(stmt)
            reviews = [dict(row._mapping) for row in result]
            
            # Path processing
            import config
            for review in reviews:
                path = review['image_path']
                if path.startswith('temp_'):
                    review['image_url'] = f"/api/radiologist/image/{review['id']}"
                elif path.startswith('uploads/'):
                    review['image_url'] = f"/{path}"
                else:
                    review['image_url'] = f"/uploads/{os.path.basename(path)}"
                
                # Model Name Mapping
                review['model_used'] = config.MODEL_ROUTES.get(review['disease_type'], review['disease_type'])
            
            return {"reviews": reviews, "count": len(reviews)}
    except Exception as e:
        logger.error(f"Failed to fetch reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit-review")
async def submit_review(
    submission: ReviewSubmission,
    authorization: Optional[str] = Header(None)
):
    # Extract hospital_id from JWT
    from api.routes import verify_token
    from fastapi.security import HTTPAuthorizationCredentials
    
    radiologist_id = "radiologist_1" # Fallback
    
    if authorization:
        try:
            # Handle "Bearer <token>"
            token_str = authorization.replace("Bearer ", "")
            from security.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = jwt_handler.verify_token(token_str)
            radiologist_id = payload.get("sub", "radiologist_1")
            
            # If sub is the hospital ID (e.g. fotclinic), use it.
            # If it's a specific user (e.g. admin_fotclinic), we might want the hospital_id field if available
            if payload.get("hospital_id"):
                 radiologist_id = payload.get("hospital_id")
                 
        except Exception as e:
            logger.warning(f"Failed to extract user from token: {e}")
            
    try:
        with engine.begin() as conn:
            if submission.action == 'skip':
                conn.execute(
                    update(labeled_data).where(labeled_data.c.review_id == submission.review_id)
                    .values(status='skipped')
                )
            else:
                conn.execute(
                    update(labeled_data).where(labeled_data.c.review_id == submission.review_id)
                    .values(
                        radiologist_label=submission.radiologist_label,
                        agrees_with_ai=submission.agrees_with_ai,
                        notes=submission.notes,
                        radiologist_id=radiologist_id,
                        status='reviewed',
                        reviewed_at=func.now()
                    )
                )
            
            # Audit
            conn.execute(insert(review_audit).values(
                review_id=submission.review_id,
                action=submission.action,
                radiologist_id=radiologist_id,
                details=f"Label: {submission.radiologist_label}, Agrees: {submission.agrees_with_ai}"
            ))
            
            # Stats
            if submission.action != 'skip':
                update_model_performance(conn, submission.review_id, submission.agrees_with_ai)

        # Trigger Training (outside transaction)
        if submission.action != 'skip' and submission.radiologist_label:
            await trigger_training_task(submission.review_id, submission.radiologist_label, radiologist_id)
            
        return {
            "success": True,
            "message": "Review submitted successfully",
            "ground_truth_created": submission.action != 'skip',
            "training_triggered": submission.action != 'skip' and submission.radiologist_label is not None
        }
            
    except Exception as e:
        logger.error(f"Submit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def update_model_performance(conn, review_id: str, correct: bool):
    # Fetch disease type
    row = conn.execute(
        select(labeled_data.c.disease_type).where(labeled_data.c.review_id == review_id)
    ).first()
    
    if not row: return
    disease_type = row[0]
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Upsert logic
    # Check exists
    check = conn.execute(
        select(model_performance.c.id).where(
            (model_performance.c.disease_type == disease_type) &
            (model_performance.c.date == today)
        )
    ).first()
    
    if check:
        # Update
        conn.execute(
            update(model_performance).where(model_performance.c.id == check.id)
            .values(
                total_predictions=model_performance.c.total_predictions + 1,
                correct_predictions=model_performance.c.correct_predictions + (1 if correct else 0),
                accuracy=(model_performance.c.correct_predictions + (1 if correct else 0)) / (model_performance.c.total_predictions + 1)
            )
        )
    else:
        # Insert
        conn.execute(
            insert(model_performance).values(
                disease_type=disease_type,
                date=today,
                total_predictions=1,
                correct_predictions=1 if correct else 0,
                accuracy=1.0 if correct else 0.0
            )
        )

async def trigger_training_task(review_id: str, label: str, radiologist_id: str):
    try:
        import asyncio
        from api.routes import trigger_supervised_training
        import config
        
        with engine.connect() as conn:
            row = conn.execute(
                select(labeled_data.c.image_path, labeled_data.c.disease_type)
                .where(labeled_data.c.review_id == review_id)
            ).first()
            
        if row:
            image_path, disease_type = row
            if os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                model_name = config.MODEL_ROUTES.get(disease_type, 'unknown')
                
                asyncio.create_task(trigger_supervised_training(
                    review_id=review_id,
                    image_bytes=image_bytes,
                    ground_truth_label=label,
                    model_name=model_name,
                    hospital_id=radiologist_id
                ))
    except Exception as e:
        logger.error(f"Training trigger failed: {e}")

@router.get("/stats")
async def get_stats(disease_type: Optional[str] = None):
    try:
        with engine.connect() as conn:
            query = select(
                func.count().label('total'),
                func.sum(case((labeled_data.c.status == 'pending', 1), else_=0)).label('pending'),
                func.sum(case((labeled_data.c.status == 'reviewed', 1), else_=0)).label('reviewed'),
                func.sum(case((labeled_data.c.agrees_with_ai == True, 1), else_=0)).label('agreed'),
                func.avg(labeled_data.c.ai_confidence).label('avg_conf')
            )
            
            if disease_type:
                query = query.where(labeled_data.c.disease_type == disease_type)
            
            # Case expression requires: from sqlalchemy import case
            # Adding import dynamically or fixing imports above.
            # I forgot 'case' in imports. I will add it in the final string content.
            pass 
            
            # SIMPLIFIED STATS QUERY using text just to be safe with CASE syntax
            sql = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'reviewed' THEN 1 ELSE 0 END) as reviewed,
                    SUM(CASE WHEN agrees_with_ai = true THEN 1 ELSE 0 END) as agreed,
                    AVG(ai_confidence) as avg_confidence
                FROM labeled_data
            """
            params = {}
            if disease_type:
                sql += " WHERE disease_type = :dt"
                params['dt'] = disease_type
                
            row = conn.execute(text(sql), params).fetchone()
            # Handle None results
            total = row[0] or 0
            pending = row[1] or 0
            reviewed = row[2] or 0
            agreed = row[3] or 0
            avg_conf = row[4] or 0.0
            
            # rates
            agreement_rate = (agreed / reviewed * 100) if reviewed > 0 else 0
            
            # Reviewed today
            sql_today = """
                SELECT COUNT(*) FROM labeled_data 
                WHERE status = 'reviewed' AND reviewed_at >= current_date
            """
            # current_date is Postgres; 'datetime("now")' is sqlite.
            # func.now() abstract is better.
            # using text("reviewed_at >= :date")
            today_count = conn.execute(
                select(func.count()).where(
                    (labeled_data.c.status == 'reviewed') & 
                    (labeled_data.c.reviewed_at >= func.current_date())
                )
            ).scalar()
            
            return {
                "pending_reviews": pending,
                "reviewed_today": today_count,
                "total_reviewed": reviewed,
                "ai_accuracy": round(agreement_rate, 1),
                "agreement_rate": round(agreement_rate, 1),
                "avg_confidence": round(avg_conf * 100, 1)
            }
    except Exception as e:
        logger.error(f"Stats fail: {e}")
        # Return zeros on fail
        return {"pending_reviews": 0, "reviewed_today": 0, "total_reviewed": 0, "ai_accuracy": 0, "agreement_rate": 0, "avg_confidence": 0}

@router.get("/training-data")
async def get_training_data(disease_type: Optional[str] = None, min_confidence: float = 0.0, limit: int = 1000):
    try:
        with engine.connect() as conn:
            stmt = select(
                labeled_data.c.image_path,
                labeled_data.c.image_hash,
                labeled_data.c.disease_type,
                labeled_data.c.radiologist_label.label('ground_truth'),
                labeled_data.c.ai_prediction,
                labeled_data.c.ai_confidence,
                labeled_data.c.agrees_with_ai,
                labeled_data.c.reviewed_at
            ).where(
                (labeled_data.c.status == 'reviewed') &
                (labeled_data.c.radiologist_label != None)
            )
            
            if disease_type:
                stmt = stmt.where(labeled_data.c.disease_type == disease_type)
            if min_confidence > 0:
                stmt = stmt.where(labeled_data.c.ai_confidence >= min_confidence)
                
            stmt = stmt.order_by(labeled_data.c.reviewed_at.desc()).limit(limit)
            
            rows = conn.execute(stmt).fetchall()
            data = [dict(row._mapping) for row in rows]
            return {"training_samples": len(data), "data": data}
    except Exception as e:
        logger.error(f"Fetch training data fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
