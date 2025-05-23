from db import engine
from models import Base
import asyncio


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Table successfully created!")


if __name__ == "__main__":
    asyncio.run(init_db())
