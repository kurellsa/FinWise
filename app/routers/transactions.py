from datetime import date as date_type
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import Transaction
from auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/transactions", response_class=HTMLResponse)
def transactions_page(
    request: Request,
    account: str = Query(default=""),
    category: str = Query(default=""),
    search: str = Query(default=""),
    date_from: str = Query(default=""),
    date_to: str = Query(default=""),
    db: Session = Depends(get_db),
):
    user_id, username = require_auth(request)

    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if account:
        query = query.filter(Transaction.account == account)
    if category:
        query = query.filter(Transaction.category == category)
    if search:
        query = query.filter(Transaction.description.ilike(f"%{search}%"))
    if date_from:
        query = query.filter(Transaction.date >= date_type.fromisoformat(date_from))
    if date_to:
        query = query.filter(Transaction.date <= date_type.fromisoformat(date_to))

    txns = query.order_by(Transaction.date.desc()).limit(500).all()
    total_shown = len(txns)
    total_amount = sum(t.amount for t in txns)

    accounts = [
        r[0] for r in
        db.query(Transaction.account)
        .filter(Transaction.user_id == user_id)
        .distinct()
        .all()
    ]
    categories = [
        r[0] for r in
        db.query(Transaction.category)
        .filter(Transaction.user_id == user_id)
        .distinct()
        .order_by(Transaction.category)
        .all()
    ]

    # Build export URL with same filters
    params = "&".join(
        f"{k}={v}" for k, v in
        [("account", account), ("category", category), ("search", search),
         ("date_from", date_from), ("date_to", date_to)] if v
    )
    export_url = f"/export/filtered.csv?{params}" if params else "/export/transactions.csv"

    return templates.TemplateResponse(
        request,
        "transactions.html",
        {
            "transactions": txns,
            "accounts": accounts,
            "categories": categories,
            "selected_account": account,
            "selected_category": category,
            "search": search,
            "date_from": date_from,
            "date_to": date_to,
            "total_shown": total_shown,
            "total_amount": round(total_amount, 2),
            "export_url": export_url,
            "username": username,
        },
    )
