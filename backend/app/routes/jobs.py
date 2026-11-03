from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import (
    get_buyer_agent,
    get_current_user,
    get_funder,
    get_intent_checker,
    get_runner,
    get_session_factory,
)
from app.errors import ApiError
from app.models import Job, PaymentState, Seller, Submission, User
from app.schemas.jobs import (
    JobCreated,
    JobIn,
    JobList,
    JobStatus,
    SubmissionAccepted,
    SubmissionIn,
)
from app.services.buyer_agent import BuyerAgent
from app.services.funding import Funder
from app.services.guard import IntentChecker
from app.services.jobs import run_job
from app.services.sandbox import SandboxResult
from app.services.verification import payment_for_job, verify_submission
from app.services.views import job_to_out, load_payment_out, seller_public_id

router = APIRouter(tags=["jobs"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Agent = Annotated[BuyerAgent, Depends(get_buyer_agent)]
Checker = Annotated[IntentChecker, Depends(get_intent_checker)]
FunderDep = Annotated[Funder, Depends(get_funder)]
Factory = Annotated[Callable[[], Session], Depends(get_session_factory)]
Runner = Annotated[Callable[[str, str], SandboxResult], Depends(get_runner)]


def parse_job_id(public_id: str) -> int | None:
    """Turn "job_2003" into 2003. Anything else is not a job ID."""
    prefix, _, number = public_id.partition("_")
    if prefix != "job" or not number.isdigit():
        return None
    return int(number)


@router.post("/jobs", response_model=JobCreated, status_code=201)
def create_job(
    body: JobIn,
    db: DbSession,
    user: CurrentUser,
    agent: Agent,
    checker: Checker,
    funder: FunderDep,
):
    request_text = body.request_text.strip()
    if not request_text:
        raise ApiError(422, "validation_error", "request_text: must not be blank")

    job, payment = run_job(
        db, user, request_text, body.seller_id, agent, checker, funder
    )
    db.commit()
    seller = db.get(Seller, job.seller_id)
    return JobCreated(
        job=job_to_out(job, seller, payment.id),
        payment=load_payment_out(db, payment),
    )

@router.get("/jobs", response_model=JobList)
def list_jobs(
    db: DbSession,
    user: CurrentUser,
    status: JobStatus | None = None,
    seller_id: str | None = None,
):
    """The jobs the caller may see. A seller account sees only its own seller's jobs,
    a buyer sees the jobs they created. The tests' code is never included."""
    query = select(Job).order_by(Job.created_at.desc(), Job.id.desc())
    if user.role == "seller":
        query = query.where(Job.seller_id == user.seller_id)
    else:
        query = query.where(Job.user_id == user.id)
    if status is not None:
        query = query.where(Job.status == status)

    items = []
    for job in db.scalars(query).all():
        seller = db.get(Seller, job.seller_id)
        if seller_id is not None and seller_public_id(seller) != seller_id:
            continue
        payment = payment_for_job(db, job.id)
        items.append(job_to_out(job, seller, payment.id if payment else None))
    return JobList(items=items, total=len(items))


@router.post(
    "/jobs/{job_id}/submission",
    response_model=SubmissionAccepted,
    status_code=202,
  
)
def submit_work(
    job_id: str,
    body: SubmissionIn,
    background: BackgroundTasks,
    user: CurrentUser,
    db: DbSession,
    factory: Factory,
    runner: Runner,
    funder: FunderDep,
):
    """The seller hands in their work. Checking it takes a while, so this
    answers straight away and the result appears on the payment."""
    number = parse_job_id(job_id)
    job = db.get(Job, number) if number is not None else None
    if job is None:
        raise ApiError(404, "not_found", "Job not found.")

    seller = db.get(Seller, job.seller_id)

    if user.role == "seller" and user.seller_id != job.seller_id:
        raise ApiError(
            422, "validation_error", "seller_id: this job belongs to a different seller."
        )
    
    if body.seller_id != seller_public_id(seller):
        raise ApiError(
            422, "validation_error", "seller_id: this job belongs to a different seller."
        )
    if not body.content.strip():
        raise ApiError(422, "validation_error", "content: must not be blank")

    payment = payment_for_job(db, job.id)
    if (
        job.status != "awaiting_work"
        or payment is None
        or payment.state != PaymentState.HELD
    ):
        raise ApiError(409, "invalid_state", "This job is not waiting for work.")
    if not job.test_code:
        raise ApiError(
            409, "invalid_state", "This job has no tests to check the work against."
        )

    submission = Submission(job_id=job.id, seller_id=seller.id, content=body.content)
    db.add(submission)
    db.flush()
    job.status = "verifying"  # a second submission is refused from here on
    db.commit()

    background.add_task(verify_submission, factory, submission.id, runner, funder)
    return SubmissionAccepted(
        submission_id=f"sub_{submission.id}", payment_id=f"pay_{payment.id}"
    )
