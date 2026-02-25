"""Unit tests for services/context_builder.py — in-memory SQLite via db_session."""
from datetime import date
import pytest
from services.context_builder import build_snapshot
from models import Transaction, UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _txn(db, description: str, amount: float, d: date, category: str = "Test") -> None:
    db.add(Transaction(
        account="TestAcct",
        date=d,
        description=description,
        amount=amount,
        category=category,
        source_file="test.csv",
    ))


def _profile(db, alert_threshold=500.0, emergency_fund=0.0, buffer=0.0) -> None:
    db.add(UserProfile(
        id=1,
        alert_threshold=alert_threshold,
        emergency_fund_target=emergency_fund,
        monthly_buffer=buffer,
        outstanding_debts="[]",
    ))


# ---------------------------------------------------------------------------
# Empty DB
# ---------------------------------------------------------------------------

class TestEmptyDatabase:
    def test_returns_error_key(self, db_session):
        result = build_snapshot(db_session)
        assert "error" in result

    def test_no_transactions_loaded(self, db_session):
        result = build_snapshot(db_session)
        assert result["total_transactions_loaded"] == 0


# ---------------------------------------------------------------------------
# Snapshot structure and math
# ---------------------------------------------------------------------------

class TestSnapshotWithData:
    def _seed(self, db):
        _txn(db, "PAYROLL",    3000.0,  date(2024, 3, 1),  "Income")
        _txn(db, "RENT",      -1200.0,  date(2024, 3, 2),  "Housing")
        _txn(db, "STARBUCKS",    -5.0,  date(2024, 3, 5),  "Dining")
        db.commit()

    def test_all_expected_keys_present(self, db_session):
        self._seed(db_session)
        snap = build_snapshot(db_session)
        for key in ["total_balance", "latest_month", "all_time",
                    "budget", "recurring", "alerts", "transactions",
                    "data_range", "accounts", "insights"]:
            assert key in snap, f"Missing key: {key}"

    def test_income_total(self, db_session):
        self._seed(db_session)
        snap = build_snapshot(db_session)
        assert snap["latest_month"]["income"] == pytest.approx(3000.0)

    def test_expense_total(self, db_session):
        self._seed(db_session)
        snap = build_snapshot(db_session)
        # abs(−1200 + −5) = 1205
        assert snap["latest_month"]["expenses"] == pytest.approx(1205.0)

    def test_monthly_surplus(self, db_session):
        self._seed(db_session)
        snap = build_snapshot(db_session)
        # net = 3000 − 1205 = 1795
        assert snap["budget"]["monthly_surplus"] == pytest.approx(1795.0)

    def test_total_balance(self, db_session):
        self._seed(db_session)
        snap = build_snapshot(db_session)
        assert snap["total_balance"] == pytest.approx(1795.0)

    def test_by_category_populated(self, db_session):
        self._seed(db_session)
        snap = build_snapshot(db_session)
        cats = snap["latest_month"]["by_category"]
        assert "Housing" in cats
        assert cats["Housing"] == pytest.approx(1200.0)

    def test_transactions_list_capped_at_100(self, db_session):
        for i in range(120):
            _txn(db_session, f"TXN-{i}", -1.0, date(2024, 3, 1))
        db_session.commit()
        snap = build_snapshot(db_session)
        assert len(snap["transactions"]) <= 100


# ---------------------------------------------------------------------------
# Safe-to-spend
# ---------------------------------------------------------------------------

class TestSafeToSpend:
    def test_no_obligations(self, db_session):
        """safe_to_spend = balance when emergency_fund and buffer are both 0."""
        _profile(db_session, emergency_fund=0.0, buffer=0.0)  # override defaults
        _txn(db_session, "PAYROLL", 2000.0, date(2024, 3, 1))
        db_session.commit()
        snap = build_snapshot(db_session)
        assert snap["budget"]["safe_to_spend"] == pytest.approx(2000.0)

    def test_emergency_fund_and_buffer_deducted(self, db_session):
        _profile(db_session, emergency_fund=1000.0, buffer=200.0)
        _txn(db_session, "PAYROLL", 3000.0, date(2024, 3, 1))
        _txn(db_session, "RENT",   -1000.0, date(2024, 3, 2))
        db_session.commit()
        # balance = 2000, no recurring → safe = 2000 − 1000 − 200 = 800
        snap = build_snapshot(db_session)
        assert snap["budget"]["safe_to_spend"] == pytest.approx(800.0)

    def test_can_go_negative(self, db_session):
        """When balance < emergency fund the safe_to_spend should be negative."""
        _profile(db_session, emergency_fund=5000.0, buffer=0.0)
        _txn(db_session, "PAYROLL", 1000.0, date(2024, 3, 1))
        db_session.commit()
        snap = build_snapshot(db_session)
        assert snap["budget"]["safe_to_spend"] < 0


# ---------------------------------------------------------------------------
# Large-purchase alerts
# ---------------------------------------------------------------------------

class TestAlerts:
    def test_large_purchase_triggers_alert(self, db_session):
        _profile(db_session, alert_threshold=100.0)
        _txn(db_session, "MACBOOK PRO", -2500.0, date(2024, 3, 10))
        db_session.commit()
        snap = build_snapshot(db_session)
        assert len(snap["alerts"]) == 1
        assert snap["alerts"][0]["description"] == "MACBOOK PRO"

    def test_small_purchase_no_alert(self, db_session):
        _profile(db_session, alert_threshold=100.0)
        _txn(db_session, "COFFEE", -4.50, date(2024, 3, 10))
        db_session.commit()
        snap = build_snapshot(db_session)
        assert snap["alerts"] == []

    def test_income_never_triggers_alert(self, db_session):
        _profile(db_session, alert_threshold=100.0)
        _txn(db_session, "BONUS PAYMENT", 5000.0, date(2024, 3, 10))
        db_session.commit()
        snap = build_snapshot(db_session)
        assert snap["alerts"] == []
