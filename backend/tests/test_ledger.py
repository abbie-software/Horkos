import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import PaymentEvent, Seller, User
from app.models import PaymentState as S
from app.services.ledger import (
    ALLOWED_TRANSITIONS,
    InvalidTransition,
    create_payment,
    transition,
)

PATHS = {
    S.RELEASED: [S.APPROVED, S.HELD, S.VERIFIED, S.RELEASED],
    S.REFUNDED: [S.APPROVED, S.HELD, S.REFUNDED],
    S.BLOCKED: [S.BLOCKED],
}


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                User(id=1, email="amara@example.com", name="Amara"),
                Seller(id=1, name="Test Seller", paypal_email="seller@example.com"),
            ]
        )
        session.commit()
        yield session


def new_payment(db):
    return create_payment(
        db, user_id=1, seller_id=1, amount_cents=2000, description="Write a script"
    )


def events_of(db, payment):
    rows = db.scalars(
        select(PaymentEvent)
        .where(PaymentEvent.payment_id == payment.id)
        .order_by(PaymentEvent.id)
    )
    return [(e.from_state, e.to_state) for e in rows]


def walk(db, payment, steps):
    for step in steps:
        transition(db, payment, step, f"moving to {step.value}")


def test_new_payment_starts_proposed_with_an_event(db):
    payment = new_payment(db)
    assert payment.state == S.PROPOSED
    assert events_of(db, payment) == [(None, "proposed")]


def test_happy_path_ends_released_and_logs_every_step(db):
    payment = new_payment(db)
    walk(db, payment, PATHS[S.RELEASED])
    assert payment.state == S.RELEASED
    assert [to for _, to in events_of(db, payment)] == [
        "proposed", "approved", "held", "verified", "released",
    ]


def test_failed_verification_refunds_the_buyer(db):
    payment = new_payment(db)
    walk(db, payment, PATHS[S.REFUNDED])
    assert payment.state == S.REFUNDED


def test_guard_can_block_a_proposal(db):
    payment = new_payment(db)
    walk(db, payment, PATHS[S.BLOCKED])
    assert payment.state == S.BLOCKED


def test_steps_cannot_be_skipped(db):
    payment = new_payment(db)
    with pytest.raises(InvalidTransition):
        transition(db, payment, S.HELD, "skipping approval")
    assert payment.state == S.PROPOSED
    assert events_of(db, payment) == [(None, "proposed")]


@pytest.mark.parametrize("final_state", [S.RELEASED, S.REFUNDED, S.BLOCKED])
def test_final_states_cannot_move(db, final_state):
    payment = new_payment(db)
    walk(db, payment, PATHS[final_state])
    for target in S:
        with pytest.raises(InvalidTransition):
            transition(db, payment, target, "trying to move a finished payment")
    assert payment.state == final_state


def test_a_reason_is_required(db):
    payment = new_payment(db)
    with pytest.raises(ValueError):
        transition(db, payment, S.APPROVED, "   ")
    assert payment.state == S.PROPOSED


@pytest.mark.parametrize("bad_amount", [0, -5, 10.5])
def test_amount_must_be_positive_whole_cents(db, bad_amount):
    with pytest.raises(ValueError):
        create_payment(
            db, user_id=1, seller_id=1, amount_cents=bad_amount, description="x"
        )


def test_every_state_has_a_rule():
    assert set(ALLOWED_TRANSITIONS) == set(S)