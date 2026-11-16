"""Pydantic validation schemas for HTTP requests and responses."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.exceptions.booking_exceptions import InvalidTimezoneError
from app.utils.timezone_utils import parse_and_validate_local_datetime, validate_iana_timezone


class BookingCreateRequest(BaseModel):
    """Schema for POST /api/bookings request body."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "professor_id": "PROF001",
                "student_id": "STU001",
                "local_start_time": "2024-10-15T10:00:00",
                "timezone": "America/Chicago",
                "duration_minutes": 30,
            }
        },
    )

    professor_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier for the professor.",
    )
    student_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier for the student.",
    )
    local_start_time: str = Field(
        ...,
        description="Naive ISO-8601 local start time (e.g. '2024-10-15T10:00:00'). Must not contain offsets or 'Z'.",
    )
    timezone: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Valid IANA timezone identifier (e.g. 'America/Chicago').",
    )
    duration_minutes: int = Field(
        ...,
        ge=1,
        le=480,
        description="Duration of the appointment in minutes (between 1 and 480).",
    )

    @field_validator("local_start_time")
    @classmethod
    def validate_local_time(cls, v: str) -> str:
        parse_and_validate_local_datetime(v)
        return v.strip()

    @field_validator("timezone")
    @classmethod
    def validate_tz(cls, v: str) -> str:
        try:
            validate_iana_timezone(v)
        except InvalidTimezoneError as e:
            raise ValueError(e.message) from e
        return v.strip()


class BookingResponse(BaseModel):
    """Schema for booking representation in API responses."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "professor_id": "PROF001",
                "student_id": "STU001",
                "starts_at": "2024-10-15T10:00:00-05:00",
                "duration_minutes": 30,
            }
        },
    )

    id: int = Field(..., description="Unique booking ID.")
    professor_id: str = Field(..., description="Unique identifier for the professor.")
    student_id: str = Field(..., description="Unique identifier for the student.")
    starts_at: str = Field(
        ...,
        description="Appointment start time in ISO-8601 format with original timezone offset.",
    )
    duration_minutes: int = Field(..., description="Duration of the appointment in minutes.")


class HealthResponse(BaseModel):
    """Schema for GET /health endpoint."""

    status: str = Field(default="healthy", description="Service health status.")
