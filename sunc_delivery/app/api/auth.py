from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password
from app.db.models import User

router = APIRouter()


@router.get("/register", response_class=HTMLResponse, name="register")
def register_page(request: Request, user=Depends(get_current_user)):
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/auth/register.html",
        context={"request": request, "user": user, "errors": []},
    )


@router.post("/register")
def register(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    errors = []

    email = email.strip().lower()
    username = username.strip()

    if not email:
        errors.append("Email обязателен.")
    if not username:
        errors.append("Имя пользователя обязательно.")
    if len(password) < 6:
        errors.append("Пароль должен быть не короче 6 символов.")
    if password != password_confirm:
        errors.append("Пароли не совпадают.")

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        errors.append("Пользователь с таким email уже существует.")

    if errors:
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="pages/auth/register.html",
            context={"request": request, "user": None, "errors": errors},
            status_code=400,
        )

    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        role="client",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.get("/login", response_class=HTMLResponse, name="login")
def login_page(request: Request, user=Depends(get_current_user)):
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/auth/login.html",
        context={"request": request, "user": user, "errors": []},
    )


@router.post("/login")
def login(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="pages/auth/login.html",
            context={
                "request": request,
                "user": None,
                "errors": ["Неверный email или пароль."],
            },
            status_code=400,
        )

    if not user.is_active:
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="pages/auth/login.html",
            context={
                "request": request,
                "user": None,
                "errors": ["Аккаунт отключён."],
            },
            status_code=403,
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout", name="logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)