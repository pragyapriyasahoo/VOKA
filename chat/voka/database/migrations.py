"""Database migration system for Voka."""

from pathlib import Path
from typing import Optional

from voka.database.postgres import PostgresDatabase


def get_current_version(db: PostgresDatabase) -> int:
    """Get the current migration version."""
    try:
        with db._require_connection().cursor() as cursor:
            cursor.execute("SELECT MAX(version) FROM schema_migrations")
            result = cursor.fetchone()
            return result["max"] if result and result["max"] is not None else 0
    except Exception:
        return 0


def run_migrations(connection_url: Optional[str] = None) -> int:
    """Run all pending migrations. Returns the final version."""
    db = PostgresDatabase(connection_url)
    try:
        db.connect()
        current = get_current_version(db)
        
        # Migration 1: Initial schema (schema.sql contains all versions)
        if current < 1:
            schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
            # Execute entire schema as single block (handles function definitions)
            with db._require_connection().cursor() as cursor:
                cursor.execute(schema)
            current = 1
        
        # Migration 2: Already included in schema.sql, just record if needed
        if current < 2:
            with db._require_connection().cursor() as cursor:
                cursor.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (2, 'Add dedup index, updated_at triggers, fix emotion confidence NOT NULL') ON CONFLICT DO NOTHING"
                )
            db.connection.commit()
            current = 2
        
        return current
    finally:
        db.close()


def get_migration_status(connection_url: Optional[str] = None) -> dict:
    """Get migration status without running migrations."""
    db = PostgresDatabase(connection_url)
    try:
        db.connect()
        current = get_current_version(db)
        with db._require_connection().cursor() as cursor:
            cursor.execute("SELECT version, applied_at, description FROM schema_migrations ORDER BY version")
            history = cursor.fetchall()
        return {"current_version": current, "history": history}
    finally:
        db.close()