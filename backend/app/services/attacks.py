import logging
import time
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, PaymentState, Submission, User
from app.scripts.demo_data import DEMO_USER
from app.services.attack_scripts import (
    ATTACKS,
    BAD_WORK_CODE,
    ScriptedAgent,
    ScriptedChecker,
)
from app.services.funding import Funder
from app.services.jobs import run_job
from app.services.sandbox import SandboxResult
from app.services.verification import verify_submission

log = logging.getLogger(__name__)


def run_attack(
    session_factory: Callable[[], Session],
    attack_type: str,
    runner: Callable[[str, str], SandboxResult],
    funder: Funder,
    pause: float = 1.0,
) -> None:
    """Play an attack through the real Guard, one step at a time.

    This runs in the background after the request was answered. Each step is
    its own transaction, so the Live Feed shows the story as it unfolds.
    """
    script = ATTACKS[attack_type]
    try:
        held_job_id = None
        seller_id = None
        for step in script.steps:
            if pause > 0:
                time.sleep(pause)
            with session_factory() as db:
                user = db.scalar(select(User).where(User.email == DEMO_USER["email"]))
                job, payment = run_job(
                    db,
                    user,
                    step.request_text,
                    step.seller,
                    ScriptedAgent(step),
                    ScriptedChecker(),
                    funder,
                    recipient_email=step.recipient_email,
                )
                db.commit()
                held_job_id = job.id if payment.state == PaymentState.HELD else None
                seller_id = job.seller_id

        if script.hand_in_bad_work and held_job_id is not None:
            if pause > 0:
                time.sleep(pause)
            with session_factory() as db:
                submission = Submission(
                    job_id=held_job_id, seller_id=seller_id, content=BAD_WORK_CODE
                )
                db.add(submission)
                db.flush()
                db.get(Job, held_job_id).status = "verifying"
                db.commit()
                submission_id = submission.id
            verify_submission(session_factory, submission_id, runner, funder)
    except Exception:
        log.exception("The %s attack could not finish", attack_type)
