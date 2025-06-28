from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..schemas import User
from ..utils import auth
from pydantic import EmailStr
from typing import Dict

router = APIRouter(prefix="/users", tags=["users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# In-memory user store for demo purposes
fake_users: Dict[str, dict] = {}


@router.post("/register", response_model=User)
def register_user(user: User, db: Session = Depends(get_db)):
    if user.email in fake_users:
        raise HTTPException(status_code=400, detail="Email already registered.")
    fake_users[user.email] = user.dict()
    return user


@router.post("/login")
def login_user(email: EmailStr, password: str):
    user = fake_users.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    # Password check skipped for demo
    token = auth.create_access_token({"sub": email})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/create-admin", response_model=User)
def create_admin_user(user: User, db: Session = Depends(get_db)):
    if user.email in fake_users:
        raise HTTPException(status_code=400, detail="Email already registered.")
    user_dict = user.dict()
    user_dict["is_admin"] = True
    fake_users[user.email] = user_dict
    return User(**user_dict)


@router.get("/all", response_model=list[User])
def list_users():
    return [User(**u) for u in fake_users.values()]
