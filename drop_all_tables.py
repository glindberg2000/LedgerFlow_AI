import psycopg
import os
from dotenv import load_dotenv

# Load environment variables from .env.dev if present
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env.dev"))

DB_NAME = os.environ.get("DB_NAME", "ledgerflow_fresh")
DB_USER = os.environ.get("DB_USER", "newuser")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "newpassword")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5435")

conn_str = f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} host={DB_HOST} port={DB_PORT}"

with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        print("\n--- TABLES ---")
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        for (table,) in cur.fetchall():
            print(f"Table: {table}")
        print("\n--- VIEWS ---")
        cur.execute(
            "SELECT table_name FROM information_schema.views WHERE table_schema = 'public';"
        )
        for (view,) in cur.fetchall():
            print(f"View: {view}")
        print("\n--- SEQUENCES ---")
        cur.execute(
            "SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public';"
        )
        for (seq,) in cur.fetchall():
            print(f"Sequence: {seq}")
        print("\n--- TYPES ---")
        cur.execute(
            "SELECT typname FROM pg_type WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');"
        )
        for (typ,) in cur.fetchall():
            print(f"Type: {typ}")
        print("\n--- INDEXES ---")
        cur.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public';")
        for (idx,) in cur.fetchall():
            print(f"Index: {idx}")
print("\nAll object types in public schema listed.")
