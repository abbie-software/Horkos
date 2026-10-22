from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.services.oath_store import get_latest_oath, save_oath

DEMO_EMAIL = "amara@example.com"
DEMO_OATH = (
    "Spend up to $50 per job and $100 per day. Only on coding work. "
    "Ask me before anything over $30, and always ask me about a seller "
    "I have not used before."
)


def seed() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            user = User(email=DEMO_EMAIL, name="Amara")
            db.add(user)
            db.flush()
            print("Created demo user Amara")
        if get_latest_oath(db, user.id) is None:
            save_oath(db, user.id, DEMO_OATH)
            print("Saved the demo oath")
        db.commit()


if __name__ == "__main__":
    seed()