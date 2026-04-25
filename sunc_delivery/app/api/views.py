from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_user
from app.db.models import Product

router = APIRouter()


def _get_cart(request: Request) -> dict[str, int]:
    return request.session.setdefault("cart", {})


def _cart_count(cart: dict[str, int]) -> int:
    return sum(cart.values())


def _load_cart_items(db: Session, cart: dict[str, int]) -> list[dict]:
    if not cart:
        return []

    product_ids = [int(pid) for pid in cart.keys()]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    items: list[dict] = []
    for pid_str, quantity in cart.items():
        pid = int(pid_str)
        product = product_map.get(pid)
        if not product:
            continue
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": Decimal(str(product.price)) * quantity,
            }
        )
    return items


@router.get("/", response_class=HTMLResponse, name="home")
def home(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    products = db.query(Product).limit(6).all()
    return request.app.state.templates.TemplateResponse(
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
    return request.app.state.templates.TemplateResponse(
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
    user=Depends(require_user),
):
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/profile.html",
        context={
            "request": request,
            "user": user,
            "recent_orders": [],
        },
    )


@router.get("/chat", response_class=HTMLResponse, name="chat")
def chat(
    request: Request,
    user=Depends(require_user),
):
    return request.app.state.templates.TemplateResponse(
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


@router.get("/cart", response_class=HTMLResponse, name="cart")
def cart_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    cart = _get_cart(request)
    cart_items = _load_cart_items(db, cart)
    total_price = sum((item["line_total"] for item in cart_items), Decimal("0.00"))

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/cart.html",
        context={
            "request": request,
            "user": user,
            "cart_items": cart_items,
            "total_price": total_price,
            "total_items": _cart_count(cart),
        },
    )


@router.post("/cart/add/{product_id}", name="cart_add")
def cart_add(
    request: Request,
    product_id: int,
    quantity: int = Form(1),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if quantity < 1:
        quantity = 1

    cart = _get_cart(request)
    key = str(product_id)
    cart[key] = cart.get(key, 0) + quantity
    request.session["cart"] = cart

    return RedirectResponse(url="/cart", status_code=303)


@router.post("/cart/update/{product_id}", name="cart_update")
def cart_update(
    request: Request,
    product_id: int,
    delta: int = Form(...),
    user=Depends(require_user),
):
    cart = _get_cart(request)
    key = str(product_id)

    if key not in cart:
        return RedirectResponse(url="/cart", status_code=303)

    new_quantity = cart[key] + delta
    if new_quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = new_quantity

    request.session["cart"] = cart
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/cart/remove/{product_id}", name="cart_remove")
def cart_remove(
    request: Request,
    product_id: int,
    user=Depends(require_user),
):
    cart = _get_cart(request)
    cart.pop(str(product_id), None)
    request.session["cart"] = cart
    return RedirectResponse(url="/cart", status_code=303)


@router.get("/order/create", response_class=HTMLResponse, name="order_create")
def order_create(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    cart = _get_cart(request)
    cart_items = _load_cart_items(db, cart)
    total_price = sum((item["line_total"] for item in cart_items), Decimal("0.00"))

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/order_create.html",
        context={
            "request": request,
            "user": user,
            "cart_items": cart_items,
            "total_items": _cart_count(cart),
            "total_price": total_price,
            "couriers": [],
            "delivery_points": [
                "Главный корпус",
                "Общежитие",
                "Столовая",
                "Библиотека",
            ],
        },
    )