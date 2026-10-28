import asyncio
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

BATCH = 100


@dataclass(frozen=True)
class StreamSettings:
    poll_seconds: float = 1.0  # how often the database is checked for new events
    ping_seconds: float = 15.0  # a keep-alive comment, so the connection stays open
    max_seconds: float | None = None  # None means run until the client leaves


def parse_event_number(value: str | None) -> int | None:
    """Turn "evt_12" into 12. Anything else is not an event ID."""
    if not value:
        return None
    prefix, _, number = value.strip().partition("_")
    if prefix != "evt" or not number.isdigit():
        return None
    return int(number)


def sse_message(number: int, data_json: str) -> str:
    """One unnamed Server-Sent Event, as the contract asks. The id line lets a
    browser that reconnects say where it stopped."""
    return f"id: evt_{number:03d}\ndata: {data_json}\n\n"


async def stream_events(
    latest: Callable[[], int],
    read_after: Callable[[int], list[tuple[int, str]]],
    after_id: int | None,
    settings: StreamSettings,
) -> AsyncIterator[str]:
    """Send new events as they appear.

    A new connection starts from now. A reconnecting browser sends the last id
    it saw, and the stream resumes after it. The database reads run in a worker
    thread so they never block the server.
    """
    if after_id is None:
        after_id = await asyncio.to_thread(latest)
    started = last_sent = time.monotonic()
    yield ": connected\n\n"
    while True:
        batch = await asyncio.to_thread(read_after, after_id)
        for number, data in batch:
            after_id = number
            last_sent = time.monotonic()
            yield sse_message(number, data)
        now = time.monotonic()
        if now - last_sent >= settings.ping_seconds:
            last_sent = now
            yield ": ping\n\n"
        if settings.max_seconds is not None and now - started >= settings.max_seconds:
            return
        if len(batch) < BATCH:  # a full batch means there may be more waiting
            await asyncio.sleep(settings.poll_seconds)
