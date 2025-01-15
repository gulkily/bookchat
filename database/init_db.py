#!/usr/bin/env python3

import sqlite3
import os
import sys
from pathlib import Path

def init_database():
    """Initialize the SQLite database with the schema and run migrations"""
    # Get the directory containing this script
    db_dir = Path(__file__).parent
    schema_path = db_dir / 'schema.sql'
    migrations_dir = db_dir / 'migrations'
    db_path = db_dir / 'messages.db'

    # Create database directory if it doesn't exist
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(migrations_dir, exist_ok=True)

    print(f"Initializing database at {db_path}")
    
    try:
        # Connect to SQLite database (creates it if it doesn't exist)
        with sqlite3.connect(db_path) as conn:
            # Enable foreign key support
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Read and execute schema file
            with open(schema_path, 'r') as f:
                schema = f.read()
            conn.executescript(schema)

            # Create migrations table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Get list of applied migrations
            applied_migrations = {row[0] for row in conn.execute("SELECT filename FROM migrations")}

            # Get and sort migration files
            migration_files = sorted([f for f in migrations_dir.glob('*.sql')])

            # Apply new migrations
            for migration_file in migration_files:
                if migration_file.name not in applied_migrations:
                    print(f"Applying migration: {migration_file.name}")
                    with open(migration_file, 'r') as f:
                        migration_sql = f.read()
                    conn.executescript(migration_sql)
                    conn.execute("INSERT INTO migrations (filename) VALUES (?)", (migration_file.name,))
                    conn.commit()

            print("Database initialization and migrations completed successfully")
            
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def main():
    """Main function to initialize the database"""
    success = init_database()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
