import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Transaction
from services.csv_parser import parse_csv
from services.categorizer import categorize
from auth import require_auth

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    account: str = Form(...),
    db: Session = Depends(get_db),
):
    user_id, username = require_auth(request)

    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    rows, error = parse_csv(filepath, account, file.filename)
    if error:
        return {"error": error}

    inserted = 0
    skipped = 0
    for row in rows:
        # Deduplicate: same user + account + date + description + amount
        exists = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.account == row["account"],
                Transaction.date == row["date"],
                Transaction.description == row["description"],
                Transaction.amount == row["amount"],
            )
            .first()
        )
        if exists:
            skipped += 1
            continue

        # Apply rule-based category if not already set by parser
        if row.get("category") in (None, "", "Uncategorized"):
            row["category"] = categorize(row["description"])

        row["user_id"] = user_id
        db.add(Transaction(**row))
        inserted += 1

    db.commit()

    return RedirectResponse(
        url=f"/?uploaded={inserted}&skipped={skipped}&account={account}",
        status_code=303,
    )
