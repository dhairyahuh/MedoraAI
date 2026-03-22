import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from federated.federated_storage import FederatedStorage
import config
from sqlalchemy import text

def check_connection():
    print("="*60)
    print("DATABASE CONNECTION CHECK")
    print("="*60)
    
    print(f"1. Configuration:")
    print(f"   DATABASE_URL: {config.DATABASE_URL.split('://')[0]}://***@{config.DATABASE_URL.split('@')[-1] if '@' in config.DATABASE_URL else '...'}")
    
    try:
        # Initialize storage (connects to DB)
        storage_dir = Path(config.BASE_DIR) / "federated_data"
        fs = FederatedStorage(storage_dir)
        
        print("\n2. Connection:")
        print("   ✓ FederatedStorage initialized")
        print(f"   ✓ Engine dialect: {fs.engine.name}")
        
        # Run a query
        with fs.engine.connect() as conn:
            result = conn.execute(text("SELECT count(*) FROM training_rounds")).scalar()
            print(f"\n3. Query Test:")
            print(f"   ✓ Successfully executed 'SELECT count(*) FROM training_rounds'")
            print(f"   ✓ Result: {result} rows")
        
        print("\nSUCCESS: Database connection is active and working!")
        return True
        
    except Exception as e:
        print(f"\nFAILURE: Could not connect to database.")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    check_connection()
