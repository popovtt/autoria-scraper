from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import datetime
from typing import Sequence

import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from .models.car_orm import CarOrm
from .utils.db import SessionLocal

log = logging.getLogger("autoria.scraper")

ODOMETER_RE = re.compile(r"\D+")
DIGITS_RE = re.compile(r"\D+")

REQUEST_DELAY_RANGE = (0.8, 2.2)
PAGE_DELAY_RANGE = (2.0, 4.5)
MAX_RETRIES = 3

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
]


def parse_odometer(text: str) -> int:
    n = int(ODOMETER_RE.sub("", text) or 0)
    return n * 1000 if n < 1000 else n


def only_digits(text: str) -> str:
    return DIGITS_RE.sub("", text or "")


def safe_text(node, default: str = "") -> str:
    return node.get_text(strip=True) if node else default


def safe_attr(node, attr: str, default: str = "") -> str:
    if not node:
        return default
    return node.get(attr) or default


async def human_delay(delay_range: tuple[float, float]) -> None:
    await asyncio.sleep(random.uniform(*delay_range))


async def fetch(session: aiohttp.ClientSession, url: str) -> str:
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await human_delay(REQUEST_DELAY_RANGE)

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=25)) as r:
                if r.status in (403, 429):
                    text = await r.text()
                    log.warning(
                        "Got %s for %s (attempt=%s). Body_len=%s",
                        r.status,
                        url,
                        attempt,
                        len(text),
                    )
                    # Backoff
                    await asyncio.sleep(2.0 * attempt + random.uniform(0, 1.5))
                    continue

                r.raise_for_status()
                return await r.text()

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_exc = e
            log.warning(
                "Request failed (attempt=%s/%s) url=%s err=%r",
                attempt,
                MAX_RETRIES,
                url,
                e,
            )
            await asyncio.sleep(1.5 * attempt + random.uniform(0, 1.0))

    raise RuntimeError(
        f"Failed to fetch {url} after {MAX_RETRIES} retries"
    ) from last_exc


async def parse_car(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title = safe_text(soup.select_one("h1"))

    price_raw = safe_text(soup.select_one("#sidePrice strong")) or safe_text(
        soup.select_one(".price_value strong")
    )
    odo_raw = safe_text(soup.select_one("#basicInfoTableMainInfo0 span"))

    username = safe_text(soup.select_one("#sellerInfoUserName span"))
    phone_raw = safe_text(soup.select_one(".button-main.mt-16 span"))

    img = soup.select_one("span.picture img")
    images_count = len(soup.select(".preview-gallery img"))

    car_number = safe_text(soup.select_one(".car-number.ua span"))
    car_vin = safe_text(soup.select_one("#badgesVin span"))

    return {
        "url": url,
        "title": title,
        "price_usd": int(only_digits(price_raw) or 0),
        "odometer": parse_odometer(odo_raw) if odo_raw else 0,
        "username": username,
        "phone_number": only_digits(phone_raw),
        "image_url": safe_attr(img, "data-src") or safe_attr(img, "src"),
        "images_count": images_count,
        "car_number": car_number,
        "car_vin": car_vin,
        "datetime_found": datetime.now(),
    }


async def _fetch_existing_urls(db, urls: Sequence[str]) -> set[str]:
    if not urls:
        return set()
    stmt = select(CarOrm.url).where(CarOrm.url.in_(urls))
    rows = (await db.execute(stmt)).scalars().all()
    return set(rows)


async def _bulk_insert_ignore_conflicts(db, rows: list[dict]) -> int:
    if not rows:
        return 0

    stmt = (
        insert(CarOrm).values(rows).on_conflict_do_nothing(index_elements=[CarOrm.url])
    )
    res = await db.execute(stmt)
    return int(res.rowcount or 0)


async def run_scraper(
    start_url: str,
    *,
    concurrency: int = 6,
    page_start: int = 1,
) -> None:
    log.info(
        "RUN SCRAPER fired at %s | start_url=%s | concurrency=%s",
        datetime.now(),
        start_url,
        concurrency,
    )

    sem = asyncio.Semaphore(concurrency)

    async def guarded_parse(http: aiohttp.ClientSession, url: str) -> dict | None:
        async with sem:
            try:
                log.debug("Fetch car | %s", url)
                html = await fetch(http, url)
                data = await parse_car(html, url)
                log.debug("Parsed ok | title=%s | %s", data.get("title", "")[:80], url)
                return data
            except Exception:
                log.exception("Failed to fetch/parse car | %s", url)
                return None

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    async with aiohttp.ClientSession(headers=headers) as http:
        page = page_start

        while True:
            listing_url = f"{start_url}?page={page}"
            log.info("Listing page | page=%s | %s", page, listing_url)

            try:
                html = await fetch(http, listing_url)
            except Exception:
                log.exception("Failed to fetch listing page | %s", listing_url)
                break

            soup = BeautifulSoup(html, "html.parser")
            links = [a["href"] for a in soup.select("a.address[href]")]

            log.info("Links found | page=%s | count=%s", page, len(links))

            if not links:
                log.info("No more links. Stop.")
                break

            async with SessionLocal() as db:
                existing = await _fetch_existing_urls(db, links)
                to_fetch = [u for u in links if u not in existing]

                log.info(
                    "DB dedupe | page=%s | existing=%s | new=%s",
                    page,
                    len(existing),
                    len(to_fetch),
                )

                parsed_raw = await asyncio.gather(
                    *[guarded_parse(http, u) for u in to_fetch]
                )
                rows = [r for r in parsed_raw if r is not None]

                inserted = await _bulk_insert_ignore_conflicts(db, rows)
                await db.commit()

                log.info(
                    "DB commit | page=%s | parsed=%s | inserted=%s",
                    page,
                    len(rows),
                    inserted,
                )

            await human_delay(PAGE_DELAY_RANGE)
            page += 1

    log.info("Scraper finished")
