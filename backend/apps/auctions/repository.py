"""Repository for category database operations."""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auctions.models import Category


class CategoryRepository:
    """Repository for category CRUD operations."""

    def __init__(self, db: AsyncSession):
        """Initialize category repository.

        Args:
            db: Async database session

        """
        self._db = db

    async def get_all(self) -> Sequence[Category]:
        """Get all categories ordered by name.

        Returns:
            Sequence of all categories

        """
        stmt = select(Category).order_by(Category.name.asc())
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, category_id: uuid.UUID) -> Category | None:
        """Get category by ID.

        Args:
            category_id: Category UUID

        Returns:
            Category instance or None if not found

        """
        stmt = select(Category).where(Category.id == category_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Category | None:
        """Get category by slug.

        Args:
            slug: Category slug

        Returns:
            Category instance or None if not found

        """
        query = select(Category).where(Category.slug == slug)
        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def get_children(self, parent_id: uuid.UUID) -> Sequence[Category]:
        """Get child categories of a parent category.

        Args:
            parent_id: Parent category UUID

        Returns:
            Sequence of child categories

        """
        query = (
            select(Category)
            .where(Category.parent_id == parent_id)
            .order_by(Category.name.asc())
        )
        result = await self._db.execute(query)
        return result.scalars().all()
