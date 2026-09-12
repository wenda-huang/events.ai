from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services.cluster import run_cluster
from app.services.scan import run_scan

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/scan")
def trigger_scan(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_scan(db)


@router.post("/cluster")
def trigger_cluster(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_cluster(db)
