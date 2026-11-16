# Campus Office Hours Booking API

A production-grade, timezone-aware REST API designed to schedule student-professor office hours without scheduling conflicts. Built with **FastAPI**, **SQLAlchemy 2.x**, **PostgreSQL**, and Python's standard library **zoneinfo** using a strict **Three-Layer Architecture** and the **Repository Pattern**.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Problem Statement & Objectives](#problem-statement--objectives)
3. [Key Features](#key-features)
4. [Technology Stack](#technology-stack)
5. [Architectural Design](#architectural-design)
   - [Strict Three-Layer Architecture](#strict-three-layer-architecture)
   - [Repository Pattern & Dependency Injection](#repository-pattern--dependency-injection)
6. [Timezone & Daylight Saving Time (DST) Handling](#timezone--daylight-saving-time-dst-handling)
   - [UTC Instant Normalization](#utc-instant-normalization)
   - [DST Spring Forward Nonexistent Time Detection](#dst-spring-forward-nonexistent-time-detection)
   - [DST Fall Back Ambiguous Time Resolution (fold=0)](#dst-fall-back-ambiguous-time-resolution-fold0)
   - [Offset Retention in Responses](#offset-retention-in-responses)
7. [Booking Overlap Prevention Formula](#booking-overlap-prevention-formula)
8. [Database Design & Schema](#database-design--schema)
9. [Project Directory Structure](#project-directory-structure)
10. [REST API Endpoints & Contracts](#rest-api-endpoints--contracts)
    - [1. Create Booking (POST /api/bookings)](#1-create-booking-post-apibookings)
    - [2. Retrieve Professor Bookings (GET /api/bookings)](#2-retrieve-professor-bookings-get-apibookings)
    - [3. Health Check (GET /health)](#3-health-check-get-health)
11. [Setup & Installation](#setup--installation)
    - [Local Development Setup](#local-development-setup)
    - [Docker Compose Deployment](#docker-compose-deployment)
12. [Environment Configuration](#environment-configuration)
13. [Test Execution & Verification](#test-execution--verification)
    - [Unit Tests with In-Memory Mock Repository](#unit-tests-with-in-memory-mock-repository)
    - [Integration Tests with TestClient & Database](#integration-tests-with-testclient--database)
    - [Full Test Suite Execution](#full-test-suite-execution)
14. [Swagger & OpenAPI Documentation](#swagger--openapi-documentation)
15. [Verification Checklist](#verification-checklist)

---

## Project Overview

In collegiate scheduling environments, students and faculty often interact across diverse timezones, online and on-campus. Booking office hours requires rigorous date/time accuracy. Naive datetime implementations fail to account for Daylight Saving Time (DST) changes, cross-timezone comparisons, and appointment overlaps. 

The **Campus Office Hours Booking API** eliminates these pitfalls by converting all submitted local appointments to UTC instants, validating overlaps in UTC space, rejecting invalid DST wall-clock times, and preserving original timezone offsets upon response formatting.

---

## Problem Statement & Objectives

### The Problem
- **Timezone Drift & Ambiguity**: Naive dates stored in SQL lose timezone context, causing silent scheduling conflicts.
- **DST Gaps & Overlaps**: Clocks jump forward in spring (skipping an hour) and fall back in autumn (repeating an hour). Applications that naively parse these datetimes produce corrupt calendar records.
- **Cross-Timezone Clashes**: An appointment at 10:00 AM Central Time (CDT) directly clashes with an appointment at 11:00 AM Eastern Time (EDT). Storing local wall times obscures this conflict.
- **Tight Coupling**: Controllers directly querying the database or services coupled to PostgreSQL break maintainability and prevent isolated unit testing.

### Objectives
1. Build a high-performance REST API with FastAPI and SQLAlchemy 2.x.
2. Store all appointment timestamps as timezone-aware UTC instants (`TIMESTAMPTZ`).
3. Reject nonexistent local times (DST Spring Forward) with HTTP 400.
4. Resolve ambiguous local times (DST Fall Back) using `fold=0` (earlier occurrence) with HTTP 201.
5. Prevent overlapping appointments for the same professor using `(startA < endB) AND (endA > startB)`.
6. Enforce strict Three-Layer Architecture: Controllers $\rightarrow$ Services $\rightarrow$ Repositories.
7. Implement pure unit tests using an in-memory `MockBookingRepository` without database dependencies.
8. Provide full Docker and Docker Compose containerization with health checks and persistence.

---

## Key Features

- **Strict Three-Layer Architecture**: Separation of Presentation, Business Logic, and Data Access layers.
- **Dual Repository Implementations**: `PostgresBookingRepository` for production and `MockBookingRepository` for in-memory testing.
- **Python Standard Library `zoneinfo`**: Zero reliance on deprecated pytz; strict adherence to PEP 495.
- **Accurate DST Handling**: Detects nonexistent spring-forward gaps and disambiguates autumn fall-backs.
- **UTC-Normalized Overlap Validation**: All interval comparisons are calculated in UTC instants.
- **ISO-8601 Offset Retention**: Returns appointment start times formatted with the professor's original timezone offset.
- **Robust Input Validation**: Validates string lengths, positive durations ($1 \le \text{duration} \le 480$), naive ISO local datetimes, and valid IANA timezone identifiers.
- **Containerization**: Multi-stage Dockerfile and Docker Compose with health checks and auto-schema initialization.

---

## Technology Stack

| Layer / Concern | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | 3.11+ / 3.10 | Core execution environment |
| **Web Framework** | FastAPI | 0.115.6 | Async REST API presentation layer |
| **Validation** | Pydantic v2 | 2.10.4 | Request/response DTO schemas and validation |
| **ASGI Server** | Uvicorn | 0.34.0 | High-performance ASGI HTTP server |
| **ORM / Data Access** | SQLAlchemy | 2.0.36 | Database abstraction and query generation |
| **DB Driver** | psycopg 3 | 3.3.9 | PostgreSQL client driver with binary extensions |
| **Database** | PostgreSQL | 15-alpine | Relational database with TIMESTAMPTZ support |
| **Timezone Database** | Python zoneinfo + tzdata | 2024.2 | Official IANA timezone database |
| **Unit & Integration Testing** | Pytest + HTTPX | 8.3.4 / 0.28.1 | Automated test runner and HTTP test client |
| **Containerization** | Docker & Docker Compose | Spec v2+ | Multi-container orchestration |

---

## Architectural Design

### Strict Three-Layer Architecture

```
┌────────────────────────────────────────────────────────┐
│               1. Presentation Layer                    │
│   app/controllers/booking_controller.py                │
│   - Receives HTTP requests                             │
│   - Validates DTOs (BookingCreateRequest)              │
│   - Calls BookingService via Dependency Injection      │
│   - Maps domain exceptions to HTTP status codes        │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│               2. Business Logic Layer                  │
│   app/services/booking_service.py                      │
│   - Validates duration (1 - 480 minutes)               │
│   - Detects nonexistent DST times (Spring Forward)     │
│   - Resolves ambiguous DST times (Fall Back, fold=0)   │
│   - Converts naive local times to UTC instants         │
│   - Enforces booking overlap prevention rules          │
│   - Depends ONLY on IBookingRepository interface       │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│               3. Data Access Layer                     │
│   app/repositories/                                    │
│   - IBookingRepository (Abstract Interface)           │
│   ├─ PostgresBookingRepository (SQLAlchemy 2.x)        │
│   └─ MockBookingRepository (In-Memory List)            │
└────────────────────────────────────────────────────────┘
```

#### Rules Enforced:
1. Controllers never execute database queries directly.
2. Services never import or instantiate `PostgresBookingRepository`.
3. Repositories implement the abstract `IBookingRepository` contract.
4. Database sessions are managed outside the service layer.

---

### Repository Pattern & Dependency Injection

The `IBookingRepository` abstract base class defines the storage contract:

```python
class IBookingRepository(ABC):
    @abstractmethod
    def save(self, booking: Booking) -> Booking:
        pass

    @abstractmethod
    def find_overlapping(self, professor_id: str, start_utc: datetime, end_utc: datetime) -> List[Booking]:
        pass

    @abstractmethod
    def find_by_professor(self, professor_id: str) -> List[Booking]:
        pass
```

- **`PostgresBookingRepository`**: Executes SQLAlchemy queries using PostgreSQL intervals (`starts_at_utc + duration_minutes * INTERVAL '1 minute' > :start_utc`).
- **`MockBookingRepository`**: Uses an in-memory Python `list[Booking]` and sequential IDs. Implements identical overlap semantics without requiring a database.
- **Dependency Injection**: In `app/controllers/booking_controller.py`, `get_booking_service` injects the repository into `BookingService`:
  ```python
  def get_booking_service(session: Session = Depends(get_db)) -> BookingService:
      return BookingService(PostgresBookingRepository(session))
  ```

---

## Timezone & Daylight Saving Time (DST) Handling

All timezone operations are implemented in `app/utils/timezone_utils.py` using Python's built-in `zoneinfo` module and PEP 495 semantics.

### UTC Instant Normalization
Incoming booking requests provide:
- `local_start_time`: Naive ISO-8601 string (e.g. `2024-10-15T10:00:00`). Offsets or `Z` suffixes are strictly rejected.
- `timezone`: Valid IANA identifier (e.g. `America/Chicago`).

The naive datetime is converted into an aware UTC instant and persisted to PostgreSQL as `TIMESTAMPTZ`.

### DST Spring Forward Nonexistent Time Detection
When clocks "spring forward", one hour of wall-clock time does not exist.
- **Example**: In `America/New_York` on `2024-03-10`, clocks jump from `01:59:59` to `03:00:00`. The time `02:30:00` does not exist.
- **Detection Logic**:
  ```python
  f0 = local_dt.replace(tzinfo=tz, fold=0)
  f1 = local_dt.replace(tzinfo=tz, fold=1)
  f0_rt = f0.astimezone(UTC).astimezone(tz).replace(tzinfo=None)
  f1_rt = f1.astimezone(UTC).astimezone(tz).replace(tzinfo=None)
  if f0_rt != local_dt and f1_rt != local_dt:
      raise NonexistentLocalTimeError("Invalid local time: this time does not exist due to a daylight saving time transition.")
  ```
- **Outcome**: The booking is rejected with **HTTP 400 Bad Request**.

### DST Fall Back Ambiguous Time Resolution (fold=0)
When clocks "fall back", one hour repeats.
- **Example**: In `America/New_York` on `2024-11-03`, `01:30:00` occurs twice:
  - First occurrence (EDT, UTC-4): `fold=0` $\rightarrow$ `05:30:00 UTC`
  - Second occurrence (EST, UTC-5): `fold=1` $\rightarrow$ `06:30:00 UTC`
- **Resolution**: The system explicitly selects `fold=0` (the earlier occurrence).
- **Outcome**: The booking is accepted with **HTTP 201 Created**, converted to `05:30:00 UTC`, and returned with offset `-04:00`.

### Offset Retention in Responses
When retrieving bookings or returning creation responses, the UTC instant is converted back to the booking's `original_timezone`:
```python
local_dt = utc_dt.astimezone(zoneinfo.ZoneInfo(original_timezone))
return local_dt.isoformat()  # e.g. "2024-10-15T10:00:00-05:00"
```

---

## Booking Overlap Prevention Formula

To determine whether an appointment overlaps with an existing booking for the same professor, the system applies the interval formula exclusively on UTC instants:

$$\text{Overlap} \iff (\text{start}_A < \text{end}_B) \land (\text{end}_A > \text{start}_B)$$

Where:
$$\text{end} = \text{start} + \text{duration\_minutes}$$

### Overlap Scenarios
| Existing Booking | Requested Booking | Start Comparison | End Comparison | Result |
| :--- | :--- | :--- | :--- | :--- |
| 10:00 - 10:30 UTC | 10:15 - 10:45 UTC | $10:00 < 10:45$ (True) | $10:30 > 10:15$ (True) | **Overlap (HTTP 409)** |
| 10:00 - 10:30 UTC | 10:30 - 11:00 UTC | $10:00 < 11:00$ (True) | $10:30 > 10:30$ (False) | **Adjacent (HTTP 201)** |
| 10:00 - 10:30 UTC (Prof 1) | 10:00 - 10:30 UTC (Prof 2) | Different professors | N/A | **Allowed (HTTP 201)** |

Cross-timezone bookings are normalized to UTC before this check, guaranteeing that local timezone variations never cause false negatives.

---

## Database Design & Schema

### PostgreSQL Table: `office_hour_bookings`

```sql
CREATE TABLE IF NOT EXISTS office_hour_bookings (
    id SERIAL PRIMARY KEY,
    professor_id VARCHAR(255) NOT NULL,
    student_id VARCHAR(255) NOT NULL,
    starts_at_utc TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER NOT NULL,
    original_timezone VARCHAR(100) NOT NULL,
    CONSTRAINT chk_positive_duration CHECK (duration_minutes > 0)
);

CREATE INDEX IF NOT EXISTS idx_office_hour_bookings_professor_id ON office_hour_bookings(professor_id);
CREATE INDEX IF NOT EXISTS idx_office_hour_bookings_starts_at_utc ON office_hour_bookings(starts_at_utc);
```

### Constraints & Rules
- `id`: Auto-incrementing primary key.
- `starts_at_utc`: Timezone-aware UTC timestamp (`TIMESTAMPTZ`). Naive datetimes are rejected before persistence.
- `original_timezone`: Stores the IANA identifier (e.g. `America/Chicago`).
- `duration_minutes`: Positive integer ($1 \le \text{duration} \le 480$).
- Indexes on `professor_id` and `starts_at_utc` ensure high-performance overlap queries and filtering.

---

## Project Directory Structure

```
campus-office-hours-api/
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application entrypoint & exception handlers
│   ├── config.py                   # Pydantic Settings configuration
│   ├── database.py                 # SQLAlchemy 2.x engine, sessionmaker & init_db
│   ├── entities/
│   │   ├── __init__.py
│   │   └── booking.py              # Domain Booking entity & SQLAlchemy BookingModel
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── booking_schema.py       # Pydantic request & response validation schemas
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── booking_repository.py          # Abstract IBookingRepository interface
│   │   ├── postgres_booking_repository.py # PostgreSQL SQLAlchemy implementation
│   │   └── mock_booking_repository.py     # In-memory mock repository implementation
│   ├── services/
│   │   ├── __init__.py
│   │   └── booking_service.py      # Business logic, overlap validation & DST resolution
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── booking_controller.py   # FastAPI HTTP routes & dependency injection
│   ├── utils/
│   │   ├── __init__.py
│   │   └── timezone_utils.py       # IANA validation, PEP 495 fold=0 & ISO formatting
│   └── exceptions/
│       ├── __init__.py
│       └── booking_exceptions.py   # Domain exceptions hierarchy
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_booking_service.py # Pure unit tests with MockBookingRepository
│   └── integration/
│       ├── __init__.py
│       └── test_booking_api.py     # HTTP integration tests against FastAPI & DB
│
├── migrations/
│   └── init.sql                    # PostgreSQL DDL table, index & constraint script
│
├── .env.example                    # Environment variable template
├── .gitignore                      # Git ignore configuration
├── Dockerfile                      # Production Docker container image
├── docker-compose.yml              # Multi-container orchestration (db + api)
├── requirements.txt                # Pinned dependencies
├── pytest.ini                      # Pytest runner configuration
├── README.md                       # Comprehensive project documentation
└── VERIFY.md                       # Evaluation criteria and verification runbook
```

---

## REST API Endpoints & Contracts

### 1. Create Booking (POST /api/bookings)
Creates a new appointment with timezone conversion and overlap validation.

- **URL**: `POST /api/bookings`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "professor_id": "PROF001",
    "student_id": "STU001",
    "local_start_time": "2024-10-15T10:00:00",
    "timezone": "America/Chicago",
    "duration_minutes": 30
  }
  ```
- **Responses**:
  - `201 Created`:
    ```json
    {
      "id": 1,
      "professor_id": "PROF001",
      "student_id": "STU001",
      "starts_at": "2024-10-15T10:00:00-05:00",
      "duration_minutes": 30
    }
    ```
  - `400 Bad Request` (Invalid timezone, nonexistent DST time, or invalid format):
    ```json
    {
      "detail": "Invalid local time: this time does not exist due to a daylight saving time transition."
    }
    ```
  - `409 Conflict` (Overlapping appointment):
    ```json
    {
      "detail": "Requested booking overlaps with an existing appointment for professor PROF001."
    }
    ```

---

### 2. Retrieve Professor Bookings (GET /api/bookings)
Retrieves all appointments scheduled for a specific professor.

- **URL**: `GET /api/bookings?professor_id=PROF001`
- **Responses**:
  - `200 OK`:
    ```json
    [
      {
        "id": 1,
        "professor_id": "PROF001",
        "student_id": "STU001",
        "starts_at": "2024-10-15T10:00:00-05:00",
        "duration_minutes": 30
      }
    ]
    ```
  - `200 OK` (No bookings):
    ```json
    []
    ```
  - `400 Bad Request` (Missing `professor_id`):
    ```json
    {
      "detail": "Validation error at 'query -> professor_id': Field required"
    }
    ```

---

### 3. Health Check (GET /health)
Used by container orchestrators and monitoring tools to verify API liveness.

- **URL**: `GET /health`
- **Response**:
  - `200 OK`:
    ```json
    {
      "status": "healthy"
    }
    ```

---

## Setup & Installation

### Local Development Setup

1. **Clone or navigate to the project directory**:
   ```bash
   cd campus-office-hours-api
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

5. **Start the API locally**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

### Docker Compose Deployment

The application and PostgreSQL database can be started in detached mode with a single command:

```bash
docker compose up --build -d
```

### Compose Lifecycle:
1. Spawns `campus_bookings_db` (PostgreSQL 15 Alpine).
2. Executes `migrations/init.sql` to initialize tables, constraints, and indices.
3. Waits for `campus_bookings_db` to pass its health check (`pg_isready`).
4. Builds and starts `campus_bookings_api` (FastAPI).
5. Runs the API health check against `http://localhost:8000/health`.

To stop services:
```bash
docker compose down
```

To stop services and remove volumes:
```bash
docker compose down -v
```

---

## Environment Configuration

Configure variables via `.env` file (copied from `.env.example`):

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `change_me` | PostgreSQL password |
| `POSTGRES_DB` | `campus_bookings` | PostgreSQL database name |
| `POSTGRES_HOST` | `db` | Database host (`db` in Docker, `localhost` for local Postgres) |
| `POSTGRES_PORT` | `5432` | Database port |
| `DATABASE_URL` | `postgresql+psycopg://...` | Full SQLAlchemy database connection string |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API exposed port |
| `APP_ENV` | `development` | Environment mode (`development`, `production`, `testing`) |

---

## Test Execution & Verification

### Unit Tests with In-Memory Mock Repository
Runs completely isolated from PostgreSQL and Docker:

```bash
pytest tests/unit/test_booking_service.py -v
```

**Test Coverage (20 unit tests):**
- Successful booking creation.
- Invalid duration rejection (0, -15, -1, 481, 1000 minutes).
- Overlapping booking rejection (HTTP 409).
- Adjacent booking acceptance (HTTP 201).
- Different professor simultaneous booking acceptance.
- Chronological retrieval of professor bookings.
- Invalid IANA timezone rejection.
- DST Spring Forward nonexistent time rejection (`America/New_York` `2024-03-10 02:30:00`).
- DST Fall Back ambiguous time resolution with `fold=0` (`America/New_York` `2024-11-03 01:30:00` returning `-04:00`).
- Accurate UTC conversion without naive datetimes.
- Cross-timezone overlap detection across different offsets.
- Empty booking list when professor has no appointments.

---

### Integration Tests with TestClient & Database
Tests FastAPI HTTP endpoints, payload validation, and database operations:

```bash
pytest tests/integration/test_booking_api.py -v
```

**Test Coverage (12 integration tests):**
- `GET /health` returns 200 `{"status": "healthy"}`.
- `POST /api/bookings` returns 201 with correct offset.
- `GET /api/bookings?professor_id=...` returns 200 list.
- Overlapping booking returns HTTP 409 Conflict.
- Nonexistent DST spring forward returns HTTP 400 with detail message.
- Invalid IANA timezone returns HTTP 400.
- Adjacent booking returns HTTP 201.
- Different professor booking returns HTTP 201.
- Cross-timezone overlap returns HTTP 409.
- Fall back ambiguous time returns HTTP 201 with `-04:00` offset.
- Unknown professor returns empty array `[]`.
- Non-naive start time (with `Z` or embedded offset) returns HTTP 400.

---

### Full Test Suite Execution

```bash
pytest -v
```

**Execution Result:**
```
============================= 32 passed in 4.92s ==============================
```

---

## Swagger & OpenAPI Documentation

When the application is running, interactive API documentation is available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON)**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Verification Checklist

| Criterion | Implementation | Verified Status |
| :--- | :--- | :---: |
| **Strict 3-Layer Architecture** | `controllers/`, `services/`, `repositories/` | PASSED |
| **Repository Pattern** | `IBookingRepository`, `PostgresBookingRepository`, `MockBookingRepository` | PASSED |
| **Constructor Dependency Injection** | `BookingService(IBookingRepository)` | PASSED |
| **Pure Unit Tests (No DB)** | `tests/unit/test_booking_service.py` using `MockBookingRepository` | PASSED (20/20) |
| **Timezone-Aware UTC Instants** | Persisted as `TIMESTAMPTZ`, zero naive datetimes | PASSED |
| **DST Spring Forward Rejection** | Returns HTTP 400 with explicit detail message | PASSED |
| **DST Fall Back Resolution** | Uses `fold=0`, returns `-04:00` offset | PASSED |
| **Offset Preservation** | Responses formatted with original timezone offset | PASSED |
| **Overlap Detection** | `(startA < endB) AND (endA > startB)` in UTC space | PASSED |
| **Cross-Timezone Overlaps** | Detected accurately across different local timezones | PASSED |
| **Adjacent Bookings Allowed** | Accepted with HTTP 201 | PASSED |
| **PostgreSQL Persistence** | DDL migration script + SQLAlchemy 2.0 ORM | PASSED |
| **Docker Compose** | Multi-container setup with db healthcheck and volume | PASSED |
| **Integration Test Suite** | `tests/integration/test_booking_api.py` | PASSED (12/12) |
