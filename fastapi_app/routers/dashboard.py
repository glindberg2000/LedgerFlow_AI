from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Transaction, User, StatementFile

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/transaction_count")
def transaction_count(db: Session = Depends(get_db)):
    return {"transaction_count": db.query(Transaction).count()}


@router.get("/client_count")
def client_count(db: Session = Depends(get_db)):
    return {"client_count": db.query(User).count()}


@router.get("/statement_count")
def statement_count(db: Session = Depends(get_db)):
    return {"statement_count": db.query(StatementFile).count()}


@router.get("/batch_status")
def batch_status(db: Session = Depends(get_db)):
    # Placeholder for batch status logic
    return {"status": "ok", "message": "Batch status not yet implemented"}


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    return {
        "transaction_count": db.query(Transaction).count(),
        "client_count": db.query(User).count(),
        "statement_count": db.query(StatementFile).count(),
        "batch_status": {"status": "ok", "message": "Batch status not yet implemented"},
    }
