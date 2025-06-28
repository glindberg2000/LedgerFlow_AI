from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import BusinessProfile as BusinessProfileModel
from ..schemas import BusinessProfile as BusinessProfileSchema

router = APIRouter(prefix="/business-profiles", tags=["business-profiles"])

"""Business Profiles API: Returns business clients managed by the system (from profiles_businessprofile)."""


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[BusinessProfileSchema])
def list_business_profiles(db: Session = Depends(get_db)):
    profiles = db.query(BusinessProfileModel).all()
    return [
        BusinessProfileSchema(
            client_id=p.client_id,
            business_type=p.business_type,
            business_description=p.business_description,
            contact_info=p.contact_info,
            location=p.location,
            created_at=p.created_at.date() if p.created_at else None,
            updated_at=p.updated_at.date() if p.updated_at else None,
        )
        for p in profiles
    ]
