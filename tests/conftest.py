import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.config import settings
from app.core.database import get_db


def _create_test_database():
    """Create test database if it doesn't exist."""
    default_url = settings.DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    engine = create_engine(default_url)
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))
        # Drop if exists to get clean state
        conn.execute(text("DROP DATABASE IF EXISTS org_structure_test"))
        # Use template0 to avoid picking up alembic_version from template1
        conn.execute(text("CREATE DATABASE org_structure_test TEMPLATE template0"))
    engine.dispose()


def _get_test_db_url():
    base = settings.DATABASE_URL.rsplit("/", 1)[0]
    return f"{base}/org_structure_test"


def _run_migrations():
    """Run Alembic migrations on test database."""
    from alembic.config import Config
    from alembic import command

    test_url = _get_test_db_url()
    os.environ["DATABASE_URL"] = test_url

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_url)
    command.upgrade(alembic_cfg, "head")


def _truncate_tables(engine):
    """Truncate all tables between tests."""
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE employees, departments RESTART IDENTITY CASCADE"))
        conn.commit()


@pytest.fixture(scope="session")
def engine():
    """Create test database and run migrations once per test session."""
    _create_test_database()
    _run_migrations()

    test_url = _get_test_db_url()
    test_engine = create_engine(test_url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    """Provide a clean database session for each test."""
    _truncate_tables(engine)

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session):
    """Test client with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()