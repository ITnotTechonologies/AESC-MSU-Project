from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import User


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/auth/login"},
        )
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return user