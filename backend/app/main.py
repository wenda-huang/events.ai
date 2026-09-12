from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, events, jobs, users
from app.seed import seed_if_empty
from app.services.cluster import run_cluster
from app.services.scan import run_scan

scheduler = BackgroundScheduler()


def _job_scan() -> None:
    db = SessionLocal()
    try:
        run_scan(db)
    finally:
        db.close()


def _job_cluster() -> None:
    db = SessionLocal()
    try:
        run_cluster(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    scheduler.add_job(_job_scan, "interval", hours=6, id="scan", replace_existing=True)
    scheduler.add_job(_job_cluster, "interval", hours=6, minutes=15, id="cluster", replace_existing=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="events.ai", lifespan=lifespan)
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(events.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"ok": True, "city": "Pittsburgh"}


@app.get("/config/public")
def public_config():
    tile_url = settings.secret("carto_tile_url") or settings.carto_tile_url
    carto_key = settings.secret("carto_api_key")
    if carto_key:
        separator = "&" if "?" in tile_url else "?"
        tile_url = f"{tile_url}{separator}key={carto_key}"
    return {
        "carto_api_base_url": settings.secret("carto_api_base_url") or settings.carto_api_base_url,
        "tile_url": tile_url,
        "has_carto_key": bool(carto_key),
        "has_querit_key": bool(settings.secret("querit_api_key")),
    }
