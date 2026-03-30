"""Script to seed initial categories into the database."""

import asyncio
import logging
import re
import sys
from pathlib import Path

# Add the project root to sys.path so we can import the apps
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import model registry to ensure all models are registered with SQLAlchemy
import config.model_registry  # noqa: F401
from apps.auctions.models import Category
from apps.auctions.repository import CategoryRepository
from config.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

CATEGORIES_TO_SEED = [
    "Electronics",
    "Fashion",
    "Furniture",
    "Vehicles",
    "Books",
    "Sports & Fitness",
    "Home & Garden",
    "Art & Collectibles",
    "Kitchenware",
    "Real Estate",
    "Musical Instruments",
    "Other",
]


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        Slugified text

    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


async def seed_categories():
    """Seed initial categories into the database."""
    async with AsyncSessionLocal() as session:
        repo = CategoryRepository(session)
        created_count = 0

        for name in CATEGORIES_TO_SEED:
            slug = slugify(name)

            # Check if slug exists already in DB.
            exists = await repo.get_by_slug(slug)
            if not exists:
                logger.info(f"Adding category: {name}")
                new_cat = Category(name=name, slug=slug, parent_id=None)
                session.add(new_cat)
                created_count += 1

            else:
                logger.info(f"Skipping (already exists): {name}")

        await session.commit()
        logger.info(f"Seeding complete! Added {created_count} new categories")


if __name__ == "__main__":
    asyncio.run(seed_categories())
