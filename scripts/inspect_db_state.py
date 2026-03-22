
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from utils.database import engine
from sqlalchemy import inspect, text

def inspect_state():
    print("="*60)
    print("DATABASE STATE REPORT")
    print(f"URL: {engine.url}")
    print("="*60)
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if not tables:
        print("No tables found!")
        return

    print(f"\nFound {len(tables)} tables:\n")
    
    with engine.connect() as conn:
        for t in sorted(tables):
            # Get count
            count = conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
            print(f"📂 Table: {t.upper()} ({count} rows)")
            
            # Get latest 1 row sample (if any)
            if count > 0:
                # Try to find a timestamp column for sorting, else just get any
                cols = [c['name'] for c in inspector.get_columns(t)]
                
                # Heuristic for 'latest'
                order_col = None
                if 'timestamp' in cols: order_col = 'timestamp'
                elif 'created_at' in cols: order_col = 'created_at'
                elif 'id' in cols: order_col = 'id'
                elif 'round_id' in cols: order_col = 'round_id'
                
                query = f"SELECT * FROM {t}"
                if order_col:
                    query += f" ORDER BY {order_col} DESC"
                query += " LIMIT 1"
                
                row = conn.execute(text(query)).mappings().first()
                print(f"   Latest Entry: {dict(row)}")
            print("-" * 60)

if __name__ == "__main__":
    inspect_state()
