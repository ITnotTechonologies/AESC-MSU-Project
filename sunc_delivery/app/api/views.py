from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session
from app.db.models import Product as ProductModel
from app.api.deps import get_db

BASE_DIR = Path(__file__).resolve().parent.parent
templates_dir = BASE_DIR / "templates"

env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    autoescape=select_autoescape(["html", "xml"]),
    cache_size=0,
)

router = APIRouter()

@router.get("/", name="home")
def home(request: Request, db: Session = Depends(get_db)):
    html = env.get_template("pages/home.html").render(
        {"request": request, "products": []}
    )
    return HTMLResponse(html)

@router.get("/catalog", name="catalog")
def catalog(request: Request, db: Session = Depends(get_db)):
    products = db.query(ProductModel).all()
    html = env.get_template("pages/catalog.html").render(
        {"request": request, "products": products}
    )
    return HTMLResponse(html)

@router.get("/orders/create", name="order_create")
def order_create(request: Request, db: Session = Depends(get_db)):
    html = env.get_template("pages/order_create.html").render(
        {"request": request}
    )
    return HTMLResponse(html)