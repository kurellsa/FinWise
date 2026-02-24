from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from services.context_builder import build_snapshot
from services.ai_service import query_ai

router = APIRouter()
templates = Jinja2Templates(directory="templates")

chat_history: list[dict] = []   # In-memory for pilot; resets on server restart


@router.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request):
    return templates.TemplateResponse(
        "chat.html", {"request": request, "history": chat_history}
    )


@router.post("/chat", response_class=HTMLResponse)
def chat_submit(
    request: Request,
    question: str = Form(...),
    db: Session = Depends(get_db),
):
    snapshot = build_snapshot(db)
    answer = query_ai(question, snapshot)

    chat_history.append({"role": "user", "text": question})
    chat_history.append({"role": "assistant", "text": answer})

    return templates.TemplateResponse(
        "chat.html", {"request": request, "history": chat_history}
    )
