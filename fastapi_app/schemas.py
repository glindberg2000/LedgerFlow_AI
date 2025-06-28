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
    transaction_date: Optional[date] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    client_id: Optional[str] = None
    account_number: Optional[str] = None
    file_path: Optional[str] = None
    transaction_id: Optional[str] = None
    transaction_type: Optional[str] = None


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


class BusinessProfile(BaseModel):
    """BusinessProfile represents a business client managed by the system (from profiles_businessprofile)."""

    client_id: str
    business_type: Optional[str] = None
    business_description: Optional[str] = None
    contact_info: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None


class Agent(BaseModel):
    id: int
    name: str
    purpose: Optional[str] = None
    prompt: Optional[str] = None
    llm_id: Optional[int] = None
