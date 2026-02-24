# FinWise AI — Phase 1 (Pilot)

AI-powered personal finance dashboard using manually exported bank CSVs as input.

---

## File Structure

```
app/
├── main.py                  # FastAPI entry point, dashboard route
├── database.py              # SQLite connection + SQLAlchemy session
├── models.py                # Transaction table schema
│
├── routers/
│   ├── upload.py            # POST /upload — CSV ingestion + deduplication
│   ├── transactions.py      # GET  /transactions — filterable transaction list
│   └── ai.py               # GET/POST /chat — AI advisor (Claude)
│
├── services/
│   ├── csv_parser.py        # Detects bank format (Chase/BofA/Citi/Generic) and normalizes rows
│   ├── categorizer.py       # Rule-based merchant categorization (no API call)
│   ├── context_builder.py   # Builds anonymized financial snapshot for AI queries
│   └── ai_service.py       # Calls Groq API (Llama 3.3 70B) with snapshot + user question
│
├── templates/
│   ├── base.html            # Bootstrap 5 layout + navbar
│   ├── dashboard.html       # Stats cards, account balances, category donut chart
│   ├── transactions.html    # Filterable transaction table (account, category)
│   └── chat.html           # AI advisor chat UI
│
├── requirements.txt
├── .env.example             # Template for environment variables
├── .gitignore
└── README.md
```

---

## Setup

### 1. Prerequisites

- Python 3.12+
- A [Groq API key](https://console.groq.com) (free, no credit card required)

### 2. Install dependencies

```bash
cd Finwise/app
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```
GROQ_API_KEY=gsk_your-key-here
GROQ_MODEL=llama-3.3-70b-versatile
```

### 4. Run

```bash
uvicorn main:app --reload
```

Open `http://localhost:8000`

---

## Using the App

### Upload a CSV

1. Go to the Dashboard (`/`)
2. Enter an account label — e.g. `Bank1`, `Bank2`, `CreditCard`
3. Select your downloaded CSV file and click **Upload**
4. Repeat for each account

Supported bank formats: **Chase, Bank of America, Citi, Generic** (auto-detected by column headers).

To add a new bank format, add a `_parse_bankname()` function in `services/csv_parser.py`.

### View Transactions

Go to `/transactions` — filter by account or category.

### Ask the AI Advisor

Go to `/chat` and type any question:

- *"Can I spend $2,500 on a vacation this month?"*
- *"How much did I spend on dining last month?"*
- *"What are my biggest expense categories?"*

The AI receives only an **anonymized snapshot** (aggregated numbers, no names, no account numbers) — never raw transaction data.

---

## Cost

| Item | Cost |
|---|---|
| Groq API (free tier) | $0 |
| Everything else | $0 |
| **Total** | **$0** |

---

## Phase 2 (Not in scope yet)

- Live bank connectivity via Plaid (replaces CSV upload)
- PostgreSQL (replaces SQLite)
- Multi-user auth
- Cloud deployment
