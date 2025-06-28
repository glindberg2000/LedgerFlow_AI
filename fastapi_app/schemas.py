from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import date


class User(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool = True
    is_admin: bool = False


class Account(BaseModel):
    id: int
    name: str
    type: str  # e.g., 'checking', 'credit', 'investment'
    owner_id: int  # User ID
    institution: Optional[str]
    number_last4: Optional[str]


class Transaction(BaseModel):
    id: int
    date: date
    description: str
    amount: float
    category: Optional[str]
    account_id: int
    statement_id: Optional[int]
    raw_text: Optional[str]


class StatementPeriod(BaseModel):
    start: date
    end: date


class Statement(BaseModel):
    id: int
    account_id: int
    period: StatementPeriod
    transactions: List[Transaction] = []
    source: str
    parser_version: str
