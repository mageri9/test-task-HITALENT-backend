import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.config import settings
from app.core.database import get_db
from app.models import Base


TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.DATABASE_URL.rsplit("/", 1)[-1],
    "org_structure_test",
)


def _create_test_database():
    """Create test database if it doesn't exist."""
    default_url = settings.DATABASE_URL.rstrip("/", 1)[0] + "/org_structure"
    engine = create_engine(default_url)
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))
        conn.execute(text("CREATE DATABASE org_structure_test"))
    engine.dispose()

def _run_migrations():
    """Run Alembic migrations on test database."""
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")

def _truncate_tables(engine):
    """Truncate all tables between tests."""
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE employee, departments RESTART IDENTITY CASCADE"))
        conn.commit()


@pytest.fixture(scope="session")
def engine():
    """Create test database and run migrations once per test session."""
    try:
        _create_test_database()
    except Exception:
        pass    # Database already exists

    _run_migrations()

    test_engine = create_engine(TEST_DATABASE_URL)
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