from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth import verify_password, create_session_cookie, COOKIE_NAME

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, registered: str = ""):
    msg = "Account created. Please sign in." if registered else ""
    return templates.TemplateResponse(request, "login.html", {"msg": msg, "error": ""})


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
        response = RedirectResponse(url="/", status_code=303)
        create_session_cookie(response, user.id, user.username)
        return response
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid username or password.", "msg": ""},
        status_code=401,
    )


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
