from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.db.models import Product

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="home")
def home(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    products = db.query(Product).limit(6).all()
    return templates.TemplateResponse(
        request=request,
        name="pages/home.html",
        context={
            "request": request,
            "user": user,
            "popular_products": products,
            "couriers": [],
        },
    )


@router.get("/catalog", response_class=HTMLResponse, name="catalog")
def catalog(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    products = db.query(Product).all()
    return templates.TemplateResponse(
        request=request,
        name="pages/catalog.html",
        context={
            "request": request,
            "products": products,
            "categories": [],
            "filters": {},
            "user": user,
        },
    )


@router.get("/profile", response_class=HTMLResponse, name="profile")
def profile(
    request: Request,
    user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        request=request,
        name="pages/profile.html",
        context={
            "request": request,
            "user": user,
            "recent_orders": [],
        },
    )


@router.get("/order/create", response_class=HTMLResponse, name="order_create")
def order_create(
    request: Request,
    user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        request=request,
        name="pages/order_create.html",
        context={
            "request": request,
            "user": user,
            "cart_items": [],
            "couriers": [],
            "delivery_points": [
                "Главный корпус",
                "Общежитие",
                "Столовая",
                "Библиотека",
            ],
            "total_items": 0,
            "total_price": 0,
        },
    )


@router.get("/chat", response_class=HTMLResponse, name="chat")
def chat(
    request: Request,
    user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        request=request,
        name="pages/chat.html",
        context={
            "request": request,
            "user": user,
            "order": None,
            "courier": None,
            "messages": [],
        },
    )