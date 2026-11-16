"""Business logic layer for managing office-hour bookings."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Union
from app.entities.booking import Booking
from app.exceptions.booking_exceptions import (
    BookingOverlapError,
    InvalidBookingDurationError,
)
from app.repositories.booking_repository import IBookingRepository
from app.utils.timezone_utils import (
    local_to_utc,
    parse_and_validate_local_datetime,
    utc_to_local_iso,
    validate_iana_timezone,
)


class BookingService:
    """Service encapsulating business rules for office-hour bookings.

    Depends strictly on the abstract IBookingRepository interface.
    """

    MIN_DURATION_MINUTES = 1
    MAX_DURATION_MINUTES = 480

    def __init__(self, repository: IBookingRepository):
        """Constructor-based Dependency Injection."""
        self._repository = repository

    def create_booking(
        self,
        professor_id: str,
        student_id: str,
        local_start_time: Union[str, datetime],
        timezone_name: str,
        duration_minutes: int,
    ) -> Booking:
        """Validate input parameters, normalize to UTC, verify overlaps, and persist booking.

        Args:
            professor_id: Unique identifier for the professor.
            student_id: Unique identifier for the student.
            local_start_time: Naive local ISO-8601 string or naive datetime.
            timezone_name: Valid IANA timezone identifier (e.g. 'America/Chicago').
            duration_minutes: Appointment duration in minutes (1 - 480).

        Returns:
            Booking: Persisted domain entity with assigned ID.

        Raises:
            InvalidBookingDurationError: If duration is <= 0 or > 480.
            InvalidTimezoneError: If timezone identifier is invalid.
            NonexistentLocalTimeError: If local time falls into DST Spring Forward gap.
            BookingOverlapError: If appointment conflicts with existing booking.
            ValueError: If input parameters fail format validation.
        """
        # 1. Validate duration
        if (
            not isinstance(duration_minutes, int)
            or duration_minutes < self.MIN_DURATION_MINUTES
            or duration_minutes > self.MAX_DURATION_MINUTES
        ):
            raise InvalidBookingDurationError(duration_minutes)

        # 2. Validate IDs
        if not professor_id or not isinstance(professor_id, str) or not professor_id.strip():
            raise ValueError("professor_id must be a non-empty string.")
        if not student_id or not isinstance(student_id, str) or not student_id.strip():
            raise ValueError("student_id must be a non-empty string.")

        prof_id = professor_id.strip()
        stu_id = student_id.strip()

        # 3. Validate IANA timezone
        validate_iana_timezone(timezone_name)

        # 4. Parse naive local datetime
        if isinstance(local_start_time, str):
            local_dt = parse_and_validate_local_datetime(local_start_time)
        elif isinstance(local_start_time, datetime):
            if local_start_time.tzinfo is not None:
                raise ValueError("local_start_time must not contain a UTC offset or Z suffix.")
            local_dt = local_start_time
        else:
            raise ValueError("local_start_time must be an ISO-8601 string or naive datetime.")

        # 5. Convert local time to UTC instant (detects nonexistent and resolves ambiguous with fold=0)
        _, starts_at_utc = local_to_utc(local_dt, timezone_name)
        ends_at_utc = starts_at_utc + timedelta(minutes=duration_minutes)

        # 6. Check for overlapping bookings for the same professor
        overlapping = self._repository.find_overlapping(
            professor_id=prof_id,
            start_utc=starts_at_utc,
            end_utc=ends_at_utc,
        )
        if overlapping:
            raise BookingOverlapError(professor_id=prof_id)

        # 7. Construct and persist domain entity
        new_booking = Booking(
            id=None,
            professor_id=prof_id,
            student_id=stu_id,
            starts_at_utc=starts_at_utc,
            duration_minutes=duration_minutes,
            original_timezone=timezone_name,
        )

        return self._repository.save(new_booking)

    def get_professor_bookings(self, professor_id: str) -> List[Booking]:
        """Retrieve all bookings scheduled for a given professor.

        Returns:
            List[Booking]: Chronologically sorted list of bookings (empty if none).
        """
        if not professor_id or not isinstance(professor_id, str):
            return []
        return self._repository.find_by_professor(professor_id.strip())

    def format_booking_response(self, booking: Booking) -> Dict[str, Any]:
        """Format a domain Booking entity into the API response schema with correct timezone offset."""
        starts_at_iso = utc_to_local_iso(booking.starts_at_utc, booking.original_timezone)
        return {
            "id": booking.id,
            "professor_id": booking.professor_id,
            "student_id": booking.student_id,
            "starts_at": starts_at_iso,
            "duration_minutes": booking.duration_minutes,
        }
