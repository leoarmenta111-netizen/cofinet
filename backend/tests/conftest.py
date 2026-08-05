import os

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_HOST", "postgres")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "cofinet_test")
os.environ.setdefault("DATABASE_USER", "cofinet_test")
os.environ.setdefault("DATABASE_PASSWORD", "cofinet-test-password")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-jwt-secret-with-at-least-32-characters")
os.environ.setdefault("FRONTEND_URL", "http://localhost:8080")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:8080"]')

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import hash_password
from app.database.deps import get_db
from app.database.session import Base
from app.main import app
from app.models.admin import Admin, AdminRole
from app.models.admin_access import (  # noqa: F401
    InternalHotspotCredential,
    PinBatch,
    PinBatchFailure,
)
from app.models.membership import Membership  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.plan import Plan
from app.models.purchase import Purchase  # noqa: F401
from app.models.user import User  # noqa: F401


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def super_admin(db_session):
    admin = Admin(
        email="owner@example.com",
        full_name="Local Owner",
        password_hash=hash_password("LocalOwnerPass123!"),
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.add(
        Plan(
            name="Local Test",
            description="Local-only test plan",
            price=25,
            duration_minutes=30,
            is_active=True,
        )
    )
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture()
def super_headers(client, super_admin):
    response = client.post(
        "/admin/login",
        json={"email": super_admin.email, "password": "LocalOwnerPass123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
