import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Oath, User
from app.services.oath import OathParseError
from app.services.oath_store import get_latest_oath, oath_to_out, save_oath

OATH = "Spend up to $50 per job and $100 per day. Only on coding work."


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                User(id=1, email="amara@example.com", name="Amara"),
                User(id=2, email="other@example.com", name="Other"),
            ]
        )
        session.commit()
        yield session


def count_oaths(db):
    return db.scalar(select(func.count()).select_from(Oath))


def test_nothing_saved_yet(db):
    assert get_latest_oath(db, 1) is None


def test_saved_oath_comes_back_on_the_next_load(db):
    save_oath(db, 1, OATH)
    db.commit()
    loaded = oath_to_out(get_latest_oath(db, 1))
    assert loaded.raw_text == OATH
    assert loaded.policy.per_job_cap_cents == 5000
    assert loaded.policy.allowed_categories == ["coding"]
    assert loaded.id.startswith("oath_")


def test_latest_save_wins_and_history_is_kept(db):
    save_oath(db, 1, OATH)
    save_oath(db, 1, "Spend up to $20 per job and $40 per day.")
    db.commit()
    assert get_latest_oath(db, 1).text.startswith("Spend up to $20")
    assert count_oaths(db) == 2


def test_a_bad_oath_saves_nothing(db):
    with pytest.raises(OathParseError):
        save_oath(db, 1, "Spend up to $50 per job.")
    assert count_oaths(db) == 0


def test_users_do_not_see_each_others_oaths(db):
    save_oath(db, 1, OATH)
    db.commit()
    assert get_latest_oath(db, 2) is None


def test_updated_at_is_utc(db):
    save_oath(db, 1, OATH)
    db.commit()
    stamp = oath_to_out(get_latest_oath(db, 1)).updated_at
    assert stamp.utcoffset().total_seconds() == 0