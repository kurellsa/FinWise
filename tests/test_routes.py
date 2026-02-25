"""
Integration tests for HTTP routes — FastAPI TestClient + in-memory SQLite.

The `client` fixture (conftest.py) is pre-authenticated via a signed session cookie.
The `anon_client` fixture sends requests without a cookie.
Both use in-memory SQLite so the real Neon DB is never touched.
"""
import io
import json
import pytest

# ---------------------------------------------------------------------------
# Minimal valid CSVs
# ---------------------------------------------------------------------------

CHASE_CSV = (
    "Transaction Date,Post Date,Description,Category,Type,Amount\n"
    "01/15/2024,01/16/2024,STARBUCKS,Food & Drink,Sale,-5.25\n"
    "01/16/2024,01/17/2024,PAYROLL,Income,ACH_CREDIT,3500.00\n"
)

UNKNOWN_CSV = "Foo,Bar,Baz\n1,2,3\n"


def _upload(client, content: str = CHASE_CSV, account: str = "TestAcct", follow=False):
    """Helper: POST /upload with multipart form."""
    return client.post(
        "/upload",
        data={"account": account},
        files={"file": ("test.csv", io.BytesIO(content.encode()), "text/csv")},
        follow_redirects=follow,
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_authenticated_empty_db_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_unauthenticated_redirects_to_login(self, anon_client):
        resp = anon_client.get("/")
        assert resp.status_code in (302, 303)
        assert "/login" in resp.headers.get("location", "")

    def test_dashboard_after_upload_returns_200(self, client):
        _upload(client, follow=True)
        resp = client.get("/")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class TestUpload:
    def test_valid_csv_redirects(self, client):
        resp = _upload(client)
        assert resp.status_code in (302, 303)

    def test_valid_csv_reports_inserted_count(self, client):
        resp = _upload(client)
        loc = resp.headers.get("location", "")
        assert "uploaded=2" in loc          # CHASE_CSV has 2 data rows

    def test_duplicate_upload_reports_skipped(self, client):
        _upload(client)                     # first: both inserted
        resp = _upload(client)              # second: both are duplicates
        loc = resp.headers.get("location", "")
        assert "skipped=2" in loc

    def test_unknown_format_returns_error_json(self, client):
        resp = client.post(
            "/upload",
            data={"account": "Test"},
            files={"file": ("bad.csv", io.BytesIO(UNKNOWN_CSV.encode()), "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "error" in body
        assert "Unrecognized" in body["error"]

    def test_account_label_stored(self, client, db_session):
        _upload(client, account="MyBank")
        from models import Transaction
        txns = db_session.query(Transaction).all()
        assert all(t.account == "MyBank" for t in txns)

    def test_categorizer_applied_when_category_uncategorized(self, client, db_session):
        """BofA CSV has no category column — categorizer should fill it in."""
        bofa = (
            "Date,Description,Amount,Running Bal.\n"
            "01/15/2024,STARBUCKS COFFEE,-4.50,100.00\n"
        )
        _upload(client, content=bofa)
        from models import Transaction
        txn = db_session.query(Transaction).first()
        assert txn.category == "Dining"


# ---------------------------------------------------------------------------
# Transactions page
# ---------------------------------------------------------------------------

class TestTransactions:
    def test_empty_db_returns_200(self, client):
        assert client.get("/transactions").status_code == 200

    def test_with_data_returns_200(self, client):
        _upload(client, follow=True)
        assert client.get("/transactions").status_code == 200

    def test_search_filter_applied(self, client):
        _upload(client, follow=True)
        resp = client.get("/transactions?search=STARBUCKS")
        assert resp.status_code == 200
        assert "STARBUCKS" in resp.text


# ---------------------------------------------------------------------------
# Reports page
# ---------------------------------------------------------------------------

class TestReports:
    def test_empty_db_returns_200(self, client):
        assert client.get("/reports").status_code == 200

    def test_with_data_returns_200(self, client):
        _upload(client, follow=True)
        assert client.get("/reports").status_code == 200


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------

class TestSettings:
    def test_get_returns_200(self, client):
        assert client.get("/settings").status_code == 200

    def test_save_redirects_with_saved_flag(self, client):
        resp = client.post(
            "/settings",
            data={
                "alert_threshold": "750",
                "emergency_fund_target": "5000",
                "monthly_buffer": "300",
            },
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert "saved=1" in resp.headers.get("location", "")

    def test_saved_values_persisted_in_db(self, client, db_session):
        client.post(
            "/settings",
            data={
                "alert_threshold": "750",
                "emergency_fund_target": "5000",
                "monthly_buffer": "300",
            },
            follow_redirects=False,
        )
        from models import UserProfile
        profile = db_session.get(UserProfile, 1)
        assert profile.alert_threshold == 750.0
        assert profile.emergency_fund_target == 5000.0
        assert profile.monthly_buffer == 300.0

    def test_debt_saved_and_parsed_correctly(self, client, db_session):
        client.post(
            "/settings",
            data={
                "alert_threshold": "500",
                "emergency_fund_target": "0",
                "monthly_buffer": "200",
                "debt_names": "Car Loan",
                "debt_balances": "12000",
                "debt_rates": "4.5",
            },
            follow_redirects=False,
        )
        from models import UserProfile
        profile = db_session.get(UserProfile, 1)
        debts = json.loads(profile.outstanding_debts)
        assert len(debts) == 1
        assert debts[0]["name"] == "Car Loan"
        assert debts[0]["balance"] == pytest.approx(12000.0)
        assert debts[0]["rate"] == pytest.approx(4.5)

    def test_empty_debt_name_skipped(self, client, db_session):
        """Rows with an empty name field must be ignored, not saved."""
        client.post(
            "/settings",
            data={
                "alert_threshold": "500",
                "emergency_fund_target": "0",
                "monthly_buffer": "200",
                "debt_names": "",           # blank name → skip
                "debt_balances": "1000",
                "debt_rates": "5",
            },
            follow_redirects=False,
        )
        from models import UserProfile
        profile = db_session.get(UserProfile, 1)
        debts = json.loads(profile.outstanding_debts)
        assert debts == []


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

class TestExport:
    def test_export_all_csv_returns_csv_content_type(self, client):
        resp = client.get("/export/transactions.csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_export_all_csv_has_header_row(self, client):
        resp = client.get("/export/transactions.csv")
        assert "Date" in resp.text
        assert "Amount" in resp.text

    def test_export_after_upload_has_data(self, client):
        _upload(client, follow=True)
        resp = client.get("/export/transactions.csv")
        assert "STARBUCKS" in resp.text
