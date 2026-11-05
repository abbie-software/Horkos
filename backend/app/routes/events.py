from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.deps import check_stream_token, get_session_factory, get_stream_settings
from app.services.activity import latest_event_id, read_events_after
from app.services.streaming import StreamSettings, parse_event_number, stream_events

router = APIRouter(tags=["events"])

Factory = Annotated[Callable[[], Session], Depends(get_session_factory)]
Settings = Annotated[StreamSettings, Depends(get_stream_settings)]


@router.get("/events", dependencies=[Depends(check_stream_token)])
async def events(request: Request, factory: Factory, settings: Settings):
    """The Live Feed: Server-Sent Events, one unnamed event per message."""
    after_id = parse_event_number(request.headers.get("last-event-id"))
    stream = stream_events(
        lambda: latest_event_id(factory),
        lambda after: read_events_after(factory, after),
        after_id,
        settings,
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
