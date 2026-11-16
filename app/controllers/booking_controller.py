"""Presentation layer: FastAPI routing and HTTP controller for office-hour bookings."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.exceptions.booking_exceptions import (
    BookingOverlapError,
    BookingServiceError,
    InvalidBookingDurationError,
    InvalidTimezoneError,
    NonexistentLocalTimeError,
)
from app.repositories.postgres_booking_repository import PostgresBookingRepository
from app.schemas.booking_schema import (
    BookingCreateRequest,
    BookingResponse,
    HealthResponse,
)
from app.services.booking_service import BookingService

router = APIRouter(tags=["Bookings"])


def get_booking_service(session: Session = Depends(get_db)) -> BookingService:
    """Dependency provider injecting PostgresBookingRepository into BookingService."""
    repository = PostgresBookingRepository(session)
    return BookingService(repository)


@router.post(
    "/api/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create office-hour booking",
    description="Create a new office-hour booking with timezone validation, DST handling, and overlap prevention.",
)
def create_booking(
    request: BookingCreateRequest,
    service: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    """Handle booking creation request."""
    try:
        booking = service.create_booking(
            professor_id=request.professor_id,
            student_id=request.student_id,
            local_start_time=request.local_start_time,
            timezone_name=request.timezone,
            duration_minutes=request.duration_minutes,
        )
        formatted = service.format_booking_response(booking)
        return BookingResponse(**formatted)
    except BookingOverlapError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except NonexistentLocalTimeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except (InvalidTimezoneError, InvalidBookingDurationError, ValueError) as e:
        msg = getattr(e, "message", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    except BookingServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.get(
    "/api/bookings",
    response_model=List[BookingResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve bookings for a professor",
    description="Retrieve all office-hour bookings for a specific professor formatted in their original timezones.",
)
def get_bookings(
    professor_id: str = Query(
        ...,
        description="Professor ID to retrieve bookings for.",
        min_length=1,
    ),
    service: BookingService = Depends(get_booking_service),
) -> List[BookingResponse]:
    """Retrieve bookings for a given professor."""
    bookings = service.get_professor_bookings(professor_id)
    return [BookingResponse(**service.format_booking_response(b)) for b in bookings]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Service health verification endpoint for container orchestrators and monitoring.",
)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")
