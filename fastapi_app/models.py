from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    Date,
    ForeignKey,
    Numeric,
    Text,
    DateTime,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Transaction(Base):
    __tablename__ = "profiles_transaction"
    id = Column(Integer, primary_key=True, index=True)
    transaction_date = Column(Date)
    amount = Column(Numeric)
    description = Column(String)
    category = Column(String)
    client_id = Column(Integer)
    account_number = Column(String)
    file_path = Column(String)
    transaction_id = Column(String)
    transaction_type = Column(String)
    # Add more fields as needed from the actual schema


class User(Base):
    __tablename__ = "auth_user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    email = Column(String)
    is_active = Column(Integer)
    is_staff = Column(Integer)
    is_superuser = Column(Integer)
    date_joined = Column(Date)
    last_login = Column(Date)


class StatementFile(Base):
    __tablename__ = "profiles_uploadedfile"
    id = Column(Integer, primary_key=True, index=True)
    # Add fields as needed


# Account and Statement models are omitted for now, as dashboard metrics do not require them.
