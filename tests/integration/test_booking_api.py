"""Integration tests verifying HTTP endpoints, validation, and database persistence."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Configure test environment
settings.APP_ENV = "testing"

test_db_url = os.getenv("TEST_DATABASE_URL")
if not test_db_url:
    # Attempt connecting to configured Postgres; if unreachable, fallback to SQLite
    try:
        candidate_engine = create_engine(
            settings.effective_database_url,
            connect_args={"connect_timeout": 1},
        )
        with candidate_engine.connect() as conn:
            test_db_url = settings.effective_database_url
    except Exception:
        test_db_url = "sqlite:///./test_integration.db"

test_engine = create_engine(
    test_db_url,
    connect_args={"check_same_thread": False} if test_db_url.startswith("sqlite") else {},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from app.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables in the test database once per session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if "sqlite" in test_db_url and os.path.exists("./test_integration.db"):
        try:
            os.remove("./test_integration.db")
        except OSError:
            pass


@pytest.fixture
def db_session():
    """Provide a clean transactional session for each integration test."""
    session = TestingSessionLocal()
    # Clean tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Provide TestClient with get_db overridden to use test session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_check_endpoint(client: TestClient):
    """Verify GET /health returns 200 OK with status healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_post_booking_success(client: TestClient):
    """Verify POST /api/bookings successfully creates a booking and returns 201 Created."""
    payload = {
        "professor_id": "PROF001",
        "student_id": "STU001",
        "local_start_time": "2024-10-15T10:00:00",
        "timezone": "America/Chicago",
        "duration_minutes": 30,
    }
    response = client.post("/api/bookings", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] is not None
    assert data["professor_id"] == "PROF001"
    assert data["student_id"] == "STU001"
    assert data["duration_minutes"] == 30
    # America/Chicago in October is CDT (-05:00)
    assert data["starts_at"] == "2024-10-15T10:00:00-05:00"


def test_get_bookings_success(client: TestClient):
    """Verify GET /api/bookings returns all bookings for a given professor."""
    payload = {
        "professor_id": "PROF001",
        "student_id": "STU001",
        "local_start_time": "2024-10-15T10:00:00",
        "timezone": "America/Chicago",
        "duration_minutes": 30,
    }
    client.post("/api/bookings", json=payload)

    response = client.get("/api/bookings?professor_id=PROF001")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["professor_id"] == "PROF001"
    assert data[0]["starts_at"] == "2024-10-15T10:00:00-05:00"


def test_http_409_overlap_conflict(client: TestClient):
    """Verify POST /api/bookings returns 409 Conflict when an appointment overlaps with existing one."""
    # First booking: 10:00 - 10:30 UTC
    b1_payload = {
        "professor_id": "PROF001",
        "student_id": "STU001",
        "local_start_time": "2024-10-15T10:00:00",
        "timezone": "UTC",
        "duration_minutes": 30,
    }
    resp1 = client.post("/api/bookings", json=b1_payload)
    assert resp1.status_code == 201

    # Overlapping booking: 10:15 - 10:45 UTC
    b2_payload = {
        "professor_id": "PROF001",
        "student_id": "STU002",
        "local_start_time": "2024-10-15T10:15:00",
        "timezone": "UTC",
        "duration_minutes": 30,
    }
    resp2 = client.post("/api/bookings", json=b2_payload)
    assert resp2.status_code == 409
    assert "overlaps" in resp2.json()["detail"].lower()


def test_http_400_invalid_dst_spring_forward(client: TestClient):
    """Verify POST /api/bookings returns 400 Bad Request for nonexistent DST Spring Forward time."""
    payload = {
        "professor_id": "PROF001",
        "student_id": "STU001",
        "local_start_time": "2024-03-10T02:30:00",
        "timezone": "America/New_York",
        "duration_minutes": 30,
    }
    response = client.post("/api/bookings", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid local time: this time does not exist due to a daylight saving time transition."
    )


def test_http_400_invalid_timezone(client: TestClient):
    """Verify POST /api/bookings returns 400 Bad Request for invalid IANA timezone."""
    payload = {
        "professor_id": "PROF001",
        "student_id": "STU001",
        "local_start_time": "2024-10-15T10:00:00",
        "timezone": "Invalid/Unknown_Zone",
        "duration_minutes": 30,
    }
    response = client.post("/api/bookings", json=payload)
    assert response.status_code == 400


def test_http_201_adjacent_booking(client: TestClient):
    """Verify adjacent appointments are accepted and return 201 Created."""
    # Booking A: 10:00 - 10:30 UTC
    resp1 = client.post(
        "/api/bookings",
        json={
            "professor_id": "PROF001",
            "student_id": "STU001",
            "local_start_time": "2024-10-15T10:00:00",
            "timezone": "UTC",
            "duration_minutes": 30,
        },
    )
    assert resp1.status_code == 201

    # Booking B: 10:30 - 11:00 UTC (Immediately adjacent)
    resp2 = client.post(
        "/api/bookings",
        json={
            "professor_id": "PROF001",
            "student_id": "STU002",
            "local_start_time": "2024-10-15T10:30:00",
            "timezone": "UTC",
            "duration_minutes": 30,
        },
    )
    assert resp2.status_code == 201


def test_http_201_booking_for_different_professor(client: TestClient):
    """Verify concurrent bookings for different professors are permitted and return 201 Created."""
    resp1 = client.post(
        "/api/bookings",
        json={
            "professor_id": "PROF001",
            "student_id": "STU001",
            "local_start_time": "2024-10-15T10:00:00",
            "timezone": "America/Chicago",
            "duration_minutes": 30,
        },
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        "/api/bookings",
        json={
            "professor_id": "PROF002",
            "student_id": "STU002",
            "local_start_time": "2024-10-15T10:00:00",
            "timezone": "America/Chicago",
            "duration_minutes": 30,
        },
    )
    assert resp2.status_code == 201


def test_cross_timezone_overlap_detection(client: TestClient):
    """Verify overlapping appointments submitted in different local timezones are detected in UTC."""
    # Booking 1: 14:00 - 15:00 America/Chicago (CDT, UTC-5) -> 19:00 - 20:00 UTC
    resp1 = client.post(
        "/api/bookings",
        json={
            "professor_id": "PROF001",
            "student_id": "STU001",
            "local_start_time": "2024-10-15T14:00:00",
            "timezone": "America/Chicago",
            "duration_minutes": 60,
        },
    )
    assert resp1.status_code == 201

    # Booking 2: 15:30 - 16:00 America/New_York (EDT, UTC-4) -> 19:30 - 20:00 UTC (overlaps!)
    resp2 = client.post(
        "/api/bookings",
        json={
            "professor_id": "PROF001",
            "student_id": "STU002",
            "local_start_time": "2024-10-15T15:30:00",
            "timezone": "America/New_York",
            "duration_minutes": 30,
        },
    )
    assert resp2.status_code == 409


def test_correct_offset_in_response_and_dst_fall_back(client: TestClient):
    """Verify that ambiguous time on DST Fall Back is accepted with fold=0 and returns -04:00 offset."""
    # 2024-11-03 01:30:00 in America/New_York (first occurrence is EDT -04:00)
    response = client.post(
        "/api/bookings",
        json={
            "professor_id": "PROF001",
            "student_id": "STU001",
            "local_start_time": "2024-11-03T01:30:00",
            "timezone": "America/New_York",
            "duration_minutes": 30,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["starts_at"] == "2024-11-03T01:30:00-04:00"


def test_empty_professor_bookings(client: TestClient):
    """Verify GET /api/bookings returns empty list when professor has no bookings."""
    response = client.get("/api/bookings?professor_id=UNKNOWN_PROF")
    assert response.status_code == 200
    assert response.json() == []


def test_local_time_with_offset_rejected(client: TestClient):
    """Verify that non-naive local_start_time (containing Z or offset) is rejected with 400 Bad Request."""
    response = client.post(
        "/api/bookings",
        json={
            "professor_id": "PROF001",
            "student_id": "STU001",
            "local_start_time": "2024-10-15T10:00:00Z",
            "timezone": "America/Chicago",
            "duration_minutes": 30,
        },
    )
    assert response.status_code == 400
