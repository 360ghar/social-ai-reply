"""Migration script: Local auth → Supabase Auth.

This script handles the database schema changes needed for the auth migration:
1. Adds supabase_user_id column to account_users
2. Removes password_hash column from account_users
3. Drops the password_reset_tokens table (Supabase handles resets now)

IMPORTANT: Run this script AFTER you have:
1. Created all existing users in Supabase (manually or via the Supabase admin API)
2. Mapped each local user's ID to their Supabase UUID

Usage:
    # Dry run — shows what would change
    python scripts/migrate_auth_to_supabase.py --dry-run

    # Execute the migration
    python scripts/migrate_auth_to_supabase.py --execute

    # If you have a JSON mapping file of email → supabase_user_id:
    python scripts/migrate_auth_to_supabase.py --execute --mapping users_mapping.json
"""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import text

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal, engine


def check_column_exists(conn, table: str, column: str) -> bool:
    """Check if a column exists in a table (works for SQLite and PostgreSQL)."""
    db_url = str(engine.url)
    if "sqlite" in db_url:
        result = conn.execute(text(f"PRAGMA table_info({table})"))
        columns = [row[1] for row in result]
        return column in columns
    else:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ), {"table": table, "column": column})
        return result.fetchone() is not None


def check_table_exists(conn, table: str) -> bool:
    db_url = str(engine.url)
    if "sqlite" in db_url:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:table"
        ), {"table": table})
        return result.fetchone() is not None
    else:
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_name = :table"
        ), {"table": table})
        return result.fetchone() is not None


def run_migration(dry_run: bool = True, mapping_file: str | None = None):
    """Execute the auth migration."""
    db_url = str(engine.url)
    is_sqlite = "sqlite" in db_url
    print(f"Database: {db_url}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTING'}\n")

    session = SessionLocal()

    try:
        conn = session.connection()

        # Step 1: Check current state
        has_password_hash = check_column_exists(conn, "account_users", "password_hash")
        has_supabase_id = check_column_exists(conn, "account_users", "supabase_user_id")
        has_reset_tokens = check_table_exists(conn, "password_reset_tokens")

        print("Current state:")
        print(f"  account_users.password_hash exists: {has_password_hash}")
        print(f"  account_users.supabase_user_id exists: {has_supabase_id}")
        print(f"  password_reset_tokens table exists: {has_reset_tokens}")
        print()

        # Step 2: Load user mapping if provided
        user_mapping = {}
        if mapping_file:
            with open(mapping_file) as f:
                user_mapping = json.load(f)
            print(f"Loaded {len(user_mapping)} user mappings from {mapping_file}")
            print()

        # Step 3: Add supabase_user_id column
        if not has_supabase_id:
            print("Adding supabase_user_id column to account_users...")
            if not dry_run:
                if is_sqlite:
                    conn.execute(text(
                        "ALTER TABLE account_users ADD COLUMN supabase_user_id VARCHAR(255)"
                    ))
                else:
                    conn.execute(text(
                        "ALTER TABLE account_users ADD COLUMN supabase_user_id VARCHAR(255) UNIQUE"
                    ))
                session.commit()
            print("  Done." if not dry_run else "  [Would add column]")
        else:
            print("supabase_user_id column already exists — skipping.")

        # Step 4: Populate supabase_user_id from mapping
        if user_mapping:
            print("\nPopulating supabase_user_id from mapping...")
            for email, supabase_uid in user_mapping.items():
                if not dry_run:
                    conn.execute(text(
                        "UPDATE account_users SET supabase_user_id = :uid WHERE email = :email"
                    ), {"uid": supabase_uid, "email": email})
                print(f"  {email} → {supabase_uid}" + ("" if not dry_run else " [would update]"))
            if not dry_run:
                session.commit()

        # Step 5: Check for users without supabase_user_id
        if not dry_run and has_supabase_id:
            result = conn.execute(text(
                "SELECT id, email FROM account_users WHERE supabase_user_id IS NULL"
            ))
            unmapped = result.fetchall()
            if unmapped:
                print(f"\nWARNING: {len(unmapped)} users have no supabase_user_id:")
                for row in unmapped:
                    print(f"  ID={row[0]}, email={row[1]}")
                print("  You must create these users in Supabase and update the mapping.")
                print("  The migration will NOT remove password_hash until all users are mapped.")
                return

        # Step 6: Remove password_hash column
        if has_password_hash:
            print("\nRemoving password_hash column from account_users...")
            if not dry_run:
                if is_sqlite:
                    # SQLite doesn't support DROP COLUMN before 3.35.0
                    # For safety, we leave the column but set all values to null
                    conn.execute(text("UPDATE account_users SET password_hash = NULL"))
                    print("  Set all password_hash values to NULL (SQLite cannot drop columns).")
                else:
                    conn.execute(text("ALTER TABLE account_users DROP COLUMN password_hash"))
                    print("  Dropped column.")
                session.commit()
            else:
                print("  [Would remove column]")

        # Step 7: Drop password_reset_tokens table
        if has_reset_tokens:
            print("\nDropping password_reset_tokens table...")
            if not dry_run:
                conn.execute(text("DROP TABLE IF EXISTS password_reset_tokens"))
                session.commit()
                print("  Dropped.")
            else:
                print("  [Would drop table]")

        print("\nMigration " + ("preview complete." if dry_run else "complete!"))

    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate auth from local DB to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--execute", action="store_true", help="Execute the migration")
    parser.add_argument("--mapping", type=str, help="JSON file mapping email → supabase_user_id")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("Please specify --dry-run or --execute")
        sys.exit(1)

    run_migration(dry_run=args.dry_run, mapping_file=args.mapping)
