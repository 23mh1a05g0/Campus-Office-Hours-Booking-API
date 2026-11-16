"""Unit tests for BookingService using MockBookingRepository with zero database dependencies."""
from datetime import datetime, timezone
import pytest
from app.entities.booking import Booking
from app.exceptions.booking_exceptions import (
    BookingOverlapError,
    InvalidBookingDurationError,
    InvalidTimezoneError,
    NonexistentLocalTimeError,
)
from app.repositories.mock_booking_repository import MockBookingRepository
from app.services.booking_service import BookingService


@pytest.fixture
def mock_repo() -> MockBookingRepository:
    """Fixture providing a fresh in-memory mock repository."""
    return MockBookingRepository()


@pytest.fixture
def booking_service(mock_repo: MockBookingRepository) -> BookingService:
    """Fixture instantiating BookingService with the mock repository via Dependency Injection."""
    return BookingService(mock_repo)


def test_successful_booking_creation(booking_service: BookingService):
    """Verify successful booking creation with valid local time and IANA timezone."""
    booking = booking_service.create_booking(
        professor_id="PROF001",
        student_id="STU001",
        local_start_time="2024-10-15T10:00:00",
        timezone_name="America/Chicago",
        duration_minutes=30,
    )

    assert booking.id == 1
    assert booking.professor_id == "PROF001"
    assert booking.student_id == "STU001"
    assert booking.duration_minutes == 30
    assert booking.original_timezone == "America/Chicago"

    formatted = booking_service.format_booking_response(booking)
    assert formatted["id"] == 1
    assert formatted["starts_at"] == "2024-10-15T10:00:00-05:00"
    assert formatted["duration_minutes"] == 30


@pytest.mark.parametrize("invalid_duration", [0, -15, -1, 481, 1000])
def test_invalid_duration_rejection(booking_service: BookingService, invalid_duration: int):
    """Verify that durations <= 0 or > 480 minutes are strictly rejected."""
    with pytest.raises(InvalidBookingDurationError) as exc_info:
        booking_service.create_booking(
            professor_id="PROF001",
            student_id="STU001",
            local_start_time="2024-10-15T10:00:00",
            timezone_name="America/Chicago",
            duration_minutes=invalid_duration,
        )
    assert exc_info.value.duration_minutes == invalid_duration


def test_overlapping_booking_rejection(booking_service: BookingService):
    """Verify that an appointment overlapping an existing booking for the same professor is rejected."""
    # Booking A: 10:00 - 10:30 UTC
    booking_service.create_booking(
        professor_id="PROF001",
        student_id="STU001",
        local_start_time="2024-10-15T10:00:00",
        timezone_name="UTC",
        duration_minutes=30,
    )

    # Booking B: 10:15 - 10:45 UTC (overlaps with Booking A)
    with pytest.raises(BookingOverlapError) as exc_info:
        booking_service.create_booking(
            professor_id="PROF001",
            student_id="STU002",
            local_start_time="2024-10-15T10:15:00",
            timezone_name="UTC",
            duration_minutes=30,
        )
    assert exc_info.value.professor_id == "PROF001"


def test_adjacent_booking_acceptance(booking_service: BookingService):
    """Verify that adjacent appointments (start of one is end of another) are permitted."""
    # Booking A: 10:00 - 10:30 UTC
    b1 = booking_service.create_booking(
        professor_id="PROF001",
        student_id="STU001",
        local_start_time="2024-10-15T10:00:00",
        timezone_name="UTC",
        duration_minutes=30,
    )
    assert b1.id == 1

    # Booking B: 10:30 - 11:00 UTC (immediately adjacent to Booking A)
    b2 = booking_service.create_booking(
        professor_id="PROF001",
        student_id="STU002",
        local_start_time="2024-10-15T10:30:00",
        timezone_name="UTC",
        duration_minutes=30,
    )
    assert b2.id == 2


def test_different_professor_booking_acceptance(booking_service: BookingService):
    """Verify that simultaneous appointments for different professors are permitted."""
    b1 = booking_service.create_booking(
        professor_id="PROF001",
        student_id="STU001",
        local_start_time="2024-10-15T10:00:00",
        timezone_name="America/Chicago",
        duration_minutes=30,
    )
    b2 = booking_service.create_booking(
        professor_id="PROF002",
        student_id="STU002",
        local_start_time="2024-10-15T10:00:00",
        timezone_name="America/Chicago",
        duration_minutes=30,
    )

    assert b1.id == 1
    assert b2.id == 2
    assert b1.professor_id != b2.professor_id


def test_retrieval_of_professor_bookings(booking_service: BookingService):
    """Verify retrieval and sorting of all bookings belonging to a specific professor."""
    booking_service.create_booking(
        professor_id="PROF001",
        student_id="STU001",
        local_start_time="2024-10-15T11:00:00",
        timezone_name="America/Chicago",
        duration_minutes=30,
    )
    booking_service.create_booking(
        professor_id="PROF001",
        student_id="STU002",
        local_start_time="2024-10-15T09:00:00",
        timezone_name="America/Chicago",
        duration_minutes=30,
    )
    # Different professor booking to ensure isolation
    booking_service.create_booking(
        professor_id="PROF002",
        student_id="STU003",
        local_start_time="2024-10-15T09:00:00",
        timezone_name="America/Chicago",
        duration_minutes=30,
    )

    bookings = booking_service.get_professor_bookings("PROF001")
    assert len(bookings) == 2
    # Verify chronological sorting
    assert bookings[0].starts_at_utc < bookings[1].starts_at_utc
    assert bookings[0].student_id == "STU002"
    assert bookings[1].student_id == "STU001"


@pytest.mark.parametrize("invalid_tz", ["Mars/Phobos", "Invalid_Zone", "GMT+99", "", "   "])
def test_invalid_iana_timezone_rejection(booking_service: BookingService, invalid_tz: str):
    """Verify that invalid or non-IANA timezone strings are rejected."""
    with pytest.raises(InvalidTimezoneError):
        booking_service.create_booking(
            professor_id="PROF001",
            student_id="STU001",
            local_start_time="2024-10-15T10:00:00",
            timezone_name=invalid_tz,
            duration_minutes=30,
        )


def test_dst_spring_forward_rejection(booking_service: BookingService):
    """Verify that nonexistent local time during DST Spring Forward transition is rejected with NonexistentLocalTimeError."""
    # In America/New_York, 2024-03-10 02:30:00 does not exist because clocks jump 01:59:59 -> 03:00:00
    with pytest.raises(NonexistentLocalTimeError) as exc_info:
        booking_service.create_booking(
            professor_id="PROF001",
            student_id="STU001",
            local_start_time="2024-03-10T02:30:00",
            timezone_name="America/New_York",
            duration_minutes=30,
        )
    assert "does not exist" in str(exc_info.value)


def test_dst_fall_back_acceptance_with_fold0(booking_service: BookingService):
    """Verify that ambiguous local time during DST Fall Back transition is accepted with fold=0 (-04:00 offset)."""
    # In America/New_York, 2024-11-03 01:30:00 occurs twice:
    # First occurrence (fold=0): 01:30:00 EDT (UTC-4) -> 05:30:00 UTC
    # Second occurrence (fold=1): 01:30:00 EST (UTC-5) -> 06:30:00 UTC
    booking = booking_service.create_booking(
        professor_id="PROF001",
        student_id="STU001",
        local_start_time="2024-11-03T01:30:00",
        timezone_name="America/New_York",
        duration_minutes=30,
    )

    assert booking.id == 1
    # Check UTC instant is 05:30:00 UTC
    expected_utc = datetime(2024, 11, 3, 5, 30, tzinfo=timezone.utc)
    assert booking.starts_at_utc == expected_utc

    # Formatted response must retain the -04:00 offset
    formatted = booking_service.format_booking_response(booking)
    assert formatted["starts_at"] == "2024-11-03T01:30:00-04:00"


def test_timezone_aware_conversion_to_utc(booking_service: BookingService):
    """Verify that local time is converted to an aware UTC instant and never stored as naive."""
    # America/Chicago on 2024-10-15 is CDT (UTC-5)
    booking = booking_service.create_booking(
        professor_id="PROF001",
        student_id="STU001",
        local_start_time="2024-10-15T10:00:00",
        timezone_name="America/Chicago",
        duration_minutes=45,
    )

    assert booking.starts_at_utc.tzinfo is not None
    assert booking.starts_at_utc == datetime(2024, 10, 15, 15, 0, 0, tzinfo=timezone.utc)


def test_cross_timezone_overlap_rejection(booking_service: BookingService):
    """Verify that overlapping appointments submitted in different timezones are accurately detected in UTC."""
    # Booking 1: 10:00 - 11:00 in America/Chicago (CDT, UTC-5) -> 15:00 - 16:00 UTC
    booking_service.create_booking(
        professor_id="PROF001",
        student_id="STU001",
        local_start_time="2024-10-15T10:00:00",
        timezone_name="America/Chicago",
        duration_minutes=60,
    )

    # Booking 2: 11:30 - 12:00 in America/New_York (EDT, UTC-4) -> 15:30 - 16:00 UTC
    # 15:30 UTC overlaps with [15:00, 16:00] UTC
    with pytest.raises(BookingOverlapError):
        booking_service.create_booking(
            professor_id="PROF001",
            student_id="STU002",
            local_start_time="2024-10-15T11:30:00",
            timezone_name="America/New_York",
            duration_minutes=30,
        )


def test_empty_professor_booking_list(booking_service: BookingService):
    """Verify that querying a professor with no bookings returns an empty list."""
    bookings = booking_service.get_professor_bookings("PROF_DOES_NOT_EXIST")
    assert bookings == []
