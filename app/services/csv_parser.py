"""
Parses CSV files from different banks into a normalized transaction format.
Add a new _parse_*() function to support additional banks.
"""
import pandas as pd
from datetime import date
from typing import Optional


SUPPORTED_FORMATS = {
    "chase": ["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount"],
    "bofa": ["Date", "Description", "Amount", "Running Bal."],
    "citi": ["Status", "Date", "Description", "Debit", "Credit"],
    "capital_one": ["Transaction Date", "Posted Date", "Card No.", "Description", "Debit", "Credit"],
    "visa_corporate": ["CardHolder Name", "Posting Date", "Trans. Date", "Description", "Amount", "Transaction Type"],
    "generic": ["Date", "Description", "Amount"],
}


def detect_format(df: pd.DataFrame) -> str:
    cols = set(df.columns.str.strip())
    if {"Transaction Date", "Post Date", "Description", "Amount"}.issubset(cols):
        return "chase"
    if {"Date", "Description", "Amount", "Running Bal."}.issubset(cols):
        return "bofa"
    if {"Status", "Date", "Description", "Debit", "Credit"}.issubset(cols):
        return "citi"
    if {"Transaction Date", "Posted Date", "Card No.", "Description", "Debit", "Credit"}.issubset(cols):
        return "capital_one"
    if {"CardHolder Name", "Trans. Date", "Description", "Amount", "Transaction Type"}.issubset(cols):
        return "visa_corporate"
    if {"Date", "Description", "Amount"}.issubset(cols):
        return "generic"
    return "unknown"


def _parse_chase(df: pd.DataFrame, account: str, source_file: str) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "account": account,
            "date": pd.to_datetime(row["Transaction Date"]).date(),
            "description": str(row["Description"]).strip(),
            "amount": float(row["Amount"]),
            "category": str(row.get("Category", "Uncategorized")).strip(),
            "source_file": source_file,
        })
    return rows


def _parse_bofa(df: pd.DataFrame, account: str, source_file: str) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        try:
            amount = float(str(row["Amount"]).replace(",", ""))
        except ValueError:
            continue
        rows.append({
            "account": account,
            "date": pd.to_datetime(row["Date"]).date(),
            "description": str(row["Description"]).strip(),
            "amount": amount,
            "category": "Uncategorized",
            "source_file": source_file,
        })
    return rows


def _parse_citi(df: pd.DataFrame, account: str, source_file: str) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        debit = row.get("Debit", "")
        credit = row.get("Credit", "")
        try:
            if pd.notna(debit) and str(debit).strip():
                amount = -abs(float(str(debit).replace(",", "")))
            elif pd.notna(credit) and str(credit).strip():
                amount = abs(float(str(credit).replace(",", "")))
            else:
                continue
        except ValueError:
            continue
        rows.append({
            "account": account,
            "date": pd.to_datetime(row["Date"]).date(),
            "description": str(row["Description"]).strip(),
            "amount": amount,
            "category": "Uncategorized",
            "source_file": source_file,
        })
    return rows


def _parse_capital_one(df: pd.DataFrame, account: str, source_file: str) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        debit = row.get("Debit", "")
        credit = row.get("Credit", "")
        try:
            if pd.notna(debit) and str(debit).strip():
                amount = -abs(float(str(debit).replace(",", "")))
            elif pd.notna(credit) and str(credit).strip():
                amount = abs(float(str(credit).replace(",", "")))
            else:
                continue
        except ValueError:
            continue
        raw_cat = str(row.get("Category", "")).strip()
        category = raw_cat if raw_cat and raw_cat.lower() != "nan" else "Uncategorized"
        rows.append({
            "account": account,
            "date": pd.to_datetime(row["Transaction Date"]).date(),
            "description": str(row["Description"]).strip(),
            "amount": amount,
            "category": category,
            "source_file": source_file,
        })
    return rows


def _parse_visa_corporate(df: pd.DataFrame, account: str, source_file: str) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        try:
            amount = float(str(row["Amount"]).replace(",", ""))
        except ValueError:
            continue
        txn_type = str(row.get("Transaction Type", "D")).strip().upper()
        signed_amount = -abs(amount) if txn_type == "D" else abs(amount)
        raw_cat = str(row.get("Expense Category", "")).strip()
        category = raw_cat if raw_cat and raw_cat.lower() != "nan" else "Uncategorized"
        rows.append({
            "account": account,
            "date": pd.to_datetime(row["Trans. Date"]).date(),
            "description": str(row["Description"]).strip(),
            "amount": signed_amount,
            "category": category,
            "source_file": source_file,
        })
    return rows


def _parse_generic(df: pd.DataFrame, account: str, source_file: str) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        try:
            amount = float(str(row["Amount"]).replace(",", ""))
        except ValueError:
            continue
        rows.append({
            "account": account,
            "date": pd.to_datetime(row["Date"]).date(),
            "description": str(row["Description"]).strip(),
            "amount": amount,
            "category": "Uncategorized",
            "source_file": source_file,
        })
    return rows


def _find_header_row(filepath: str, marker_cols: set[str], max_scan: int = 10) -> int:
    """Scan up to max_scan rows to find the row index containing the real headers."""
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        for i, line in enumerate(f):
            if i >= max_scan:
                break
            if any(col.lower() in line.lower() for col in marker_cols):
                return i
    return 0


def parse_csv(filepath: str, account: str, source_file: str) -> tuple[list[dict], Optional[str]]:
    """
    Returns (rows, error). rows is empty and error is set on failure.
    account: label like "Bank1", "Bank2", "CreditCard"
    """
    parsers = {
        "chase": _parse_chase,
        "bofa": _parse_bofa,
        "citi": _parse_citi,
        "capital_one": _parse_capital_one,
        "visa_corporate": _parse_visa_corporate,
        "generic": _parse_generic,
    }

    # Try reading with no skip first; if unrecognized, scan for a buried header row
    for skip in [0, None]:
        try:
            if skip is None:
                # Scan file to find the header row
                header_row = _find_header_row(
                    filepath,
                    {"Trans. Date", "Posting Date", "CardHolder Name"},
                )
                df = pd.read_csv(filepath, skiprows=header_row)
            else:
                df = pd.read_csv(filepath, skiprows=skip)
            df.columns = df.columns.str.strip()
        except Exception as e:
            return [], f"Could not read CSV: {e}"

        fmt = detect_format(df)
        if fmt in parsers:
            try:
                rows = parsers[fmt](df, account, source_file)
                return rows, None
            except Exception as e:
                return [], f"Parse error ({fmt}): {e}"

    return [], f"Unrecognized CSV format. Columns found: {list(df.columns)}"
