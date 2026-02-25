from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case
import csv
import io

from database import get_db
from models import Transaction
from auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _monthly_summaries(db: Session, user_id: int) -> list[dict]:
    rows = (
        db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            func.sum(
                case((Transaction.amount > 0, Transaction.amount), else_=0)
            ).label("income"),
            func.sum(
                case((Transaction.amount < 0, Transaction.amount), else_=0)
            ).label("expenses"),
        )
        .filter(Transaction.user_id == user_id)
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )

    summaries = []
    for r in rows:
        import calendar
        month_name = calendar.month_abbr[int(r.month)]
        label = f"{month_name} {int(r.year)}"
        income = round(float(r.income or 0), 2)
        expenses = round(abs(float(r.expenses or 0)), 2)
        summaries.append({
            "label": label,
            "year": int(r.year),
            "month": int(r.month),
            "income": income,
            "expenses": expenses,
            "net": round(income - expenses, 2),
        })
    return summaries


def _category_totals(db: Session, user_id: int) -> list[dict]:
    rows = (
        db.query(Transaction.category, func.sum(Transaction.amount).label("total"))
        .filter(Transaction.user_id == user_id, Transaction.amount < 0)
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount))   # most negative first
        .all()
    )
    return [{"category": r.category, "amount": round(abs(float(r.total)), 2)} for r in rows]


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, db: Session = Depends(get_db)):
    user_id, username = require_auth(request)
    summaries = _monthly_summaries(db, user_id)
    categories = _category_totals(db, user_id)
    return templates.TemplateResponse(
        request,
        "reports.html",
        {"summaries": summaries, "categories": categories, "username": username},
    )


@router.get("/export/transactions.csv")
def export_all(request: Request, db: Session = Depends(get_db)):
    user_id, username = require_auth(request)
    txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc())
        .all()
    )
    return _csv_response(txns, "transactions_all.csv")


@router.get("/export/filtered.csv")
def export_filtered(
    request: Request,
    account: str = "",
    category: str = "",
    search: str = "",
    date_from: str = "",
    date_to: str = "",
    db: Session = Depends(get_db),
):
    from datetime import date as date_type
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
    txns = query.order_by(Transaction.date.desc()).all()
    return _csv_response(txns, "transactions_filtered.csv")


def _csv_response(txns: list, filename: str) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Account", "Description", "Category", "Amount"])
    for t in txns:
        writer.writerow([t.date, t.account, t.description, t.category, t.amount])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
