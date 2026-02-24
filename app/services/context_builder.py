"""
Builds an anonymized financial snapshot from the database for AI queries.
Claude never sees raw PII — only aggregated numbers and generic labels.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date
from models import Transaction


def build_snapshot(db: Session) -> dict:
    # Use the most recent month present in the data, not today's date.
    # This ensures historical CSVs work correctly.
    latest = db.query(func.max(Transaction.date)).scalar()
    if latest is None:
        return {"error": "No transactions loaded yet.", "total_transactions_loaded": 0}

    ref_month = latest.month
    ref_year = latest.year

    # Transactions in the most recent data month
    month_txns = (
        db.query(Transaction)
        .filter(
            extract("month", Transaction.date) == ref_month,
            extract("year", Transaction.date) == ref_year,
        )
        .all()
    )

    month_income = sum(t.amount for t in month_txns if t.amount > 0)
    month_expenses = sum(t.amount for t in month_txns if t.amount < 0)

    # Spending by category (most recent month)
    category_totals: dict[str, float] = {}
    for t in month_txns:
        if t.amount < 0:
            category_totals[t.category] = category_totals.get(t.category, 0) + abs(t.amount)

    # All-time spending by category
    all_txns = db.query(Transaction).all()
    all_category_totals: dict[str, float] = {}
    for t in all_txns:
        if t.amount < 0:
            all_category_totals[t.category] = all_category_totals.get(t.category, 0) + abs(t.amount)

    # Balance per account (sum of all time)
    account_balances: dict[str, float] = {}
    rows = db.query(Transaction.account, func.sum(Transaction.amount)).group_by(Transaction.account).all()
    for i, (acct, total) in enumerate(rows):
        label = f"Account-{chr(65 + i)}"
        account_balances[label] = round(total, 2)

    # Date range of loaded data
    earliest = db.query(func.min(Transaction.date)).scalar()
    total_txns = db.query(func.count(Transaction.id)).scalar()

    # Individual transactions for AI reference (sorted by date desc, capped at 100)
    recent_txns = (
        db.query(Transaction)
        .order_by(Transaction.date.desc())
        .limit(100)
        .all()
    )
    transactions_list = [
        {
            "date": str(t.date),
            "description": t.description,
            "amount": round(t.amount, 2),
            "category": t.category,
        }
        for t in recent_txns
    ]

    # Data-driven smart insights (no AI call needed for dashboard)
    net = round(month_income + month_expenses, 2)
    period = latest.strftime("%B %Y")
    insights: list[str] = []
    if all_category_totals:
        top_cat = max(all_category_totals, key=all_category_totals.get)
        insights.append(f"Top spending category: {top_cat} (${all_category_totals[top_cat]:,.0f} all-time)")
    if net >= 0:
        insights.append(f"Saving ${net:,.0f} in {period}")
    else:
        insights.append(f"Over budget by ${abs(net):,.0f} in {period}")
    insights.append(f"{total_txns} transactions across {len(account_balances)} account(s)")
    if all_category_totals:
        insights.append(f"Spending tracked in {len(all_category_totals)} categories")

    return {
        "data_range": {"from": str(earliest), "to": str(latest)},
        "accounts": account_balances,
        "insights": insights,
        "latest_month": {
            "period": f"{latest.strftime('%B %Y')}",
            "income": round(month_income, 2),
            "expenses": round(abs(month_expenses), 2),
            "net": round(month_income + month_expenses, 2),
            "by_category": {k: round(v, 2) for k, v in sorted(category_totals.items(), key=lambda x: -x[1])},
        },
        "all_time": {
            "total_expenses": round(sum(all_category_totals.values()), 2),
            "by_category": {k: round(v, 2) for k, v in sorted(all_category_totals.items(), key=lambda x: -x[1])},
        },
        "transactions": transactions_list,
        "total_transactions_loaded": total_txns,
    }
