"""Custom domain and service exceptions for Campus Office Hours Booking API."""


class BookingServiceError(Exception):
    """Base exception for all booking domain errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BookingOverlapError(BookingServiceError):
    """Raised when an appointment overlaps with an existing booking for the professor."""

    def __init__(self, professor_id: str, message: str = None):
        msg = (
            message
            or f"Requested booking overlaps with an existing appointment for professor {professor_id}."
        )
        super().__init__(msg)
        self.professor_id = professor_id


class InvalidTimezoneError(BookingServiceError):
    """Raised when an unrecognized or invalid IANA timezone identifier is provided."""

    def __init__(self, timezone: str, message: str = None):
        msg = message or f"Unknown or invalid IANA timezone identifier: {timezone}."
        super().__init__(msg)
        self.timezone = timezone


class NonexistentLocalTimeError(BookingServiceError):
    """Raised when a local time does not exist due to a Daylight Saving Time transition."""

    def __init__(
        self,
        message: str = "Invalid local time: this time does not exist due to a daylight saving time transition.",
    ):
        super().__init__(message)


class InvalidBookingDurationError(BookingServiceError):
    """Raised when a requested booking duration is negative, zero, or exceeds maximum limits."""

    def __init__(self, duration_minutes: int, message: str = None):
        msg = (
            message
            or f"Invalid booking duration: {duration_minutes}. Duration must be positive and not exceed 480 minutes."
        )
        super().__init__(msg)
        self.duration_minutes = duration_minutes
