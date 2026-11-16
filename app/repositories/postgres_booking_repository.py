"""PostgreSQL implementation of IBookingRepository using SQLAlchemy 2.x."""
from datetime import datetime, timezone
from typing import List
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.entities.booking import Booking, BookingModel
from app.repositories.booking_repository import IBookingRepository


class PostgresBookingRepository(IBookingRepository):
    """PostgreSQL data access repository for office-hour bookings."""

    def __init__(self, session: Session):
        self._session = session

    def save(self, booking: Booking) -> Booking:
        """Persist a new booking record to PostgreSQL and return the updated domain entity."""
        start_utc = booking.starts_at_utc
        if start_utc.tzinfo is None:
            start_utc = start_utc.replace(tzinfo=timezone.utc)
        else:
            start_utc = start_utc.astimezone(timezone.utc)

        model = BookingModel(
            professor_id=booking.professor_id,
            student_id=booking.student_id,
            starts_at_utc=start_utc,
            duration_minutes=booking.duration_minutes,
            original_timezone=booking.original_timezone,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return model.to_entity()

    def find_overlapping(
        self, professor_id: str, start_utc: datetime, end_utc: datetime
    ) -> List[Booking]:
        """Query PostgreSQL for overlapping bookings for the given professor.

        Overlap formula:
            (starts_at_utc < :end_utc) AND (starts_at_utc + duration_minutes * INTERVAL '1 minute' > :start_utc)
        """
        # Ensure comparison timestamps are timezone-aware UTC
        if start_utc.tzinfo is None:
            start_utc = start_utc.replace(tzinfo=timezone.utc)
        else:
            start_utc = start_utc.astimezone(timezone.utc)

        if end_utc.tzinfo is None:
            end_utc = end_utc.replace(tzinfo=timezone.utc)
        else:
            end_utc = end_utc.astimezone(timezone.utc)

        bind = self._session.get_bind()
        dialect_name = bind.dialect.name if bind is not None else "postgresql"

        if dialect_name == "postgresql":
            stmt = (
                select(BookingModel)
                .where(
                    BookingModel.professor_id == professor_id,
                    BookingModel.starts_at_utc < end_utc,
                    BookingModel.starts_at_utc
                    + text("(office_hour_bookings.duration_minutes * interval '1 minute')")
                    > start_utc,
                )
                .order_by(BookingModel.starts_at_utc)
            )
            records = self._session.scalars(stmt).all()
            return [r.to_entity() for r in records]
        else:
            # Fallback for SQLite in local test harnesses
            stmt = (
                select(BookingModel)
                .where(
                    BookingModel.professor_id == professor_id,
                    BookingModel.starts_at_utc < end_utc,
                )
                .order_by(BookingModel.starts_at_utc)
            )
            records = self._session.scalars(stmt).all()
            entities = [r.to_entity() for r in records]
            return [
                e
                for e in entities
                if (
                    e.ends_at_utc.replace(tzinfo=timezone.utc)
                    if e.ends_at_utc.tzinfo is None
                    else e.ends_at_utc
                )
                > start_utc
            ]

    def find_by_professor(self, professor_id: str) -> List[Booking]:
        """Query PostgreSQL for all bookings scheduled with the specified professor."""
        stmt = (
            select(BookingModel)
            .where(BookingModel.professor_id == professor_id)
            .order_by(BookingModel.starts_at_utc.asc())
        )
        records = self._session.scalars(stmt).all()
        return [r.to_entity() for r in records]
