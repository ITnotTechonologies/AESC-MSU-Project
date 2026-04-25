from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.api import auth, views

app = FastAPI(title="SUNC Delivery")

templates = Jinja2Templates(directory="app/templates")
app.state.templates = templates

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="sunc_session",
    same_site="lax",
    https_only=False,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(views.router, tags=["pages"])