"""
Tests for auth flow and the two nav routes not covered in test_routes.py:
  /chat  (GET + POST)
  /login (GET + POST)
  /logout

Credentials match what conftest.py sets in os.environ.
"""
import pytest
from unittest.mock import patch

_USER = "testadmin"
_PASS = "testpassword123"


# ---------------------------------------------------------------------------
# /login
# ---------------------------------------------------------------------------

class TestLoginPage:
    def test_login_page_renders(self, anon_client):
        resp = anon_client.get("/login")
        assert resp.status_code == 200

    def test_login_page_has_form(self, anon_client):
        resp = anon_client.get("/login")
        assert "<form" in resp.text.lower()

    def test_valid_credentials_redirect_to_dashboard(self, anon_client):
        resp = anon_client.post("/login", data={"username": _USER, "password": _PASS})
        assert resp.status_code in (302, 303)
        assert resp.headers.get("location") == "/"

    def test_valid_login_sets_session_cookie(self, anon_client):
        resp = anon_client.post("/login", data={"username": _USER, "password": _PASS})
        assert "fw_session" in resp.cookies

    def test_wrong_password_returns_401(self, anon_client):
        resp = anon_client.post("/login", data={"username": _USER, "password": "wrongpass"})
        assert resp.status_code == 401

    def test_wrong_username_returns_401(self, anon_client):
        resp = anon_client.post("/login", data={"username": "nobody", "password": _PASS})
        assert resp.status_code == 401

    def test_invalid_login_shows_error_message(self, anon_client):
        resp = anon_client.post("/login", data={"username": _USER, "password": "bad"})
        assert "Invalid" in resp.text


# ---------------------------------------------------------------------------
# /logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_redirects_to_login(self, anon_client):
        resp = anon_client.get("/logout")
        assert resp.status_code in (302, 303)
        assert "/login" in resp.headers.get("location", "")

    def test_logout_clears_session_cookie(self, anon_client):
        """Cookie should be deleted (empty value or absent) after logout."""
        resp = anon_client.get("/logout")
        # httpx represents a deleted cookie as an empty string
        cookie_val = resp.cookies.get("fw_session", "")
        assert cookie_val == ""


# ---------------------------------------------------------------------------
# /chat
# ---------------------------------------------------------------------------

class TestChatPage:
    def test_get_chat_page_returns_200(self, client):
        resp = client.get("/chat")
        assert resp.status_code == 200

    def test_chat_page_has_message_form(self, client):
        resp = client.get("/chat")
        assert "<form" in resp.text.lower()

    def test_post_chat_returns_200(self, client):
        with patch("routers.ai.query_ai", return_value="Your balance is $1,500.00."):
            resp = client.post("/chat", data={"question": "What is my balance?"})
        assert resp.status_code == 200

    def test_post_chat_renders_ai_response(self, client):
        with patch("routers.ai.query_ai", return_value="Your balance is $1,500.00."):
            resp = client.post("/chat", data={"question": "What is my balance?"})
        assert "Your balance is $1,500.00." in resp.text

    def test_post_chat_renders_user_question(self, client):
        with patch("routers.ai.query_ai", return_value="Some answer."):
            resp = client.post("/chat", data={"question": "Can I afford a vacation?"})
        assert "Can I afford a vacation?" in resp.text

    def test_post_chat_does_not_call_real_groq(self, client):
        """Confirm the mock intercepts the call — no real API traffic in tests."""
        with patch("routers.ai.query_ai", return_value="mocked") as mock_fn:
            client.post("/chat", data={"question": "test"})
        mock_fn.assert_called_once()
