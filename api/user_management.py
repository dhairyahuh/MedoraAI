"""
User Management System for Medical Inference Server
Replaces hardcoded radiologist IDs with proper multi-user support
"""
from datetime import datetime
from typing import Optional, Dict, List
import bcrypt
import secrets
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import (
    Table, Column, String, Boolean, DateTime, Integer, 
    select, insert, update, func, text
)
from utils.database import engine, metadata
import logging

logger = logging.getLogger(__name__)

# Models
# Models
class User(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    role: str  # 'admin', 'radiologist', 'viewer'
    hospital_id: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    # Hospital Metadata (Required for JWT)
    hospital_name: Optional[str] = None
    region: Optional[str] = None
    
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = 'radiologist'
    hospital_id: Optional[str] = None
    full_name: Optional[str] = None
    
    # Hospital Metadata
    hospital_name: Optional[str] = None
    region: Optional[str] = None
    compute_capability: Optional[str] = None
    network_speed: Optional[str] = None
    compliance_accepted: bool = False
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['admin', 'radiologist', 'viewer', 'hospital_admin']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of {allowed_roles}')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    hospital_id: Optional[str] = None
    is_active: Optional[bool] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

# Define Table at Module Level
users_table = Table(
    'users', metadata,
    Column('user_id', String, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('email', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False),
    Column('role', String, nullable=False),
    Column('hospital_id', String),
    Column('full_name', String),
    Column('is_active', Boolean, default=True),
    Column('created_at', DateTime, server_default=func.now()),
    Column('last_login', DateTime),
    Column('failed_login_attempts', Integer, default=0),
    Column('locked_until', DateTime),
    # Hospital Columns
    Column('hospital_name', String),
    Column('region', String),
    Column('compute_capability', String),
    Column('compliance_accepted', Boolean, default=False),
    extend_existing=True
)

class UserManager:
    """Manages user accounts, authentication, and permissions"""
    
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Initialize user management tables"""
        # Create table if not exists
        try:
            metadata.create_all(engine)
            self._create_default_admin()
        except Exception as e:
            logger.error(f"Failed to init user stats: {e}")

    def _create_default_admin(self):
        """Create default admin user if none exists"""
        try:
            with engine.connect() as conn:
                result = conn.execute(select(func.count()).select_from(users_table)).scalar()
                if result == 0:
                    logger.info("Creating default admin user...")
                    self.create_user(UserCreate(
                        username="admin",
                        email="admin@medora.ai",
                        password="AdminPassword123!",
                        role="admin",
                        full_name="System Administrator"
                    ))
        except Exception as e:
            logger.warning(f"Could not check/create default admin: {e}")

    def create_user(self, user_in: UserCreate) -> User:
        """Create a new user"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(user_in.password.encode('utf-8'), salt)
        
        import uuid
        user_id = str(uuid.uuid4())
        
        try:
            with engine.begin() as conn:
                stmt = insert(users_table).values(
                    user_id=user_id,
                    username=user_in.username,
                    email=user_in.email,
                    password_hash=hashed.decode('utf-8'),
                    role=user_in.role,
                    hospital_id=user_in.hospital_id,
                    full_name=user_in.full_name,

                    is_active=True,
                    # Hospital Meta
                    hospital_name=user_in.hospital_name,
                    region=user_in.region,
                    compute_capability=user_in.compute_capability,
                    compliance_accepted=user_in.compliance_accepted
                )
                conn.execute(stmt)
                
            return User(
                user_id=user_id,
                username=user_in.username,
                email=user_in.email,
                role=user_in.role,
                hospital_id=user_in.hospital_id,
                full_name=user_in.full_name,
                is_active=True,
                created_at=datetime.utcnow(),
                # Hospital Meta
                hospital_name=user_in.hospital_name,
                region=user_in.region
            )
        except Exception as e:
            if "unique constraint" in str(e).lower():
                raise ValueError("Username or email already exists")
            raise e

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password"""
        with engine.connect() as conn:
            stmt = select(users_table).where(users_table.c.username == username)
            row = conn.execute(stmt).first()
            
            if not row:
                return None
            
            # Check lock
            if row.locked_until and row.locked_until > datetime.now():
                return None
                
            # Verify password
            stored_hash = row.password_hash.encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                # Success - reset failures and update login time
                upd = update(users_table).where(users_table.c.user_id == row.user_id).values(
                    last_login=datetime.now(),
                    failed_login_attempts=0,
                    locked_until=None
                )
                conn.execute(upd)
                conn.commit()
                
                return User(
                    user_id=row.user_id,
                    username=row.username,
                    email=row.email,
                    role=row.role,
                    hospital_id=row.hospital_id,
                    full_name=row.full_name,
                    is_active=row.is_active,
                    created_at=row.created_at,
                    last_login=datetime.now(),
                    # Hospital Meta
                    hospital_name=row.hospital_name,
                    region=row.region
                )
            else:
                # Failure - increment count/lock
                failures = (row.failed_login_attempts or 0) + 1
                values = {'failed_login_attempts': failures}
                if failures >= 5:
                    from datetime import timedelta
                    values['locked_until'] = datetime.now() + timedelta(minutes=15)
                
                upd = update(users_table).where(users_table.c.user_id == row.user_id).values(**values)
                conn.execute(upd)
                conn.commit()
                return None

    def get_user(self, user_id: str) -> Optional[User]:
        with engine.connect() as conn:
            stmt = select(users_table).where(users_table.c.user_id == user_id)
            row = conn.execute(stmt).first()
            if row:
                return User(
                    user_id=row.user_id,
                    username=row.username,
                    email=row.email,
                    role=row.role,
                    hospital_id=row.hospital_id,
                    full_name=row.full_name,
                    is_active=row.is_active,
                    created_at=row.created_at,
                    last_login=row.last_login
                )
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        with engine.connect() as conn:
            stmt = select(users_table).where(users_table.c.email == email)
            row = conn.execute(stmt).first()
            if row:
                return User(
                    user_id=row.user_id,
                    username=row.username,
                    email=row.email,
                    role=row.role,
                    hospital_id=row.hospital_id,
                    full_name=row.full_name,
                    is_active=row.is_active,
                    created_at=row.created_at,
                    last_login=row.last_login
                )
            return None

    # Helper for simple updates usually required
    def update_user(self, user_id: str, updates: UserUpdate) -> Optional[User]:
        values = {}
        if updates.full_name is not None: values['full_name'] = updates.full_name
        if updates.email is not None: values['email'] = updates.email
        if updates.hospital_id is not None: values['hospital_id'] = updates.hospital_id
        if updates.is_active is not None: values['is_active'] = updates.is_active
        
        if not values:
            return self.get_user(user_id)
            
        with engine.begin() as conn:
            stmt = update(users_table).where(users_table.c.user_id == user_id).values(**values)
            res = conn.execute(stmt)
            if res.rowcount > 0:
                pass
        
        return self.get_user(user_id)
