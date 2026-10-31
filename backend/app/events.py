"""Tiny in-process pub/sub for Server-Sent Events (GET /api/stream).

Each open stream subscribes with its own asyncio.Queue. publish() can be called from
any thread (sync endpoints run in a thread pool), so it hands each message to the
subscriber's event loop with call_soon_threadsafe. A slow client whose queue is full
just misses messages; it never blocks the app.
"""
import asyncio
import json
from collections.abc import AsyncIterator

from app import config

_subscribers: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []


def format_sse(event: str, data) -> str:
    """One SSE message: `event: <name>` + a JSON `data:` line + blank line."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def has_subscribers() -> bool:
    return bool(_subscribers)


def subscribe() -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append((asyncio.get_running_loop(), queue))
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    _subscribers[:] = [(loop, q) for loop, q in _subscribers if q is not queue]


def _offer(queue: asyncio.Queue, message: str) -> None:
    if not queue.full():
        queue.put_nowait(message)


def publish(event: str, data) -> None:
    """Send an event to every open stream (safe to call from any thread)."""
    message = format_sse(event, data)
    for loop, queue in list(_subscribers):
        try:
            loop.call_soon_threadsafe(_offer, queue, message)
        except RuntimeError:  # that stream's event loop is gone
            unsubscribe(queue)


async def stream(first_message: str) -> AsyncIterator[str]:
    """Messages for one client: `first_message`, then published events as they arrive,
    with a keep-alive comment when idle so proxies and browsers keep the connection."""
    queue = subscribe()
    try:
        yield first_message
        while True:
            try:
                yield await asyncio.wait_for(queue.get(), timeout=config.STREAM_KEEPALIVE_SEC)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    finally:
        unsubscribe(queue)
