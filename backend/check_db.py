import psycopg2
import os

POSTGRES_URL = "postgresql://neondb_owner:npg_QwvUur94cVND@ep-broad-darkness-ao0gip4k.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

try:
    print("Connecting to Neon Database...")
    conn = psycopg2.connect(POSTGRES_URL)
    cur = conn.cursor()
    
    # Check for the most recent documents
    cur.execute("SELECT id, filename, processed, upload_time FROM documents ORDER BY upload_time DESC LIMIT 5;")
    rows = cur.fetchall()
    
    print("\nMost recent documents uploaded:")
    print("-" * 50)
    for row in rows:
        status = "Processed" if row[2] else "STUCK (Unprocessed)"
        print(f"ID: {row[0]} | File: {row[1]} | Status: {status} | Time: {row[3]}")
    print("-" * 50)
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
