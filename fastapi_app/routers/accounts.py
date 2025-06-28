from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..schemas import Account

router = APIRouter(prefix="/accounts", tags=["accounts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[Account])
def list_accounts(db: Session = Depends(get_db)):
    # Placeholder: Implement account listing logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Listing accounts not implemented yet.",
    )


@router.post("/", response_model=Account)
def create_account(account: Account, db: Session = Depends(get_db)):
    # Placeholder: Implement account creation logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Account creation not implemented yet.",
    )
