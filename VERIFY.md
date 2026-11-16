# VERIFY.md - Verification Guide & Evaluation Report

This runbook documents the verification checklist, exact commands, and execution results for the **Campus Office Hours Booking API**.

---

## Evaluation Summary Table

| Requirement ID | Evaluation Criterion | Implementation Details | Verified Result |
| :--- | :--- | :--- | :---: |
| **REQ-01** | Strict Three-Layer Architecture | Separation into `app/controllers`, `app/services`, and `app/repositories` | **VERIFIED** |
| **REQ-02** | Repository Pattern | Abstract interface `IBookingRepository`, `PostgresBookingRepository`, `MockBookingRepository` | **VERIFIED** |
| **REQ-03** | Constructor Dependency Injection | `BookingService.__init__(repository: IBookingRepository)` | **VERIFIED** |
| **REQ-04** | In-Memory Mock Repository | `MockBookingRepository` operates with zero database dependencies | **VERIFIED** |
| **REQ-05** | PostgreSQL Database Schema | Table `office_hour_bookings` with indices & `CHECK (duration_minutes > 0)` | **VERIFIED** |
| **REQ-06** | UTC Normalization | Timestamps stored as timezone-aware UTC instants (`TIMESTAMPTZ`) | **VERIFIED** |
| **REQ-07** | DST Spring Forward Rejection | Nonexistent local times rejected with HTTP 400 | **VERIFIED** |
| **REQ-08** | DST Fall Back Handling | Ambiguous local times resolved with `fold=0` (returning `-04:00` offset) | **VERIFIED** |
| **REQ-09** | Offset Retention | Response returns original timezone offset (e.g. `2024-10-15T10:00:00-05:00`) | **VERIFIED** |
| **REQ-10** | Overlap Detection | Strict formula `(startA < endB) AND (endA > startB)` in UTC space | **VERIFIED** |
| **REQ-11** | Cross-Timezone Overlaps | Rejects conflicting bookings across timezones (e.g. CDT vs EDT) | **VERIFIED** |
| **REQ-12** | Adjacent Bookings Accepted | Consecutive appointments on boundaries return HTTP 201 | **VERIFIED** |
| **REQ-13** | Concurrent Professors | Simultaneous appointments for different professors return HTTP 201 | **VERIFIED** |
| **REQ-14** | REST Endpoints Implemented | `POST /api/bookings`, `GET /api/bookings?professor_id=...`, `GET /health` | **VERIFIED** |
| **REQ-15** | Unit Test Suite (20 tests) | Runs pure in-memory mock repository tests without PostgreSQL | **VERIFIED (20/20 PASS)** |
| **REQ-16** | Integration Test Suite (12 tests) | Executes HTTP requests and verifies database persistence | **VERIFIED (12/12 PASS)** |
| **REQ-17** | Total Test Suite (32 tests) | Full test execution via `pytest -v` | **VERIFIED (32/32 PASS)** |
| **REQ-18** | Docker & Docker Compose | Multi-container configuration with health checks & persistent volume | **VERIFIED (Config Valid)** |
| **REQ-19** | Zero Hardcoded Secrets | Secrets managed via `.env.example`, `.env` added to `.gitignore` | **VERIFIED** |

---

## Automated Test Execution

### 1. Unit Tests (Isolated from PostgreSQL and Docker)
```bash
pytest tests/unit/test_booking_service.py -v
```

**Actual Output:**
```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-8.3.4, pluggy-1.6.0
rootdir: C:\Users\MY PC\Desktop\Global-Tasks\Campus Office Hours Booking API
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.8.0, asyncio-0.25.0, cov-6.0.0
asyncio: mode=auto, asyncio_default_fixture_loop_scope=function
collected 20 items

tests/unit/test_booking_service.py::test_successful_booking_creation PASSED [  5%]
tests/unit/test_booking_service.py::test_invalid_duration_rejection[0] PASSED [ 10%]
tests/unit/test_booking_service.py::test_invalid_duration_rejection[-15] PASSED [ 15%]
tests/unit/test_booking_service.py::test_invalid_duration_rejection[-1] PASSED [ 20%]
tests/unit/test_booking_service.py::test_invalid_duration_rejection[481] PASSED [ 25%]
tests/unit/test_booking_service.py::test_invalid_duration_rejection[1000] PASSED [ 30%]
tests/unit/test_booking_service.py::test_overlapping_booking_rejection PASSED [ 35%]
tests/unit/test_booking_service.py::test_adjacent_booking_acceptance PASSED [ 40%]
tests/unit/test_booking_service.py::test_different_professor_booking_acceptance PASSED [ 45%]
tests/unit/test_booking_service.py::test_retrieval_of_professor_bookings PASSED [ 50%]
tests/unit/test_booking_service.py::test_invalid_iana_timezone_rejection[Mars/Phobos] PASSED [ 55%]
tests/unit/test_booking_service.py::test_invalid_iana_timezone_rejection[Invalid_Zone] PASSED [ 60%]
tests/unit/test_booking_service.py::test_invalid_iana_timezone_rejection[GMT+99] PASSED [ 65%]
tests/unit/test_booking_service.py::test_invalid_iana_timezone_rejection[] PASSED [ 70%]
tests/unit/test_booking_service.py::test_invalid_iana_timezone_rejection[   ] PASSED [ 75%]
tests/unit/test_booking_service.py::test_dst_spring_forward_rejection PASSED [ 80%]
tests/unit/test_booking_service.py::test_dst_fall_back_acceptance_with_fold0 PASSED [ 85%]
tests/unit/test_booking_service.py::test_timezone_aware_conversion_to_utc PASSED [ 90%]
tests/unit/test_booking_service.py::test_cross_timezone_overlap_rejection PASSED [ 95%]
tests/unit/test_booking_service.py::test_empty_professor_booking_list PASSED [100%]

============================= 20 passed in 0.81s ==============================
```

---

### 2. Integration Tests (FastAPI Endpoints & Database Persistence)
```bash
pytest tests/integration/test_booking_api.py -v
```

**Actual Output:**
```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-8.3.4, pluggy-1.6.0
rootdir: C:\Users\MY PC\Desktop\Global-Tasks\Campus Office Hours Booking API
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.8.0, asyncio-0.25.0, cov-6.0.0
asyncio: mode=auto, asyncio_default_fixture_loop_scope=function
collected 12 items

tests/integration/test_booking_api.py::test_health_check_endpoint PASSED [  8%]
tests/integration/test_booking_api.py::test_post_booking_success PASSED  [ 16%]
tests/integration/test_booking_api.py::test_get_bookings_success PASSED  [ 25%]
tests/integration/test_booking_api.py::test_http_409_overlap_conflict PASSED [ 33%]
tests/integration/test_booking_api.py::test_http_400_invalid_dst_spring_forward PASSED [ 41%]
tests/integration/test_booking_api.py::test_http_400_invalid_timezone PASSED [ 50%]
tests/integration/test_booking_api.py::test_http_201_adjacent_booking PASSED [ 58%]
tests/integration/test_booking_api.py::test_http_201_booking_for_different_professor PASSED [ 66%]
tests/integration/test_booking_api.py::test_cross_timezone_overlap_detection PASSED [ 75%]
tests/integration/test_booking_api.py::test_correct_offset_in_response_and_dst_fall_back PASSED [ 83%]
tests/integration/test_booking_api.py::test_empty_professor_bookings PASSED [ 91%]
tests/integration/test_booking_api.py::test_local_time_with_offset_rejected PASSED [100%]

============================= 12 passed in 5.03s ==============================
```

---

### 3. Full Test Suite Execution
```bash
pytest -v
```

**Actual Output:**
```
============================= 32 passed in 4.92s ==============================
```

---

## Manual Verification Steps & Curl Commands

### 1. Verify Health Endpoint
```bash
curl -X GET http://localhost:8000/health
```
**Expected Response:**
```json
{
  "status": "healthy"
}
```

---

### 2. Verify Successful Booking (201 Created)
```bash
curl -X POST http://localhost:8000/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "professor_id": "PROF001",
    "student_id": "STU001",
    "local_start_time": "2024-10-15T10:00:00",
    "timezone": "America/Chicago",
    "duration_minutes": 30
  }'
```
**Expected Response:**
```json
{
  "id": 1,
  "professor_id": "PROF001",
  "student_id": "STU001",
  "starts_at": "2024-10-15T10:00:00-05:00",
  "duration_minutes": 30
}
```

---

### 3. Verify Overlap Conflict (409 Conflict)
```bash
curl -X POST http://localhost:8000/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "professor_id": "PROF001",
    "student_id": "STU002",
    "local_start_time": "2024-10-15T10:15:00",
    "timezone": "America/Chicago",
    "duration_minutes": 30
  }'
```
**Expected Response:**
```json
{
  "detail": "Requested booking overlaps with an existing appointment for professor PROF001."
}
```

---

### 4. Verify Adjacent Booking Allowed (201 Created)
```bash
curl -X POST http://localhost:8000/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "professor_id": "PROF001",
    "student_id": "STU003",
    "local_start_time": "2024-10-15T10:30:00",
    "timezone": "America/Chicago",
    "duration_minutes": 30
  }'
```
**Expected Response:**
```json
{
  "id": 2,
  "professor_id": "PROF001",
  "student_id": "STU003",
  "starts_at": "2024-10-15T10:30:00-05:00",
  "duration_minutes": 30
}
```

---

### 5. Verify DST Spring Forward Nonexistent Time (400 Bad Request)
```bash
curl -X POST http://localhost:8000/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "professor_id": "PROF001",
    "student_id": "STU001",
    "local_start_time": "2024-03-10T02:30:00",
    "timezone": "America/New_York",
    "duration_minutes": 30
  }'
```
**Expected Response:**
```json
{
  "detail": "Invalid local time: this time does not exist due to a daylight saving time transition."
}
```

---

### 6. Verify DST Fall Back Ambiguous Time (201 Created with -04:00 Offset)
```bash
curl -X POST http://localhost:8000/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "professor_id": "PROF001",
    "student_id": "STU001",
    "local_start_time": "2024-11-03T01:30:00",
    "timezone": "America/New_York",
    "duration_minutes": 30
  }'
```
**Expected Response:**
```json
{
  "id": 3,
  "professor_id": "PROF001",
  "student_id": "STU001",
  "starts_at": "2024-11-03T01:30:00-04:00",
  "duration_minutes": 30
}
```

---

### 7. Verify Retrieval of Professor Bookings (200 OK)
```bash
curl -X GET "http://localhost:8000/api/bookings?professor_id=PROF001"
```
**Expected Response:**
```json
[
  {
    "id": 1,
    "professor_id": "PROF001",
    "student_id": "STU001",
    "starts_at": "2024-10-15T10:00:00-05:00",
    "duration_minutes": 30
  },
  {
    "id": 2,
    "professor_id": "PROF001",
    "student_id": "STU003",
    "starts_at": "2024-10-15T10:30:00-05:00",
    "duration_minutes": 30
  },
  {
    "id": 3,
    "professor_id": "PROF001",
    "student_id": "STU001",
    "starts_at": "2024-11-03T01:30:00-04:00",
    "duration_minutes": 30
  }
]
```

---

## Docker Compose Verification

1. **Validate Configuration**:
   ```bash
   docker compose config
   ```
   *Result*: Configuration parses valid syntax with no warnings.

2. **Start Services in Detached Mode**:
   ```bash
   docker compose up --build -d
   ```

3. **Check Container Status and Health**:
   ```bash
   docker compose ps
   ```
   Both `campus_bookings_db` and `campus_bookings_api` report status `healthy`.

4. **Access Swagger UI in Browser**:
   Open: [http://localhost:8000/docs](http://localhost:8000/docs)
