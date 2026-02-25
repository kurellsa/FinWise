# FinWise AI — Architecture & Feature Log

> **Rule:** Update this file whenever a new feature, enhancement, or structural change is shipped.
> This is the single source of truth for what is built and running.

---

## Current State: Phase 2 Complete

| Item | Detail |
|---|---|
| Repo | git@github.com:kurellsa/FinWise.git (branch: `main`, tag: `phase1`) |
| Hosting | Render (free tier) — Root Directory: `app`, start: `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| DB (prod) | Neon PostgreSQL (serverless) |
| DB (local / tests) | SQLite (auto-selected when `DATABASE_URL` is absent) |
| Python | 3.13 (pinned via `.python-version`) |

---

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | FastAPI + Uvicorn | Async-capable; single-file routers |
| ORM | SQLAlchemy 2.x | Use `case()` from `sqlalchemy`, NOT `func.case()` |
| DB driver | psycopg[binary] (psycopg3) | No Python 3.13 wheel for psycopg2 |
| Frontend | Jinja2 + Bootstrap 5.3 | dark theme via `data-bs-theme="dark"` |
| Charts | Chart.js 4 (CDN) | Donut (spending) + bar (monthly income/expense) |
| Markdown | marked.js (CDN) | Renders AI chat responses |
| AI | Groq API (`llama-3.3-70b-versatile`) | `query_ai()` in `ai_service.py` |
| Auth | bcrypt + itsdangerous signed cookies | Single-user; 8-hour session |
| Secrets | python-dotenv (`.env`) | Never committed |

---

## Project Structure

```
Finwise/
├── Architecture.md          ← this file
├── pytest.ini               ← testpaths=tests, pythonpath=app
├── requirements-dev.txt     ← pytest, pytest-cov (not installed on Render)
├── .python-version          ← 3.13 (Render pin)
├── app/
│   ├── main.py              ← FastAPI app, dashboard route
│   ├── database.py          ← engine, session, Base; auto-rewrites postgresql:// → postgresql+psycopg://
│   ├── models.py            ← Transaction, UserProfile
│   ├── auth.py              ← bcrypt, itsdangerous, get_current_user(), require_auth()
│   ├── routers/
│   │   ├── upload.py        ← POST /upload (CSV → DB)
│   │   ├── transactions.py  ← GET /transactions (search/filter/export)
│   │   ├── reports.py       ← GET /reports, GET /export/transactions.csv
│   │   ├── ai.py            ← GET+POST /chat (in-memory history)
│   │   ├── settings.py      ← GET+POST /settings (budget profile + debts)
│   │   └── login.py         ← GET+POST /login, GET /logout
│   ├── services/
│   │   ├── csv_parser.py    ← detect_format() + per-bank parsers
│   │   ├── categorizer.py   ← rule-based keyword categorization
│   │   ├── context_builder.py ← build_snapshot() for AI + dashboard
│   │   ├── recurring.py     ← detect_recurring() — 2-of-3-month rule
│   │   └── ai_service.py    ← Groq client, SYSTEM_PROMPT, query_ai()
│   ├── templates/
│   │   ├── base.html        ← navbar, dark theme, Bootstrap CDN
│   │   ├── dashboard.html   ← stat cards, donut chart, smart insights, alerts
│   │   ├── transactions.html
│   │   ├── reports.html
│   │   ├── chat.html        ← markdown rendering via marked.js
│   │   ├── settings.html    ← budget inputs + dynamic debt list
│   │   └── login.html
│   └── static/
│       └── .gitkeep
└── tests/
    ├── conftest.py          ← in-memory SQLite fixtures, TestClient, env vars
    ├── test_startup.py      ← app boot + all nav links return 200
    ├── test_nav.py          ← login, logout, chat (AI mocked)
    ├── test_routes.py       ← upload, transactions, reports, settings, export
    ├── test_context_builder.py
    ├── test_recurring.py
    ├── test_csv_parser.py
    └── test_categorizer.py
```

---

## Data Models

```
transactions
  id            INTEGER PK
  account       TEXT           "Bank1", "CreditCard" — anonymized label
  date          DATE
  description   TEXT
  amount        FLOAT          negative = debit, positive = credit
  category      TEXT
  source_file   TEXT
  created_at    DATETIME       server_default=now()

user_profile                   singleton (always id=1)
  id                    INTEGER PK
  alert_threshold       FLOAT   default 500.0   — flag adhoc purchases above this
  emergency_fund_target FLOAT   default 0.0     — kept untouched in safe-to-spend
  monthly_buffer        FLOAT   default 200.0   — extra cushion above emergency fund
  outstanding_debts     TEXT    default "[]"    — JSON: [{name, balance, rate}]
```

---

## Phase 1 Features (Complete)

| Feature | Key Files |
|---|---|
| CSV upload & deduplication | `routers/upload.py`, `services/csv_parser.py` |
| Multi-bank CSV format support | `services/csv_parser.py` |
| Rule-based auto-categorization | `services/categorizer.py` |
| Dashboard (stat cards, donut chart, insights) | `templates/dashboard.html`, `services/context_builder.py` |
| Transactions page (search, filter, export) | `routers/transactions.py`, `routers/reports.py` |
| Monthly income/expense bar chart | `templates/reports.html` |
| AI chat (Groq `llama-3.3-70b-versatile`) | `routers/ai.py`, `services/ai_service.py` |
| Markdown rendering of AI responses | `templates/chat.html` (marked.js) |
| Single-user auth (bcrypt + signed cookie) | `auth.py`, `routers/login.py` |
| SQLite → Neon PostgreSQL (prod) | `database.py` |
| Render deployment | `.python-version`, `app/static/.gitkeep` |

### Supported CSV Formats
| Bank | Column signature |
|---|---|
| Chase | `Transaction Date`, `Post Date`, `Description`, `Category`, `Type`, `Amount` |
| Bank of America | `Date`, `Description`, `Amount`, `Running Bal.` |
| Citi | `Status`, `Date`, `Description`, `Debit`, `Credit` |
| Capital One | `Transaction Date`, `Posted Date`, `Card No.`, `Description`, `Debit`, `Credit` |
| Visa Corporate | `CardHolder Name`, `Trans. Date`, `Description`, `Amount`, `Transaction Type` |
| Generic | `Date`, `Description`, `Amount` |

---

## Phase 2 Features (Complete)

| Feature | Key Files | Notes |
|---|---|---|
| Recurring payment detection | `services/recurring.py` | Appears in 2+ of last 3 months; income excluded |
| Safe-to-spend calculation | `services/context_builder.py` | balance − emergency_fund − buffer − remaining_recurring |
| Large-purchase alerts on dashboard | `templates/dashboard.html`, `context_builder.py` | Within 14 days, above threshold, not recurring |
| Monthly surplus calculation | `context_builder.py` | net of latest month (income + expenses) |
| Budget settings page | `routers/settings.py`, `templates/settings.html` | Alert threshold, emergency fund, buffer |
| Outstanding debts manager | `templates/settings.html` | Name, balance ($), interest rate (%) per debt |
| AI affordability framework | `services/ai_service.py` | Yes/No + nuance using safe_to_spend |
| AI surplus/investment guidance | `services/ai_service.py` | Emergency fund → debt avalanche → index funds |
| AI debt payoff suggestions | `services/ai_service.py` | Avalanche method; never recommends crypto/stocks |

### Safe-to-Spend Formula
```
safe_to_spend = total_balance
              - emergency_fund_target
              - monthly_buffer
              - max(0, recurring_monthly_total - spent_recurring_this_month)
```

---

## Test Suite (108 tests, 0 failures)

Run from `Finwise/`:
```bash
app/.venv/bin/python3.13 -m pytest tests/ -v
```

| File | Tests | What it covers |
|---|---|---|
| `test_startup.py` | 5 | App boots, all routes registered, env vars present, DB tables exist, all nav links → 200 |
| `test_nav.py` | 15 | Login (valid/invalid), logout, /chat GET+POST (AI mocked) |
| `test_routes.py` | 33 | Upload count/dedup/unknown format, transactions filter, settings persist, export CSV |
| `test_context_builder.py` | 14 | Income/expense math, surplus, safe-to-spend, alerts |
| `test_recurring.py` | 12 | normalize(), 1/2/3-month detection, income excluded, regression: date-vs-varchar |
| `test_csv_parser.py` | 19 | detect_format() for all banks; amount signs, categories, comma handling |
| `test_categorizer.py` | 19 | Keyword matching, case insensitivity, rule priority |

**Test isolation:** every test uses an in-memory SQLite DB via `StaticPool`; `get_db` is overridden via FastAPI's dependency injection. Real Neon DB is never touched.

---

## Known Issues / Technical Debt

| Item | Severity | Notes |
|---|---|---|
| `TemplateResponse(name, ctx)` deprecation | Low | Starlette 0.37+ prefers `TemplateResponse(request, name)`. Not breaking yet. |
| `/chat` history is in-memory | Low | `chat_history` list in `routers/ai.py` resets on server restart; not per-user |
| No auth guard on `/chat` | Medium | Any user who knows the URL can access chat; acceptable for single-user pilot |

---

## Planned (Phase 3)

- Plaid API live bank sync (sandbox request submitted)
- Per-user multi-tenant support
- Chat history persisted to DB per user
- pgvector semantic transaction search
