import sqlite3
from pathlib import Path

# Create a simple placeholder image
from PIL import Image
import numpy as np

# Create a 512x512 gray medical-looking image
img = Image.fromarray(np.random.randint(50, 200, (512, 512), dtype=np.uint8), mode='L')
img.save('uploads/test_xray.jpg')
print("✓ Created placeholder test image: uploads/test_xray.jpg")

# Update the database to point to this image
conn = sqlite3.connect('labeled_data.db')
cursor = conn.cursor()

cursor.execute("""
    UPDATE labeled_data 
    SET image_path = 'uploads/test_xray.jpg'
    WHERE review_id LIKE 'test-review%'
""")

conn.commit()
conn.close()

print(f"✓ Updated {cursor.rowcount} test review(s) to use the new image path")
print("\nNow refresh https://localhost:8000/radiologist_review.html")
