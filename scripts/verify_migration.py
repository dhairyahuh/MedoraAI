
import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Load env
from dotenv import load_dotenv
load_dotenv()

from utils.database import engine, metadata
from sqlalchemy import inspect, text

def verify_migration():
    print("="*60)
    print("MIGRATION VERIFICATION")
    print("="*60)
    
    # Check tables
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables in Database ({engine.url}):")
    for t in tables:
        print(f" - {t}")
        
    required = {'users', 'labeled_data', 'review_audit', 'model_performance', 'system_alerts'}
    missing = required - set(tables)
    
    if missing:
        print(f"\n❌ MISSING TABLES: {missing}")
        # Try to force creation (usually happens on app init, but we can force it here)
        print("Attempting to create missing tables via metadata...")
        metadata.create_all(engine)
        tables_after = inspect(engine).get_table_names()
        missing_after = required - set(tables_after)
        if missing_after:
             print(f"❌ STILL MISSING: {missing_after}")
             return False
        else:
             print("✓ Created missing tables.")
    else:
        print("\n✓ All required tables present.")
    
    # Test User Creation (via UserManager refactored code)
    print("\nTesting User Creation...")
    try:
        from api.user_management import UserManager, UserCreate
        um = UserManager() # This triggers init_database which defines logical table
        # Create unique user
        import uuid
        uid = f"test_{uuid.uuid4().hex[:8]}"
        u = um.create_user(UserCreate(
            username=uid,
            email=f"{uid}@example.com",
            password="TestPassword123!",
            role="radiologist",
            full_name="Migration Tester"
        ))
        print(f"✓ Created user: {u.username} (ID: {u.user_id})")
        
        # Verify in DB
        with engine.connect() as conn:
            exists = conn.execute(text("SELECT count(*) FROM users WHERE username=:u"), {'u': uid}).scalar()
            if exists:
                print(f"✓ User confirmed in PostgreSQL 'users' table.")
            else:
                print(f"❌ User NOT found in DB!")
                return False
                
    except Exception as e:
        print(f"❌ User test failed: {e}")
        return False

    print("\nSUCCESS: Migration logic verified.")
    return True

if __name__ == "__main__":
    verify_migration()
