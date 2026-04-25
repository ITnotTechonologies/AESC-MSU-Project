from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import views, auth, endpoints

app = FastAPI(title="SUNC Delivery")

# Статика
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Шаблоны
templates = Jinja2Templates(directory="app/templates")

# Роутеры
app.include_router(views.router)
app.include_router(auth.router, prefix="/auth")
app.include_router(endpoints.router, prefix="/api")