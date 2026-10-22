from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.errors import ApiError
from app.models import User
from app.schemas.oath import OathOut
from app.services.oath import OathParseError
from app.services.oath_store import get_latest_oath, oath_to_out, save_oath

router = APIRouter(tags=["oath"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class OathIn(BaseModel):
    raw_text: str = Field(max_length=2000)


@router.get("/oath", response_model=OathOut)
def read_oath(db: DbSession, user: CurrentUser):
    oath = get_latest_oath(db, user.id)
    if oath is None:
        raise ApiError(404, "not_found", "You have not saved an oath yet.")
    return oath_to_out(oath)


@router.put("/oath", response_model=OathOut)
def write_oath(body: OathIn, db: DbSession, user: CurrentUser):
    try:
        oath = save_oath(db, user.id, body.raw_text)
    except OathParseError as exc:
        raise ApiError(422, "validation_error", str(exc)) from exc
    db.commit()
    return oath_to_out(oath)