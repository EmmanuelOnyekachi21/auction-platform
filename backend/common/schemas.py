"""Shared Pydantic schema models used across the application.

Provides reusable response and error structures that are referenced by
multiple apps rather than belonging to any single domain module.
"""

from typing import Any, Literal

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """A single field-level error detail returned in validation responses.

    Attributes:
        field: The name of the input field that failed validation.
        message: Human-readable explanation of why the field is invalid.

    """

    field: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all API error handlers.

    Attributes:
        code: Machine-readable upper-snake-case error identifier.
        message: Human-readable summary of the error.
        details: Optional list of field-level ``ErrorDetail`` objects,
            populated for validation errors.

    """

    code: str
    status: Literal["error"] = "error"
    message: str
    details: list[ErrorDetail] = []


class SuccessResponse(BaseModel):
    """Standard success envelope returned by all API success handlers.

    Attributes:
        status: Always ``"success"`` as a convenience discriminator for clients.
        message: Human-readable description of the completed operation.
        data: The JSON-serializable response payload, or ``None``.

    """

    status: Literal["success"] = "success"
    message: str
    data: Any | None = None


class PaginationMeta(BaseModel):
    """Metadata describing the current pagination state of a list response.

    Attributes:
        page: The current page number (1-indexed).
        limit: Maximum number of items returned per page.
        total: Total number of items across all pages.
        total_pages: Total number of pages given the current limit.
        has_next: Whether a next page exists.
        has_previous: Whether a previous page exists.

    """

    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel):
    """Standard paginated response envelope.

    Attributes:
        status: Always ``"success"`` as a convenience discriminator for clients.
        message: Human-readable description of the completed operation.
        data: The JSON-serializable list of items for the current page.
        pagination: Metadata describing the current pagination state.

    """

    status: Literal["success"] = "success"
    message: str
    data: list[Any]
    pagination: PaginationMeta
