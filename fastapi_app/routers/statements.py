from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..schemas import Statement

router = APIRouter(prefix="/statements", tags=["statements"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[Statement])
def list_statements(db: Session = Depends(get_db)):
    # Placeholder: Implement statement listing logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Listing statements not implemented yet.",
    )


@router.post("/", response_model=Statement)
def create_statement(statement: Statement, db: Session = Depends(get_db)):
    # Placeholder: Implement statement creation logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Statement creation not implemented yet.",
    )
