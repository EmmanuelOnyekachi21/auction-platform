"""Pagination utilities for SQLAlchemy async queries.

Provides a ``PageParams`` schema for validating page/limit query parameters
and a ``paginate`` helper that executes a count query and a data query,
returning a fully populated ``PaginatedResponse``.
"""

import math

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import PaginatedResponse, PaginationMeta


class PageParams(BaseModel):
    """Query parameters for paginated list endpoints.

    Attributes:
        page: The requested page number, 1-indexed. Must be >= 1.
        limit: Maximum number of items to return per page.
            Clamped between 1 and 100.

    """

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


async def paginate(
    query,
    page: int,
    limit: int,
    session: AsyncSession,
) -> PaginatedResponse:
    """Execute a paginated SQLAlchemy query and return a structured response.

    Runs two database operations against the provided async session:

    1. A ``COUNT(*)`` wrapped around the original query as a subquery to
       determine the total number of matching rows.
    2. The original query with ``OFFSET`` and ``LIMIT`` applied to fetch
       the current page of results.

    Args:
        query: A SQLAlchemy ``Select`` statement to paginate. Must be
            compatible with ``.subquery()`` for the count step.
        page: The 1-indexed page number to retrieve.
        limit: Maximum number of rows to return for this page.
        session: An active ``AsyncSession`` used to execute both queries.

    Returns:
        A ``PaginatedResponse`` containing the serialised items for the
        requested page and a ``PaginationMeta`` object describing the
        full pagination state.

    """
    offset = (page - 1) * limit

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    result = await session.execute(query.offset(offset).limit(limit))
    items = result.scalars().all()

    total_pages = math.ceil(total / limit) if total > 0 else 1

    return PaginatedResponse(
        message="OK",
        data=items,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )
