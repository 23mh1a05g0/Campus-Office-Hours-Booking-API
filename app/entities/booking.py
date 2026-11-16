"""Booking domain entity and SQLAlchemy ORM model."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint
from app.database import Base


@dataclass
class Booking:
    """Domain-level Booking entity."""

    id: Optional[int]
    professor_id: str
    student_id: str
    starts_at_utc: datetime
    duration_minutes: int
    original_timezone: str

    @property
    def ends_at_utc(self) -> datetime:
        """Calculate the UTC end time instant for this booking."""
        return self.starts_at_utc + timedelta(minutes=self.duration_minutes)

    @classmethod
    def from_orm(cls, model: "BookingModel") -> "Booking":
        """Convert a SQLAlchemy BookingModel instance into a domain Booking entity."""
        return cls(
            id=model.id,
            professor_id=model.professor_id,
            student_id=model.student_id,
            starts_at_utc=model.starts_at_utc,
            duration_minutes=model.duration_minutes,
            original_timezone=model.original_timezone,
        )


class BookingModel(Base):
    """SQLAlchemy ORM model mapping to office_hour_bookings table."""

    __tablename__ = "office_hour_bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    professor_id = Column(String(255), nullable=False, index=True)
    student_id = Column(String(255), nullable=False)
    starts_at_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(
        Integer,
        CheckConstraint("duration_minutes > 0", name="chk_positive_duration"),
        nullable=False,
    )
    original_timezone = Column(String(100), nullable=False)

    def to_entity(self) -> Booking:
        """Convert ORM model to domain entity."""
        return Booking.from_orm(self)
