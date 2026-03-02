import os
import psycopg2

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres.bpjqgtpyfdcpeqixxkad",
        password="under9876rog,.z",
        host="aws-0-ap-northeast-1.pooler.supabase.com",
        port="6543",
        options="-c search_path=schedule_management"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='schedule_management' AND table_name='users'")
    rows = cursor.fetchall()
    print("Columns:")
    for row in rows:
        print(row[0])
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
