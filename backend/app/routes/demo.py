from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import (
    check_demo_enabled,
    get_attack_pause,
    get_current_user,
    get_funder,
    get_runner,
    get_session_factory,
)
from app.schemas.demo import AttackAccepted, AttackType
from app.services.activity import record_event
from app.services.attack_scripts import ATTACKS
from app.services.attacks import run_attack
from app.services.demo import attacks_so_far, reset_demo_data
from app.services.funding import Funder
from app.services.sandbox import SandboxResult

router = APIRouter(
    tags=["demo"],
    dependencies=[Depends(get_current_user), Depends(check_demo_enabled)],
)

DbSession = Annotated[Session, Depends(get_db)]
Factory = Annotated[Callable[[], Session], Depends(get_session_factory)]
Runner = Annotated[Callable[[str, str], SandboxResult], Depends(get_runner)]
FunderDep = Annotated[Funder, Depends(get_funder)]
Pause = Annotated[float, Depends(get_attack_pause)]


@router.post("/demo/attack/{attack_type}", response_model=AttackAccepted, status_code=202)
def start_attack(
    attack_type: AttackType,
    background: BackgroundTasks,
    db: DbSession,
    factory: Factory,
    runner: Runner,
    funder: FunderDep,
    pause: Pause,
):
    """Play the Red Team: a bad agent tries something and the Guard responds.
    The outcome shows up on the Live Feed."""
    number = attacks_so_far(db) + 1
    record_event(
        db,
        "demo.attack_started",
        ATTACKS[attack_type].message,
        {"attack": attack_type},
    )
    db.commit()
    background.add_task(run_attack, factory, attack_type, runner, funder, pause)
    return AttackAccepted(attack_id=f"atk_{4000 + number}", type=attack_type)


@router.post("/demo/reset", status_code=204)
def reset_demo(db: DbSession):
    """Restore the starting demo data."""
    reset_demo_data(db)
    record_event(db, "demo.reset", "The demo was reset to its starting data.", {})
    db.commit()
    return Response(status_code=204)
