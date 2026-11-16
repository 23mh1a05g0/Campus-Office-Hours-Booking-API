"""In-memory Mock Booking Repository for high-speed, isolated unit testing."""
from datetime import datetime, timezone
from typing import List
from app.entities.booking import Booking
from app.repositories.booking_repository import IBookingRepository


class MockBookingRepository(IBookingRepository):
    """In-memory mock repository implementing IBookingRepository with sequential IDs and zero external dependencies."""

    def __init__(self):
        self._bookings: List[Booking] = []
        self._next_id: int = 1

    def save(self, booking: Booking) -> Booking:
        """Assign sequential ID, persist in-memory, and return a cloned domain entity."""
        # Ensure UTC timezone awareness on starts_at_utc
        start_utc = booking.starts_at_utc
        if start_utc.tzinfo is None:
            start_utc = start_utc.replace(tzinfo=timezone.utc)
        else:
            start_utc = start_utc.astimezone(timezone.utc)

        persisted = Booking(
            id=self._next_id,
            professor_id=booking.professor_id,
            student_id=booking.student_id,
            starts_at_utc=start_utc,
            duration_minutes=booking.duration_minutes,
            original_timezone=booking.original_timezone,
        )
        self._next_id += 1
        self._bookings.append(persisted)
        return persisted

    def find_overlapping(
        self, professor_id: str, start_utc: datetime, end_utc: datetime
    ) -> List[Booking]:
        """Find overlapping appointments for professor using standard interval formula.

        Formula: (existing_start < new_end) AND (existing_end > new_start)
        """
        # Normalize input comparison instants to UTC
        if start_utc.tzinfo is None:
            start_utc = start_utc.replace(tzinfo=timezone.utc)
        else:
            start_utc = start_utc.astimezone(timezone.utc)

        if end_utc.tzinfo is None:
            end_utc = end_utc.replace(tzinfo=timezone.utc)
        else:
            end_utc = end_utc.astimezone(timezone.utc)

        overlapping: List[Booking] = []
        for b in self._bookings:
            if b.professor_id != professor_id:
                continue

            b_start = (
                b.starts_at_utc
                if b.starts_at_utc.tzinfo
                else b.starts_at_utc.replace(tzinfo=timezone.utc)
            )
            b_end = b.ends_at_utc
            if b_end.tzinfo is None:
                b_end = b_end.replace(tzinfo=timezone.utc)

            # Strict overlap formula
            if b_start < end_utc and b_end > start_utc:
                overlapping.append(b)

        return overlapping

    def find_by_professor(self, professor_id: str) -> List[Booking]:
        """Retrieve all bookings for a given professor sorted by starts_at_utc ascending."""
        matched = [b for b in self._bookings if b.professor_id == professor_id]
        return sorted(matched, key=lambda b: b.starts_at_utc)

    def clear(self) -> None:
        """Helper to reset in-memory storage during test teardown if needed."""
        self._bookings.clear()
        self._next_id = 1
