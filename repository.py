from sqlalchemy import select, func
from db import async_session
from models import Candle


async def get_all_candles():
    async with async_session() as session:
        result = await session.execute(select(Candle))
        candles = result.scalars().all()
        return candles


async def get_candles_by_tag(tag: str):
    async with async_session() as session:
        result = await session.execute(
            select(Candle).where(func.lower(tag) == func.any(Candle.tags))
        )
        return result.scalars().all()
