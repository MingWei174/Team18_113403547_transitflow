import psycopg2

try:
    conn = psycopg2.connect('host=localhost port=5433 user=transitflow password=transitflow dbname=transitflow')
    
    cur = conn.cursor()
    
    # Check all tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    tables = cur.fetchall()
    print(f'Tables in database: {len(tables)}')
    for table in tables:
        print(f'  - {table[0]}')
    
    # Try to create all tables explicitly
    print('\nExecuting schema.sql...')
    with open('databases/relational/schema.sql', 'r', encoding='utf-8') as f:
        schema = f.read()
    
    # Split by semicolon and execute
    statements = [s.strip() for s in schema.split(';') if s.strip() and not s.strip().startswith('--')]
    
    error_count = 0
    for i, stmt in enumerate(statements):
        try:
            cur.execute(stmt)
        except psycopg2.errors.DuplicateTable as e:
            pass  # Expected for existing tables
        except Exception as e:
            print(f'  ✗ Statement {i+1} ERROR: {str(e)[:80]}')
            error_count += 1
    
    conn.commit()
    
    # Check final tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    tables = cur.fetchall()
    print(f'\nFinal tables in database: {len(tables)}')
    for table in tables:
        print(f'  - {table[0]}')
    
    cur.close()
    conn.close()
    
    print(f'\n✓ Schema initialization complete!')
    
except Exception as e:
    print(f'✗ Error: {e}')
