"""Seed default bid increment tiers into the database."""

import asyncio
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

import config.model_registry  # noqa: F401, E402
from apps.auctions.models import BidIncrementTier  # noqa: E402
from config.settings import settings  # noqa: E402

TIERS = [
    {
        "min_value": Decimal("0"),
        "max_value": Decimal("5000"),
        "increment": Decimal("100"),
    },
    {
        "min_value": Decimal("5001"),
        "max_value": Decimal("20000"),
        "increment": Decimal("500"),
    },
    {
        "min_value": Decimal("20001"),
        "max_value": Decimal("100000"),
        "increment": Decimal("1000"),
    },
    {
        "min_value": Decimal("100001"),
        "max_value": Decimal("500000"),
        "increment": Decimal("5000"),
    },
    {
        "min_value": Decimal("500001"),
        "max_value": Decimal("2000000"),
        "increment": Decimal("10000"),
    },
    {
        "min_value": Decimal("2000001"),
        "max_value": None,
        "increment": Decimal("25000"),
    },
]


async def seed() -> None:
    """Insert all default bid increment tiers into the database.

    Creates a fresh async engine, opens a session, persists each tier
    defined in ``TIERS``, commits, and disposes of the engine.

    """
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        for tier_data in TIERS:
            tier = BidIncrementTier(**tier_data)
            session.add(tier)
        await session.commit()
        print(f"Seeded {len(TIERS)} bid increment tiers.")
    await engine.dispose()


asyncio.run(seed())
