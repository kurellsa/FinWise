import json
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import UserProfile
from auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _get_or_create_profile(db: Session, user_id: int) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    user_id, username = require_auth(request)
    profile = _get_or_create_profile(db, user_id)
    debts = json.loads(profile.outstanding_debts or "[]")
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"profile": profile, "debts": debts, "username": username},
    )


@router.post("/settings", response_class=HTMLResponse)
def settings_save(
    request: Request,
    alert_threshold: float = Form(500.0),
    emergency_fund_target: float = Form(0.0),
    monthly_buffer: float = Form(200.0),
    debt_names: list[str] = Form(default=[]),
    debt_balances: list[str] = Form(default=[]),
    debt_rates: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    user_id, username = require_auth(request)
    profile = _get_or_create_profile(db, user_id)
    profile.alert_threshold = alert_threshold
    profile.emergency_fund_target = emergency_fund_target
    profile.monthly_buffer = monthly_buffer

    debts = []
    for name, balance, rate in zip(debt_names, debt_balances, debt_rates):
        name = name.strip()
        if not name:
            continue
        try:
            debts.append({
                "name": name,
                "balance": float(balance or 0),
                "rate": float(rate or 0),
            })
        except ValueError:
            continue
    profile.outstanding_debts = json.dumps(debts)

    db.commit()
    return RedirectResponse(url="/settings?saved=1", status_code=303)
