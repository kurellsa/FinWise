"""Unit tests for services/recurring.py — in-memory SQLite via db_session fixture."""
from datetime import date
import pytest
from services.recurring import _normalize, detect_recurring
from models import Transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add(db, description: str, amount: float, d: date) -> None:
    db.add(Transaction(
        account="TestAcct",
        date=d,
        description=description,
        amount=amount,
        category="Test",
        source_file="test.csv",
    ))


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_uppercases(self):
        assert _normalize("netflix") == "NETFLIX"

    def test_strips_trailing_digits(self):
        result = _normalize("NETFLIX 98765")
        assert result == "NETFLIX"

    def test_preserves_multi_word_name(self):
        assert _normalize("AMAZON PRIME") == "AMAZON PRIME"

    def test_collapses_extra_spaces(self):
        result = _normalize("GYM   MEMBERSHIP")
        assert "  " not in result


# ---------------------------------------------------------------------------
# detect_recurring
# ---------------------------------------------------------------------------

class TestDetectRecurring:
    def test_empty_db_returns_empty_list(self, db_session):
        assert detect_recurring(db_session) == []

    def test_single_month_not_recurring(self, db_session):
        _add(db_session, "NETFLIX", -15.99, date(2024, 1, 15))
        db_session.commit()
        assert detect_recurring(db_session) == []

    def test_two_months_flagged_as_recurring(self, db_session):
        _add(db_session, "NETFLIX", -15.99, date(2024, 1, 15))
        _add(db_session, "NETFLIX", -15.99, date(2024, 2, 15))
        db_session.commit()
        result = detect_recurring(db_session)
        assert len(result) >= 1
        assert any("NETFLIX" in r["description"] for r in result)

    def test_three_months_months_seen_is_3(self, db_session):
        _add(db_session, "SPOTIFY", -9.99, date(2024, 1, 5))
        _add(db_session, "SPOTIFY", -9.99, date(2024, 2, 5))
        _add(db_session, "SPOTIFY", -9.99, date(2024, 3, 5))
        db_session.commit()
        result = detect_recurring(db_session)
        spotify = next(r for r in result if "SPOTIFY" in r["description"])
        assert spotify["months_seen"] == 3

    def test_income_transactions_excluded(self, db_session):
        """Positive amounts (credits) must never appear in the recurring list."""
        _add(db_session, "PAYROLL DIRECT DEPOSIT", 3500.0, date(2024, 1, 1))
        _add(db_session, "PAYROLL DIRECT DEPOSIT", 3500.0, date(2024, 2, 1))
        db_session.commit()
        assert detect_recurring(db_session) == []

    def test_avg_amount_computed_correctly(self, db_session):
        _add(db_session, "GYM MEMBERSHIP", -30.0, date(2024, 1, 10))
        _add(db_session, "GYM MEMBERSHIP", -32.0, date(2024, 2, 10))
        db_session.commit()
        result = detect_recurring(db_session)
        assert len(result) == 1
        assert result[0]["avg_amount"] == pytest.approx(31.0)

    def test_sorted_by_amount_descending(self, db_session):
        """Highest-cost recurring item should appear first."""
        _add(db_session, "RENT PAYMENT", -1500.0, date(2024, 1, 1))
        _add(db_session, "RENT PAYMENT", -1500.0, date(2024, 2, 1))
        _add(db_session, "NETFLIX", -15.99, date(2024, 1, 5))
        _add(db_session, "NETFLIX", -15.99, date(2024, 2, 5))
        db_session.commit()
        result = detect_recurring(db_session)
        assert result[0]["avg_amount"] > result[-1]["avg_amount"]

    def test_date_object_not_string_in_query(self, db_session):
        """Regression: recurring.py must pass a date object, not a string,
        or PostgreSQL raises 'operator does not exist: date >= varchar'."""
        # If this test passes the query ran without a type error on SQLite too.
        _add(db_session, "HULU", -7.99, date(2024, 2, 1))
        _add(db_session, "HULU", -7.99, date(2024, 3, 1))
        db_session.commit()
        result = detect_recurring(db_session)   # would raise if f-string used
        assert any("HULU" in r["description"] for r in result)
