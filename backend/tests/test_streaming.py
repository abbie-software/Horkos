import asyncio
import time

from app.services.streaming import (
    BATCH,
    StreamSettings,
    parse_event_number,
    sse_message,
    stream_events,
)


async def gather(stream):
    return [chunk async for chunk in stream]


def run(events, after_id, ping=15.0, max_seconds=0.15):
    def latest():
        return max((number for number, _ in events), default=0)

    def read_after(after):
        return [(n, data) for n, data in events if n > after][:BATCH]

    settings = StreamSettings(poll_seconds=0.01, ping_seconds=ping, max_seconds=max_seconds)
    return asyncio.run(gather(stream_events(latest, read_after, after_id, settings)))


def data_chunks(chunks):
    return [c for c in chunks if c.startswith("id:")]


def test_event_ids_are_parsed_strictly():
    assert parse_event_number("evt_12") == 12
    assert parse_event_number(" evt_3 ") == 3
    for bad in (None, "", "12", "pay_12", "evt_", "evt_x", "evt_-1"):
        assert parse_event_number(bad) is None


def test_a_message_is_one_unnamed_event_with_an_id_line():
    assert sse_message(7, '{"a": 1}') == 'id: evt_007\ndata: {"a": 1}\n\n'


def test_a_new_connection_starts_from_now_and_sees_nothing_old():
    chunks = run([(1, "old"), (2, "older")], after_id=None)
    assert chunks[0] == ": connected\n\n"
    assert data_chunks(chunks) == []


def test_a_reconnecting_browser_resumes_after_the_last_id_it_saw():
    chunks = run([(1, "a"), (2, "b"), (3, "c")], after_id=1)
    assert data_chunks(chunks) == ["id: evt_002\ndata: b\n\n", "id: evt_003\ndata: c\n\n"]


def test_all_events_can_be_replayed_from_the_start():
    chunks = run([(1, "a"), (2, "b")], after_id=0)
    assert len(data_chunks(chunks)) == 2


def test_events_that_appear_while_connected_are_sent():
    calls = {"count": 0}

    def latest():
        return 2

    def read_after(after):
        calls["count"] += 1
        return [(3, "new")] if calls["count"] == 2 and after < 3 else []

    settings = StreamSettings(poll_seconds=0.01, max_seconds=0.2)
    chunks = asyncio.run(gather(stream_events(latest, read_after, None, settings)))
    assert data_chunks(chunks) == ["id: evt_003\ndata: new\n\n"]


def test_a_keep_alive_comment_is_sent_when_nothing_happens():
    chunks = run([], after_id=None, ping=0.03, max_seconds=0.2)
    assert ": ping\n\n" in chunks


def test_a_large_backlog_is_delivered_in_full():
    events = [(n, "x") for n in range(1, BATCH + 6)]
    chunks = run(events, after_id=0)
    assert len(data_chunks(chunks)) == BATCH + 5


def test_the_stream_ends_when_it_is_told_to_stop():
    started = time.perf_counter()
    run([], after_id=None, max_seconds=0.1)
    assert time.perf_counter() - started < 2
