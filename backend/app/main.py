from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.routes import auth, imports, loans, manager, officer, outcomes, sync

app = FastAPI(title="Kisht")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(imports.router)
app.include_router(officer.router)
app.include_router(loans.router)
app.include_router(outcomes.router)
app.include_router(sync.router)
app.include_router(manager.router)


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("select 1"))
    except Exception:
        raise HTTPException(503, "database unreachable")
    return {"status": "ok"}
