from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import ChatMessage
from services.context_builder import build_snapshot
from services.ai_service import query_ai
from auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request, db: Session = Depends(get_db)):
    user_id, username = require_auth(request)
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "chat.html",
        {"history": history, "username": username},
    )


@router.post("/chat", response_class=HTMLResponse)
def chat_submit(
    request: Request,
    question: str = Form(...),
    db: Session = Depends(get_db),
):
    user_id, username = require_auth(request)
    snapshot = build_snapshot(db, user_id)
    answer = query_ai(question, snapshot)

    db.add(ChatMessage(user_id=user_id, role="user", text=question))
    db.add(ChatMessage(user_id=user_id, role="assistant", text=answer))
    db.commit()

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "chat.html",
        {"history": history, "username": username},
    )
