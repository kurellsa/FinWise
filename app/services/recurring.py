"""
Detects recurring payments from transaction history.
A transaction is considered recurring if the same normalized description
appears in at least 2 of the last 3 calendar months.
"""
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from models import Transaction
import re


def _normalize(description: str) -> str:
    """Strip trailing digits/IDs to group merchant variants together."""
    d = description.upper().strip()
    d = re.sub(r'\s+\d[\d\s\-\*#]+$', '', d)   # trailing ref numbers
    d = re.sub(r'\s{2,}', ' ', d)
    return d.strip()


def detect_recurring(db: Session) -> list[dict]:
    """
    Returns list of detected recurring payments:
      {description, avg_amount, months_seen, estimated_monthly}
    Only expenses (amount < 0) are considered.
    """
    latest = db.query(func.max(Transaction.date)).scalar()
    if latest is None:
        return []

    # Build set of the 3 most recent months as (year, month) tuples
    months = []
    y, m = latest.year, latest.month
    for _ in range(3):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1

    # Fetch transactions from those 3 months (expenses only)
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.amount < 0,
            Transaction.date >= f"{months[-1][0]}-{months[-1][1]:02d}-01",
        )
        .all()
    )

    # Group by normalized description → {(year,month): [amounts]}
    groups: dict[str, dict[tuple, list[float]]] = defaultdict(lambda: defaultdict(list))
    for t in txns:
        key = _normalize(t.description)
        ym = (t.date.year, t.date.month)
        if ym in months:
            groups[key][ym].append(abs(t.amount))

    recurring = []
    for desc, month_data in groups.items():
        months_seen = len(month_data)
        if months_seen < 2:
            continue
        all_amounts = [a for amounts in month_data.values() for a in amounts]
        avg_amount = round(sum(all_amounts) / len(all_amounts), 2)
        recurring.append({
            "description": desc,
            "avg_amount": avg_amount,
            "months_seen": months_seen,
            "estimated_monthly": avg_amount,
        })

    # Sort by amount descending
    recurring.sort(key=lambda x: -x["avg_amount"])
    return recurring
