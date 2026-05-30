import psycopg2

try:
    conn = psycopg2.connect('host=localhost port=5433 user=transitflow password=transitflow dbname=transitflow')
    cur = conn.cursor()
    
    # Check tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    tables = cur.fetchall()
    print(f'Tables: {len(tables)}')
    for table in tables:
        print(f'  - {table[0]}')
        # Count rows
        try:
            cur.execute(f'SELECT COUNT(*) FROM {table[0]}')
            count = cur.fetchone()[0]
            print(f'    ({count} rows)')
        except:
            pass
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f'Error: {e}')
