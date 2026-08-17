from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import SessionLocal, engine, init_schema, ping_db
from app.routers import auth, movies
from app.services.seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_schema()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield


app = FastAPI(title="OTT Movies API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(movies.router)


@app.get("/health")
def health():
    ping_db()
    return {"ok": True, "dialect": engine.dialect.name}
