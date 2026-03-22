import sqlite3

conn = sqlite3.connect('labeled_data.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM labeled_data')
total = cursor.fetchone()[0]
print(f'Total reviews: {total}')

cursor.execute('SELECT review_id, patient_id, disease_type, ai_prediction, status, created_at FROM labeled_data ORDER BY created_at DESC LIMIT 5')
print('\nRecent reviews:')
for row in cursor.fetchall():
    print(f"  {row[0][:8]}... | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")

cursor.execute('SELECT status, COUNT(*) FROM labeled_data GROUP BY status')
print('\nReview status counts:')
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
