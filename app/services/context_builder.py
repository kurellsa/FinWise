"""
Builds an anonymized financial snapshot from the database for AI queries.
Claude never sees raw PII — only aggregated numbers and generic labels.
"""
import json
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from models import Transaction, UserProfile
from services.recurring import detect_recurring


def _get_profile(db: Session, user_id: int) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def build_snapshot(db: Session, user_id: int) -> dict:
    # Use the most recent month present in the data, not today's date.
    latest = (
        db.query(func.max(Transaction.date))
        .filter(Transaction.user_id == user_id)
        .scalar()
    )
    if latest is None:
        return {"error": "No transactions loaded yet.", "total_transactions_loaded": 0}

    ref_month = latest.month
    ref_year = latest.year

    # Transactions in the most recent data month
    month_txns = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
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
    all_txns = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    all_category_totals: dict[str, float] = {}
    for t in all_txns:
        if t.amount < 0:
            all_category_totals[t.category] = all_category_totals.get(t.category, 0) + abs(t.amount)

    # Balance per account (sum of all time)
    account_balances: dict[str, float] = {}
    rows = (
        db.query(Transaction.account, func.sum(Transaction.amount))
        .filter(Transaction.user_id == user_id)
        .group_by(Transaction.account)
        .all()
    )
    for i, (acct, total) in enumerate(rows):
        label = f"Account-{chr(65 + i)}"
        account_balances[label] = round(total, 2)
    total_balance = round(sum(account_balances.values()), 2)

    # Date range + totals
    earliest = (
        db.query(func.min(Transaction.date))
        .filter(Transaction.user_id == user_id)
        .scalar()
    )
    total_txns = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.user_id == user_id)
        .scalar()
    )

    # Individual transactions for AI reference (sorted by date desc, capped at 100)
    recent_txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
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

    # --- Phase 2: Recurring payments ---
    recurring = detect_recurring(db, user_id)
    recurring_monthly_total = round(sum(r["estimated_monthly"] for r in recurring), 2)
    recurring_descs = {r["description"] for r in recurring}

    # --- Phase 2: User profile settings ---
    profile = _get_profile(db, user_id)
    emergency_fund_target = profile.emergency_fund_target
    monthly_buffer = profile.monthly_buffer
    alert_threshold = profile.alert_threshold
    debts = json.loads(profile.outstanding_debts or "[]")

    # --- Phase 2: Safe to spend ---
    spent_recurring_this_month = sum(
        abs(t.amount) for t in month_txns
        if t.amount < 0 and any(rd in t.description.upper() for rd in recurring_descs)
    )
    remaining_recurring = max(0.0, recurring_monthly_total - spent_recurring_this_month)
    safe_to_spend = round(
        total_balance - emergency_fund_target - monthly_buffer - remaining_recurring, 2
    )

    # --- Phase 2: Monthly surplus ---
    monthly_surplus = round(month_income + month_expenses, 2)

    # --- Phase 2: Large adhoc purchase alerts (last 14 days of data) ---
    alert_cutoff = latest - timedelta(days=14)
    alerts = []
    for t in recent_txns:
        if t.date < alert_cutoff:
            break
        if t.amount >= -alert_threshold:
            continue
        if any(rd in t.description.upper() for rd in recurring_descs):
            continue
        alerts.append({
            "date": str(t.date),
            "description": t.description,
            "amount": round(abs(t.amount), 2),
        })

    # --- Smart insights ---
    net = round(month_income + month_expenses, 2)
    period = latest.strftime("%B %Y")
    insights: list[str] = []
    if all_category_totals:
        top_cat = max(all_category_totals, key=all_category_totals.get)
        insights.append(f"Top spending: {top_cat} (${all_category_totals[top_cat]:,.0f} all-time)")
    if net >= 0:
        insights.append(f"Saving ${net:,.0f} in {period}")
    else:
        insights.append(f"Over budget by ${abs(net):,.0f} in {period}")
    if safe_to_spend > 0:
        insights.append(f"Safe to spend: ${safe_to_spend:,.0f} after obligations")
    else:
        insights.append(f"Budget tight — ${abs(safe_to_spend):,.0f} short after obligations")
    if recurring:
        insights.append(f"{len(recurring)} recurring payments (${recurring_monthly_total:,.0f}/mo)")

    return {
        "data_range": {"from": str(earliest), "to": str(latest)},
        "accounts": account_balances,
        "total_balance": total_balance,
        "insights": insights,
        "latest_month": {
            "period": period,
            "income": round(month_income, 2),
            "expenses": round(abs(month_expenses), 2),
            "net": net,
            "by_category": {k: round(v, 2) for k, v in sorted(category_totals.items(), key=lambda x: -x[1])},
        },
        "all_time": {
            "total_expenses": round(sum(all_category_totals.values()), 2),
            "by_category": {k: round(v, 2) for k, v in sorted(all_category_totals.items(), key=lambda x: -x[1])},
        },
        "budget": {
            "safe_to_spend": safe_to_spend,
            "emergency_fund_target": emergency_fund_target,
            "monthly_buffer": monthly_buffer,
            "recurring_monthly_total": recurring_monthly_total,
            "monthly_surplus": monthly_surplus,
            "alert_threshold": alert_threshold,
        },
        "recurring": recurring[:10],
        "debts": debts,
        "alerts": alerts,
        "transactions": transactions_list,
        "total_transactions_loaded": total_txns,
    }
