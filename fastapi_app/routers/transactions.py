from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..schemas import Transaction as TransactionSchema
from ..models import Transaction as TransactionModel
from typing import Any

router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=dict)
def list_transactions(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Any:
    total = db.query(TransactionModel).count()
    transactions = (
        db.query(TransactionModel)
        .order_by(TransactionModel.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    # Return all columns as dicts
    items = []
    for t in transactions:
        items.append(
            {
                "id": t.id,
                "transaction_date": t.transaction_date,
                "amount": float(t.amount) if t.amount is not None else None,
                "description": t.description,
                "category": t.category,
                "parsed_data": t.parsed_data,
                "client_id": t.client_id,
                "account_number": t.account_number,
                "file_path": t.file_path,
                "normalized_amount": (
                    float(t.normalized_amount)
                    if t.normalized_amount is not None
                    else None
                ),
                "source": t.source,
                "statement_end_date": t.statement_end_date,
                "statement_start_date": t.statement_start_date,
                "transaction_id": t.transaction_id,
                "transaction_type": t.transaction_type,
                "normalized_description": t.normalized_description,
                "payee": t.payee,
                "confidence": t.confidence,
                "reasoning": t.reasoning,
                "business_context": t.business_context,
                "questions": t.questions,
                "classification_method": t.classification_method,
                "payee_extraction_method": t.payee_extraction_method,
                "classification_type": t.classification_type,
                "worksheet": t.worksheet,
                "business_percentage": t.business_percentage,
                "payee_reasoning": t.payee_reasoning,
                "transaction_hash": t.transaction_hash,
                "parser_name": t.parser_name,
                "needs_account_number": t.needs_account_number,
            }
        )
    return {"total": total, "items": items, "limit": limit, "offset": offset}


@router.post("/", response_model=TransactionSchema)
def create_transaction(transaction: TransactionSchema, db: Session = Depends(get_db)):
    # Placeholder: Implement transaction creation logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transaction creation not implemented yet.",
    )
