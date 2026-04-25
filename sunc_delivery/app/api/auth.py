from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.orm import Session

from app.db.models import User
from app.api.deps import get_db
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/register")
def register(
    response: Response,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()

    token = create_access_token({"sub": user.id})
    response.set_cookie("token", token)

    return {"msg": "registered"}


@router.post("/login")
def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        return {"error": "invalid"}

    token = create_access_token({"sub": user.id})
    response.set_cookie("token", token)

    return {"msg": "ok"}