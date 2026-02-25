from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import engine, get_db, Base
from models import Transaction
from routers import upload, transactions, ai, reports, login, settings, register
from services.context_builder import build_snapshot
from auth import get_current_user

import models
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FinWise AI")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(login.router)
app.include_router(register.router)
app.include_router(upload.router)
app.include_router(transactions.router)
app.include_router(ai.router)
app.include_router(reports.router)
app.include_router(settings.router)


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    uploaded: int = 0,
    skipped: int = 0,
    account: str = "",
    db: Session = Depends(get_db),
):
    session = get_current_user(request)
    if not session:
        return RedirectResponse(url="/login", status_code=303)
    user_id, username = session

    snapshot = build_snapshot(db, user_id)
    accounts = [
        r[0] for r in
        db.query(Transaction.account)
        .filter(Transaction.user_id == user_id)
        .distinct()
        .all()
    ]

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "snapshot": snapshot,
            "accounts": accounts,
            "uploaded": uploaded,
            "skipped": skipped,
            "account": account,
            "username": username,
        },
    )
