"""FastAPI application initialization and entrypoint."""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.config import settings
from app.controllers.booking_controller import router as booking_router
from app.database import init_db
from app.exceptions.booking_exceptions import (
    BookingOverlapError,
    BookingServiceError,
    InvalidBookingDurationError,
    InvalidTimezoneError,
    NonexistentLocalTimeError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("campus_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown routines."""
    logger.info("Initializing Campus Office Hours Booking API...")
    if settings.APP_ENV != "testing":
        try:
            init_db()
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            logger.warning(
                f"Database initialization deferred or skipped: {e}. "
                "Tables will be created upon first database connection or migration."
            )
    yield
    logger.info("Shutting down Campus Office Hours Booking API...")


app = FastAPI(
    title="Campus Office Hours Booking API",
    description="Timezone-aware REST API for scheduling student-professor office hours with strict layered architecture.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Mount controller router
app.include_router(booking_router)


# Global Exception Handlers
@app.exception_handler(BookingOverlapError)
async def booking_overlap_handler(request: Request, exc: BookingOverlapError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message},
    )


@app.exception_handler(NonexistentLocalTimeError)
async def nonexistent_time_handler(request: Request, exc: NonexistentLocalTimeError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
    )


@app.exception_handler(InvalidTimezoneError)
async def invalid_timezone_handler(request: Request, exc: InvalidTimezoneError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
    )


@app.exception_handler(InvalidBookingDurationError)
async def invalid_duration_handler(request: Request, exc: InvalidBookingDurationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
    )


@app.exception_handler(BookingServiceError)
async def booking_service_error_handler(request: Request, exc: BookingServiceError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format request validation errors consistently as HTTP 400."""
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Invalid request payload.")
    if msg.startswith("Value error, "):
        msg = msg[len("Value error, "):]
    loc = " -> ".join(str(l) for l in first_error.get("loc", []))
    detail_msg = f"Validation error at '{loc}': {msg}" if loc else msg

    clean_errors = [
        {
            "loc": err.get("loc", ()),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in errors
    ]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": detail_msg, "errors": clean_errors},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.APP_ENV == "development",
    )
