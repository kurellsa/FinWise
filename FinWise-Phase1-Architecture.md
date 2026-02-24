# FinWise AI — Phase 1 Architecture (Pilot)

**Goal:** Validate the product idea at near-zero cost using CSV bank exports as input.

---

## Scope

- Upload CSV transaction files (Bank1, Bank2, Credit Card)
- Normalize, categorize, store transactions
- Dashboard: spending by category, net cash flow, account summaries
- AI chat: answer natural language financial questions via Claude API

Out of scope for Phase 1: Plaid, live bank sync, mobile app, cloud infrastructure, vector DB.

---

## Stack

| Layer | Choice | Cost |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Free |
| Database | SQLite (local) | Free |
| Frontend | Next.js 15 + Tailwind CSS | Free |
| Frontend hosting | Vercel free tier | Free |
| Backend hosting | Run locally (or Render free tier) | Free |
| AI | Claude API (claude-sonnet-4-6) | ~$5–15/month |
| Secrets | `.env` file (gitignored) | Free |

---

## Project Structure

```
finwise/
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── routers/
│   │   ├── upload.py         # CSV upload endpoint
│   │   ├── transactions.py   # Transaction CRUD
│   │   └── ai.py             # AI query endpoint
│   ├── services/
│   │   ├── csv_parser.py     # Normalize CSV formats per bank
│   │   ├── categorizer.py    # Rule-based + AI categorization
│   │   ├── context_builder.py # Build financial snapshot for AI
│   │   └── ai_service.py     # Claude API integration
│   ├── models.py             # SQLAlchemy models
│   ├── database.py           # SQLite connection
│   └── .env                  # API keys (gitignored)
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Dashboard
│   │   ├── transactions/     # Transaction feed
│   │   └── chat/             # AI advisor chat
│   └── components/
└── README.md
```

---

## Data Model (SQLite)

```sql
-- One row per transaction, normalized from any CSV format
transactions (
  id          INTEGER PRIMARY KEY,
  account     TEXT,          -- "Bank1", "Bank2", "CreditCard"
  date        DATE,
  description TEXT,
  amount      REAL,          -- negative = debit, positive = credit
  category    TEXT,
  source_file TEXT,
  created_at  DATETIME
)
```

Single table for Phase 1. No encryption overhead locally — add at hosting time.

---

## CSV Ingestion Flow

```
Upload CSV → Detect bank format (by filename or column headers)
           → Parse rows into common schema
           → Deduplicate (same date + amount + description)
           → Auto-categorize (rule-based first, Claude for unknowns)
           → Store in SQLite
```

Each bank gets a parser function in `csv_parser.py`. New banks = new parser function, nothing else changes.

---

## AI Query Flow

```
User question → Context Builder runs SQL aggregations:
                  - Balance per account
                  - MTD spend by category
                  - Avg monthly income
                  - Top merchants this month

              → Anonymized snapshot + question → Claude API
              → Claude reasons over numbers → Answer returned
```

No vector DB. No RAG. SQL gives exact numbers; Claude interprets them.

**Security:** Claude never receives account names or raw PII — only labels like "Account-A" and rounded amounts.

---

## API Endpoints (Phase 1)

```
POST /upload              — Upload one or more CSV files
GET  /transactions        — List transactions (filter by account, date, category)
GET  /summary             — Aggregated financial snapshot
POST /ai/query            — Natural language question → AI answer
```

---

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=sk-...
CLAUDE_MODEL=claude-sonnet-4-6
```

---

## What Phase 2 Adds (not now)

- Plaid live connectivity (replaces CSV upload)
- PostgreSQL (replaces SQLite)
- pgvector for semantic transaction search
- Async job queue (BullMQ) for slow AI calls
- Cloud deployment (Render/Railway paid, or AWS)
- Auth + multi-user support

---

## Cost Summary

| Item | Monthly Cost |
|---|---|
| Claude API (pilot usage) | ~$5–15 |
| Everything else | $0 |
| **Total** | **~$5–15** |
