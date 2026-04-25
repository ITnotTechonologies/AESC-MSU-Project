from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import PlainTextResponse, HTMLResponse

from app.api.endpoints import router as api_router
from app.api.views import router as views_router

BASE_DIR = Path(__file__).resolve().parent
templates_dir = BASE_DIR / "templates"

env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    autoescape=select_autoescape(["html", "xml"]),
    cache_size=0,
)

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        content = env.get_template("pages/404.html").render(
            {"request": request, "path": request.url.path}
        )
        return HTMLResponse(content, status_code=404)
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)

app.include_router(api_router, prefix="/api")
app.include_router(views_router)