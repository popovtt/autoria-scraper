import asyncio
import logging
import os

from src.scheduler import setup_scheduler
from src.scraper import run_scraper
from src.settings import config

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


async def main():
    setup_scheduler()
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
