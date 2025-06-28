from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc, text
from ..db import SessionLocal
from ..schemas import Transaction as TransactionSchema
from ..models import Transaction as TransactionModel
from typing import Any, Optional
from datetime import datetime

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
    client_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("transaction_date"),
    sort: Optional[str] = Query("desc"),
    year: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),  # YYYY-MM-DD
    end_date: Optional[str] = Query(None),  # YYYY-MM-DD
) -> Any:
    """
    List transactions with optional filtering, search, sorting, and date filtering.
    - client_id: filter by client
    - search: filter by description or payee (case-insensitive, partial match)
    - sort_by: column to sort by (default: transaction_date)
    - sort: 'asc' or 'desc' (default: desc)
    - year: filter by year (transaction_date)
    - start_date, end_date: filter by date range (transaction_date)
    """
    query = db.query(TransactionModel)

    # Filtering by client_id
    if client_id:
        query = query.filter(TransactionModel.client_id == client_id)

    # Search by description or payee
    if search:
        like_str = f"%{search}%"
        query = query.filter(
            or_(
                TransactionModel.description.ilike(like_str),
                TransactionModel.payee.ilike(like_str),
            )
        )

    # Date filtering
    if year:
        query = query.filter(
            TransactionModel.transaction_date >= datetime(year, 1, 1),
            TransactionModel.transaction_date <= datetime(year, 12, 31),
        )
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(TransactionModel.transaction_date >= start_dt)
        except Exception:
            pass  # Ignore invalid date
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(TransactionModel.transaction_date <= end_dt)
        except Exception:
            pass  # Ignore invalid date

    # Sorting
    valid_sort_columns = {
        "transaction_date": TransactionModel.transaction_date,
        "amount": TransactionModel.amount,
        "category": TransactionModel.category,
        "source": TransactionModel.source,
        "payee": TransactionModel.payee,
        "parser_name": TransactionModel.parser_name,
        "description": TransactionModel.description,
        "account_number": TransactionModel.account_number,
        "client_id": TransactionModel.client_id,
        # Add more columns as needed
    }
    sort_col = valid_sort_columns.get(sort_by, TransactionModel.transaction_date)
    sort_dir = desc if sort == "desc" else asc
    query = query.order_by(sort_dir(sort_col))

    total = query.count()
    transactions = query.offset(offset).limit(limit).all()
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
