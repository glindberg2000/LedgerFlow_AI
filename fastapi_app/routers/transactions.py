from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..schemas import Transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[Transaction])
def list_transactions(db: Session = Depends(get_db)):
    # Placeholder: Implement transaction listing logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Listing transactions not implemented yet.",
    )


@router.post("/", response_model=Transaction)
def create_transaction(transaction: Transaction, db: Session = Depends(get_db)):
    # Placeholder: Implement transaction creation logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transaction creation not implemented yet.",
    )
