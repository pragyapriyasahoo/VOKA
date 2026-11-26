"""Test fixtures and configuration for Voka."""

import uuid

import pytest

from voka.database.postgres import PostgresDatabase
from voka.database.repositories import PersistenceService


# Use parameter-based connection to avoid URL parsing issues with @ in password
TEST_DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "voka_test",
    "user": "postgres",
    "password": "Anant@1174",
}
LOCAL_USER_ID = uuid.uuid5(uuid.NAMESPACE_URL, "voka:default-local-user")


class TestPostgresDatabase(PostgresDatabase):
    """Test-specific PostgresDatabase that uses parameter-based connection."""
    
    def connect(self):
        import psycopg
        from psycopg.rows import dict_row
        
        self.connection = psycopg.connect(**TEST_DB_PARAMS, row_factory=dict_row)
        return self


@pytest.fixture(scope="session")
def test_db():
    """Create a test database connection and run migrations."""
    db = TestPostgresDatabase()
    db.connect()
    db.create_schema()
    yield db
    # Don't close here - let pytest handle it at session end
    db.close()


@pytest.fixture
def clean_test_db(test_db):
    """Clean all test data before each test."""
    # Ensure connection is alive
    if test_db.connection is None or test_db.connection.closed:
        test_db.connect()
    
    with test_db._require_connection().cursor() as cur:
        # Delete in reverse dependency order
        cur.execute("DELETE FROM emotion_events")
        cur.execute("DELETE FROM memories")
        cur.execute("DELETE FROM messages")
        cur.execute("DELETE FROM conversations")
        cur.execute("DELETE FROM users")
        cur.execute("DELETE FROM characters")
    test_db.connection.commit()
    
    # Recreate default characters
    for name in ["Manya", "Umesh", "Prabhat", "Prakriti", "Advit"]:
        test_db.create_character(name)
    test_db.create_user(LOCAL_USER_ID)
    test_db.connection.commit()
    
    yield test_db


@pytest.fixture
def persistence(clean_test_db):
    """Create a PersistenceService with test database."""
    service = PersistenceService(clean_test_db, require_postgres=True)
    yield service
    service.close()


@pytest.fixture
def sample_conversation(persistence):
    """Create a sample conversation session."""
    session = persistence.start_session("Manya")
    yield session
    persistence.close()