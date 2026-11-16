"""Abstract repository interface for booking persistence."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List
from app.entities.booking import Booking


class IBookingRepository(ABC):
    """Abstract interface defining data access operations for office-hour bookings."""

    @abstractmethod
    def save(self, booking: Booking) -> Booking:
        """Persist a new booking domain entity and return it with an assigned ID."""
        pass

    @abstractmethod
    def find_overlapping(
        self, professor_id: str, start_utc: datetime, end_utc: datetime
    ) -> List[Booking]:
        """Find all existing bookings for the professor that overlap with [start_utc, end_utc).

        Overlap condition:
            (existing.starts_at_utc < end_utc) AND (existing.ends_at_utc > start_utc)
        """
        pass

    @abstractmethod
    def find_by_professor(self, professor_id: str) -> List[Booking]:
        """Retrieve all bookings scheduled for a given professor."""
        pass
