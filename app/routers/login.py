import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import verify_password, create_session_cookie, COOKIE_NAME
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory="templates")

_USERNAME = os.environ["APP_USERNAME"]
_PASSWORD_HASH = os.environ["APP_PASSWORD_HASH"]


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == _USERNAME and verify_password(password, _PASSWORD_HASH):
        response = RedirectResponse(url="/", status_code=303)
        create_session_cookie(response, username)
        return response
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password."},
        status_code=401,
    )


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
