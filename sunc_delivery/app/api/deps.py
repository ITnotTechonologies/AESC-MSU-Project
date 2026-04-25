from fastapi import Depends, HTTPException, Cookie
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.core.security import decode_token
from app.db.models import User


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Cookie(None), db: Session = Depends(get_db)):
    if not token:
        return None

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except:
        return None

    return db.query(User).get(user_id)