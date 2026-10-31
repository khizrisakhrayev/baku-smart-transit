"""Live stream (Server-Sent Events)."""
import asyncio
import json
import threading

from fastapi.testclient import TestClient

from app import anomaly, config, events, simulator
from app.main import app
from app.routes_data import ROUTES
from app.store import Store, store


def parse(message: str) -> tuple[str, object]:
    lines = dict(line.split(": ", 1) for line in message.strip().splitlines())
    return lines["event"], json.loads(lines["data"])


def test_format_sse():
    assert events.format_sse("alert", {"id": 1}) == 'event: alert\ndata: {"id": 1}\n\n'


def test_stream_sends_first_message_then_published_events():
    async def scenario():
        gen = events.stream(events.format_sse("buses", []))
        first = await gen.__anext__()
        db = Store()
        nxt = asyncio.ensure_future(gen.__anext__())
        await asyncio.sleep(0)  # let the stream wait on its queue
        alert = db.create_alert("5", anomaly.ALERT_MESSAGE)
        created = await asyncio.wait_for(nxt, 1)
        nxt = asyncio.ensure_future(gen.__anext__())
        db.resolve_alert(alert.id)
        resolved = await asyncio.wait_for(nxt, 1)
        await gen.aclose()
        return first, created, resolved

    first, created, resolved = asyncio.run(scenario())
    assert parse(first) == ("buses", [])
    event, data = parse(created)
    assert event == "alert" and data["action"] == "created" and data["alert"]["route_id"] == "5"
    assert parse(resolved)[1]["action"] == "resolved"
    assert not events.has_subscribers()  # closed stream unsubscribed


def test_publish_from_another_thread():
    async def scenario():
        gen = events.stream("first")
        await gen.__anext__()
        nxt = asyncio.ensure_future(gen.__anext__())
        await asyncio.sleep(0)
        threading.Thread(target=events.publish, args=("buses", [1, 2])).start()
        message = await asyncio.wait_for(nxt, 1)
        await gen.aclose()
        return message

    assert parse(asyncio.run(scenario())) == ("buses", [1, 2])


def test_keep_alive_when_idle(monkeypatch):
    monkeypatch.setattr(config, "STREAM_KEEPALIVE_SEC", 0.01)

    async def scenario():
        gen = events.stream("first")
        await gen.__anext__()
        message = await asyncio.wait_for(gen.__anext__(), 1)
        await gen.aclose()
        return message

    assert asyncio.run(scenario()) == ": keep-alive\n\n"


def test_resolving_twice_publishes_once():
    async def scenario():
        db = Store()
        alert = db.create_alert("5", anomaly.ALERT_MESSAGE)
        gen = events.stream("first")
        await gen.__anext__()  # now subscribed
        db.resolve_alert(alert.id)
        db.resolve_alert(alert.id)  # already resolved: no event
        await asyncio.sleep(0.01)   # let the queued deliveries run
        queued = events._subscribers[0][1].qsize()
        await gen.aclose()
        return queued

    assert asyncio.run(scenario()) == 1


def test_stream_endpoint_starts_with_bus_positions():
    store.reset()
    simulator.seed(store, ROUTES)
    with TestClient(app).stream("GET", "/api/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        lines = []
        for line in response.iter_lines():
            if not line:
                break
            lines.append(line)
    event, buses = parse("\n".join(lines))
    assert event == "buses"
    assert len(buses) == len(ROUTES) * config.BUSES_PER_ROUTE
