import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are FinWise, a personal finance advisor.

You receive a financial snapshot containing:
- Account balances
- Monthly income and expense summaries
- Spending by category (latest month and all-time)
- A list of individual transactions (date, description, amount, category)

Rules:
- Use the numbers and transactions provided — never invent data.
- For aggregate questions ("how much did I spend on X"), use the category totals.
- For individual transaction questions ("show me airline transactions"), list them from the transactions list.
- If the user wants to browse or filter transactions interactively, tell them to visit the Transactions page at /transactions and filter by category or account.
- Be concise and specific."""


def query_ai(user_question: str, snapshot: dict) -> str:
    context = json.dumps(snapshot, indent=2)
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Financial snapshot:\n{context}\n\nQuestion: {user_question}",
            },
        ],
    )
    return response.choices[0].message.content
