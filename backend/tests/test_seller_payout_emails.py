from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.models import Seller
from app.scripts.seed import seed_demo_data, seller_email_overrides


def fresh_session():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def email_of(db, slug):
    return db.scalar(select(Seller).where(Seller.slug == slug)).paypal_email


def test_the_overrides_are_read_from_the_setting(monkeypatch):
    monkeypatch.setattr(
        settings,
        "seller_paypal_emails",
        " sel_nova = Nova@Personal.example.com , sel_kip=kip@personal.example.com,broken,=x,sel_zed=",
    )
    assert seller_email_overrides() == {
        "sel_nova": "nova@personal.example.com",
        "sel_kip": "kip@personal.example.com",
    }


def test_without_the_setting_the_made_up_emails_stay(monkeypatch):
    monkeypatch.setattr(settings, "seller_paypal_emails", "")
    with fresh_session() as db:
        seed_demo_data(db)
        assert email_of(db, "sel_nova") == "nova-seller@example.com"


def test_a_real_sandbox_email_replaces_the_made_up_one(monkeypatch):
    monkeypatch.setattr(settings, "seller_paypal_emails", "sel_nova=nova@personal.example.com")
    with fresh_session() as db:
        seed_demo_data(db)
        assert email_of(db, "sel_nova") == "nova@personal.example.com"
        assert email_of(db, "sel_kip") == "kip-seller@example.com"


def test_seeding_again_updates_sellers_that_already_exist(monkeypatch):
    monkeypatch.setattr(settings, "seller_paypal_emails", "")
    with fresh_session() as db:
        seed_demo_data(db)
        monkeypatch.setattr(
            settings, "seller_paypal_emails", "sel_kip=kip@personal.example.com"
        )
        assert seed_demo_data(db) == ["PayPal email for Kip Codes"]
        assert email_of(db, "sel_kip") == "kip@personal.example.com"
        assert seed_demo_data(db) == []