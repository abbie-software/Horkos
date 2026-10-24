from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_buyer_agent, get_current_user, get_funder, get_intent_checker
from app.errors import ApiError
from app.models import Seller, User
from app.schemas.jobs import JobCreated, JobIn
from app.services.buyer_agent import BuyerAgent
from app.services.funding import Funder
from app.services.guard import IntentChecker
from app.services.jobs import run_job
from app.services.views import job_to_out, load_payment_out

router = APIRouter(tags=["jobs"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Agent = Annotated[BuyerAgent, Depends(get_buyer_agent)]
Checker = Annotated[IntentChecker, Depends(get_intent_checker)]
FunderDep = Annotated[Funder, Depends(get_funder)]


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