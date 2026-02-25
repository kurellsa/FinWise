"""Unit tests for services/csv_parser.py — no DB needed."""
import io
import pytest
import pandas as pd

from services.csv_parser import detect_format, parse_csv

# ---------------------------------------------------------------------------
# Minimal valid CSV strings for each supported bank format
# ---------------------------------------------------------------------------

CHASE_CSV = (
    "Transaction Date,Post Date,Description,Category,Type,Amount\n"
    "01/15/2024,01/16/2024,STARBUCKS #1234,Food & Drink,Sale,-5.25\n"
    "01/16/2024,01/17/2024,DIRECT DEPOSIT PAYROLL,Income,ACH_CREDIT,3500.00\n"
)

BOFA_CSV = (
    "Date,Description,Amount,Running Bal.\n"
    "01/15/2024,WALMART SUPERCENTER,-45.23,1234.56\n"
    "01/16/2024,DIRECT DEPOSIT,3500.00,4734.56\n"
)

CITI_CSV = (
    "Status,Date,Description,Debit,Credit\n"
    "Cleared,01/15/2024,NETFLIX,15.99,\n"
    "Cleared,01/16/2024,PAYMENT RECEIVED,,500.00\n"
)

CAPITAL_ONE_CSV = (
    "Transaction Date,Posted Date,Card No.,Description,Category,Debit,Credit\n"
    "2024-01-15,2024-01-16,1234,AMAZON.COM,Shopping,89.99,\n"
    "2024-01-16,2024-01-17,1234,PAYMENT RECEIVED,Payment,,500.00\n"
)

UNKNOWN_CSV = "Foo,Bar,Baz\n1,2,3\n"


def _df(csv_text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(csv_text))


def _write(tmp_path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content)
    return str(p)


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------

class TestDetectFormat:
    def test_chase(self):
        assert detect_format(_df(CHASE_CSV)) == "chase"

    def test_bofa(self):
        assert detect_format(_df(BOFA_CSV)) == "bofa"

    def test_citi(self):
        assert detect_format(_df(CITI_CSV)) == "citi"

    def test_capital_one(self):
        assert detect_format(_df(CAPITAL_ONE_CSV)) == "capital_one"

    def test_unknown_returns_unknown(self):
        assert detect_format(_df(UNKNOWN_CSV)) == "unknown"


# ---------------------------------------------------------------------------
# parse_csv — amounts and counts
# ---------------------------------------------------------------------------

class TestParseChase:
    def test_row_count(self, tmp_path):
        rows, err = parse_csv(_write(tmp_path, "chase.csv", CHASE_CSV), "Chase", "chase.csv")
        assert err is None
        assert len(rows) == 2

    def test_negative_amount(self, tmp_path):
        rows, err = parse_csv(_write(tmp_path, "chase.csv", CHASE_CSV), "Chase", "chase.csv")
        starbucks = next(r for r in rows if "STARBUCKS" in r["description"])
        assert starbucks["amount"] == -5.25

    def test_positive_amount(self, tmp_path):
        rows, err = parse_csv(_write(tmp_path, "chase.csv", CHASE_CSV), "Chase", "chase.csv")
        payroll = next(r for r in rows if "PAYROLL" in r["description"])
        assert payroll["amount"] == 3500.00

    def test_category_preserved(self, tmp_path):
        rows, err = parse_csv(_write(tmp_path, "chase.csv", CHASE_CSV), "Chase", "chase.csv")
        starbucks = next(r for r in rows if "STARBUCKS" in r["description"])
        assert starbucks["category"] == "Food & Drink"

    def test_account_label_set(self, tmp_path):
        rows, err = parse_csv(_write(tmp_path, "chase.csv", CHASE_CSV), "MyChase", "chase.csv")
        assert all(r["account"] == "MyChase" for r in rows)


class TestParseBofa:
    def test_row_count(self, tmp_path):
        rows, err = parse_csv(_write(tmp_path, "bofa.csv", BOFA_CSV), "BofA", "bofa.csv")
        assert err is None
        assert len(rows) == 2

    def test_comma_in_amount(self, tmp_path):
        content = (
            'Date,Description,Amount,Running Bal.\n'
            '01/15/2024,RENT PAYMENT,"-1,200.00",1234.56\n'
        )
        rows, err = parse_csv(_write(tmp_path, "bofa.csv", content), "BofA", "bofa.csv")
        assert err is None
        assert rows[0]["amount"] == -1200.0

    def test_category_uncategorized(self, tmp_path):
        rows, _ = parse_csv(_write(tmp_path, "bofa.csv", BOFA_CSV), "BofA", "bofa.csv")
        assert all(r["category"] == "Uncategorized" for r in rows)


class TestParseCiti:
    def test_debit_is_negative(self, tmp_path):
        rows, err = parse_csv(_write(tmp_path, "citi.csv", CITI_CSV), "Citi", "citi.csv")
        assert err is None
        netflix = next(r for r in rows if "NETFLIX" in r["description"])
        assert netflix["amount"] == pytest.approx(-15.99)

    def test_credit_is_positive(self, tmp_path):
        rows, _ = parse_csv(_write(tmp_path, "citi.csv", CITI_CSV), "Citi", "citi.csv")
        payment = next(r for r in rows if "PAYMENT" in r["description"])
        assert payment["amount"] == pytest.approx(500.00)


class TestParseCapitalOne:
    def test_debit_is_negative(self, tmp_path):
        rows, err = parse_csv(_write(tmp_path, "c1.csv", CAPITAL_ONE_CSV), "CapOne", "c1.csv")
        assert err is None
        amazon = next(r for r in rows if "AMAZON" in r["description"])
        assert amazon["amount"] == pytest.approx(-89.99)

    def test_credit_is_positive(self, tmp_path):
        rows, _ = parse_csv(_write(tmp_path, "c1.csv", CAPITAL_ONE_CSV), "CapOne", "c1.csv")
        payment = next(r for r in rows if "PAYMENT" in r["description"])
        assert payment["amount"] == pytest.approx(500.00)

    def test_category_from_csv(self, tmp_path):
        rows, _ = parse_csv(_write(tmp_path, "c1.csv", CAPITAL_ONE_CSV), "CapOne", "c1.csv")
        amazon = next(r for r in rows if "AMAZON" in r["description"])
        assert amazon["category"] == "Shopping"


class TestUnknownFormat:
    def test_returns_empty_rows(self, tmp_path):
        rows, err = parse_csv(_write(tmp_path, "bad.csv", UNKNOWN_CSV), "X", "bad.csv")
        assert rows == []

    def test_returns_error_message(self, tmp_path):
        rows, err = parse_csv(_write(tmp_path, "bad.csv", UNKNOWN_CSV), "X", "bad.csv")
        assert err is not None
        assert "Unrecognized" in err
