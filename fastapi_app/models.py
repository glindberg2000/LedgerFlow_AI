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
    parsed_data = Column(Text)  # jsonb, but use Text for now
    client_id = Column(String)
    account_number = Column(String)
    file_path = Column(String)
    normalized_amount = Column(Numeric)
    source = Column(String)
    statement_end_date = Column(Date)
    statement_start_date = Column(Date)
    transaction_id = Column(Integer)
    transaction_type = Column(String)
    normalized_description = Column(Text)
    payee = Column(String)
    confidence = Column(String)
    reasoning = Column(Text)
    business_context = Column(Text)
    questions = Column(Text)
    classification_method = Column(String)
    payee_extraction_method = Column(String)
    classification_type = Column(String)
    worksheet = Column(String)
    business_percentage = Column(Integer)
    payee_reasoning = Column(Text)
    transaction_hash = Column(String)
    parser_name = Column(String)
    needs_account_number = Column(Boolean)
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


class BusinessProfile(Base):
    __tablename__ = "profiles_businessprofile"
    client_id = Column(String(255), primary_key=True, index=True)
    business_type = Column(Text)
    business_description = Column(Text)
    contact_info = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    common_expenses = Column(Text)
    industry_keywords = Column(Text)
    category_patterns = Column(Text)
    industry_insights = Column(Text)
    category_hierarchy = Column(Text)  # jsonb, but use Text for now
    business_context = Column(Text)
    custom_categories = Column(Text)  # jsonb, but use Text for now
    location = Column(String(200))
    business_rules = Column(Text)
    ai_generated_profile = Column(Text)  # jsonb, but use Text for now


class Agent(Base):
    __tablename__ = "profiles_agent"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    purpose = Column(Text, nullable=False)
    prompt = Column(Text, nullable=False)
    llm_id = Column(Integer)


class Tool(Base):
    __tablename__ = "profiles_tool"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    module_path = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


# Account and Statement models are omitted for now, as dashboard metrics do not require them.
