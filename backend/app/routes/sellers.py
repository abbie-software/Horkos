from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Seller
from app.schemas.sellers import SellerList
from app.services.views import seller_to_out

router = APIRouter(tags=["sellers"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/sellers",
    response_model=SellerList,
    dependencies=[Depends(get_current_user)],
)
def list_sellers(db: DbSession):
    sellers = db.scalars(select(Seller).order_by(Seller.id)).all()
    items = [seller_to_out(seller) for seller in sellers]
    return SellerList(items=items, total=len(items))