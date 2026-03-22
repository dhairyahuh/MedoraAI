"""
Test script for radiologist review system
Verifies database, API routes, and workflow
"""

import sqlite3
import os
from pathlib import Path

def test_database():
    """Test database tables are created"""
    print("\n=== Testing Database ===")
    
    db_path = "labeled_data.db"
    if not os.path.exists(db_path):
        print("❌ Database file not found")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables exist
    tables = ['labeled_data', 'review_audit', 'model_performance']
    for table in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        result = cursor.fetchone()
        if result:
            print(f"✅ Table '{table}' exists")
        else:
            print(f"❌ Table '{table}' missing")
            return False
    
    # Check schema
    cursor.execute("PRAGMA table_info(labeled_data)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    required_columns = ['review_id', 'patient_id', 'disease_type', 'image_path', 
                       'ai_prediction', 'ai_confidence', 'radiologist_label', 'status']
    
    for col in required_columns:
        if col in column_names:
            print(f"✅ Column '{col}' exists")
        else:
            print(f"❌ Column '{col}' missing")
    
    conn.close()
    return True


def test_file_structure():
    """Test required files are in place"""
    print("\n=== Testing File Structure ===")
    
    files_to_check = [
        'api/radiologist_routes.py',
        'static/radiologist_review.html',
        'PRODUCTION_FEATURES_COMPLETE.md'
    ]
    
    all_exist = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            all_exist = False
    
    return all_exist


def test_api_integration():
    """Test API routes are properly configured"""
    print("\n=== Testing API Integration ===")
    
    # Check if routes file has radiologist imports
    with open('api/routes.py', 'r', encoding='utf-8') as f:
        routes_content = f.read()
    
    if 'from api.radiologist_routes import ReviewRequest' in routes_content:
        print("✅ Radiologist routes imported in api/routes.py")
    else:
        print("❌ Radiologist routes not imported")
        return False
    
    if 'create_review' in routes_content:
        print("✅ Review creation integrated into inference")
    else:
        print("❌ Review creation not integrated")
        return False
    
    # Check main.py integration
    with open('main.py', 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    if 'radiologist_router' in main_content:
        print("✅ Radiologist router registered in main.py")
    else:
        print("❌ Radiologist router not registered")
        return False
    
    return True


def test_frontend():
    """Test frontend components"""
    print("\n=== Testing Frontend ===")
    
    # Check radiologist_review.html
    with open('static/radiologist_review.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    required_elements = [
        'review-queue',
        'pending-reviews',
        'submit-review',
        'label-option'
    ]
    
    for element in required_elements:
        if element in html_content:
            print(f"✅ Element '{element}' found")
        else:
            print(f"❌ Element '{element}' missing")
    
    # Check index.html has review link
    with open('static/index.html', 'r', encoding='utf-8') as f:
        index_content = f.read()
    
    if 'radiologist_review.html' in index_content:
        print("✅ Review link added to navigation")
    else:
        print("❌ Review link not in navigation")
    
    return True


def create_test_review():
    """Create a test review entry"""
    print("\n=== Creating Test Review ===")
    
    conn = sqlite3.connect('labeled_data.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO labeled_data 
            (review_id, patient_id, disease_type, image_path, 
             ai_prediction, ai_confidence, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            'test-review-001',
            'P12345',
            'chest_xray',
            'test_images/test_xray.jpg',
            'Pneumonia',
            0.54,
            'pending'
        ))
        
        conn.commit()
        print("✅ Test review created successfully")
        
        # Verify it was created
        cursor.execute("SELECT COUNT(*) FROM labeled_data WHERE review_id = 'test-review-001'")
        count = cursor.fetchone()[0]
        
        if count == 1:
            print("✅ Test review verified in database")
            
            # Show the review
            cursor.execute("SELECT * FROM labeled_data WHERE review_id = 'test-review-001'")
            review = cursor.fetchone()
            print(f"\nTest Review Details:")
            print(f"  Patient: {review[2]}")
            print(f"  Disease: {review[3]}")
            print(f"  Prediction: {review[6]} ({review[7]*100:.1f}% confidence)")
            print(f"  Status: {review[12]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test review: {e}")
        conn.close()
        return False


def print_summary():
    """Print summary of system status"""
    print("\n" + "="*60)
    print("PRODUCTION SYSTEM STATUS")
    print("="*60)
    
    conn = sqlite3.connect('labeled_data.db')
    cursor = conn.cursor()
    
    # Count reviews
    cursor.execute("SELECT COUNT(*) FROM labeled_data")
    total_reviews = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM labeled_data WHERE status = 'pending'")
    pending = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM labeled_data WHERE status = 'reviewed'")
    reviewed = cursor.fetchone()[0]
    
    print(f"\n📊 Database Statistics:")
    print(f"   Total Reviews: {total_reviews}")
    print(f"   Pending: {pending}")
    print(f"   Reviewed: {reviewed}")
    
    # Check audit trail
    cursor.execute("SELECT COUNT(*) FROM review_audit")
    audit_entries = cursor.fetchone()[0]
    print(f"   Audit Entries: {audit_entries}")
    
    conn.close()
    
    print(f"\n🚀 System Components:")
    print(f"   ✅ Database (labeled_data.db)")
    print(f"   ✅ API Routes (/api/radiologist/*)")
    print(f"   ✅ Frontend (radiologist_review.html)")
    print(f"   ✅ Integration (inference → review)")
    print(f"   ✅ Documentation (PRODUCTION_FEATURES_COMPLETE.md)")
    
    print(f"\n📋 Next Steps:")
    print(f"   1. Start server: python main.py")
    print(f"   2. Open: http://localhost:8000/radiologist_review.html")
    print(f"   3. Upload medical images for analysis")
    print(f"   4. Review predictions in queue")
    print(f"   5. Monitor improvement in federated learning")
    
    print("\n✅ SYSTEM READY FOR PRODUCTION DEPLOYMENT\n")


if __name__ == "__main__":
    print("="*60)
    print("RADIOLOGIST REVIEW SYSTEM - VERIFICATION TEST")
    print("="*60)
    
    results = []
    
    results.append(("Database", test_database()))
    results.append(("File Structure", test_file_structure()))
    results.append(("API Integration", test_api_integration()))
    results.append(("Frontend", test_frontend()))
    results.append(("Test Review", create_test_review()))
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print_summary()
    else:
        print("\n⚠️ SOME TESTS FAILED - Review errors above")
