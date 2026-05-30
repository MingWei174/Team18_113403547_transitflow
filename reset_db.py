import psycopg2
import psycopg2.extensions

try:
    # Connect to default postgres database
    conn = psycopg2.connect('host=localhost port=5433 user=transitflow password=transitflow dbname=postgres')
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    
    cur = conn.cursor()
    
    # Terminate existing connections to transitflow database
    cur.execute("""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = 'transitflow'
        AND pid <> pg_backend_pid()
    """)
    
    # Drop transitflow database
    try:
        cur.execute('DROP DATABASE IF EXISTS transitflow')
        print('✓ Dropped existing transitflow database')
    except Exception as e:
        print(f'  Note: {e}')
    
    # Create transitflow database
    cur.execute('CREATE DATABASE transitflow')
    print('✓ Created new transitflow database')
    
    cur.close()
    conn.close()
    
    # Now connect to the new database and run schema
    conn = psycopg2.connect('host=localhost port=5433 user=transitflow password=transitflow dbname=transitflow')
    
    print('✓ Connected to new database')
    
    with open('databases/relational/schema.sql', 'r', encoding='utf-8') as f:
        schema = f.read()
    
    # Use executescript-like approach: split and execute each statement
    cur = conn.cursor()
    
    # Remove comments
    lines = []
    for line in schema.split('\n'):
        # Remove line comments
        if '--' in line:
            line = line[:line.index('--')]
        line = line.strip()
        if line:
            lines.append(line)
    
    full_text = ' '.join(lines)
    
    # Split by semicolon
    statements = [s.strip() for s in full_text.split(';') if s.strip()]
    
    print(f'Found {len(statements)} statements')
    
    for i, stmt in enumerate(statements):
        try:
            cur.execute(stmt)
            print(f'  ✓ {i+1}/{len(statements)}')
        except Exception as e:
            print(f'  ✗ {i+1} ERROR: {str(e)[:100]}')
    
    conn.commit()
    
    # Check tables
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    tables = cur.fetchall()
    print(f'\n✓ Schema created with {len(tables)} tables:')
    for table in tables:
        print(f'  - {table[0]}')
    
    cur.close()
    conn.close()
    
    # Now seed the data
    print('\n🌱 Seeding data...')
    from skeleton import seed_postgres
    seed_postgres.main()
    
except Exception as e:
    import traceback
    print(f'✗ Error: {e}')
    traceback.print_exc()
