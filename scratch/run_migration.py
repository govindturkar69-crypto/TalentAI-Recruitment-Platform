import os
import sys

sys.path.append(os.getcwd())
from dotenv import load_dotenv

from core import get_db_connection


def run_migration():
    load_dotenv()
    migration_path = "database/migrations/001_foundation.sql"

    with open(migration_path, "r") as f:
        sql = f.read()

    # Split by semicolon, filter out empty statements
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        for stmt in statements:
            print(f"Executing: {stmt[:50]}...")
            cursor.execute(stmt)
        conn.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
