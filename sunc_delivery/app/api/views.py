from __future__ import annotations

from decimal import Decimal



from app.db.models import Product, Courier, User

from datetime import datetime, timezone
import time

from fastapi import BackgroundTasks, Depends, Form, HTTPException, Request, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user, get_current_user
from app.db.database import SessionLocal
from app.db.models import Product, Order, OrderItem, Courier, User, OrderStatusHistory

from app.db.models import Order, Courier, User
from sqlalchemy.orm import Session
from fastapi import Depends, Request
from app.api.deps import get_db, require_user

from decimal import Decimal
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_user
from app.db.models import Product

router = APIRouter()


router = APIRouter()



def complete_order_later(order_id: int):
    time.sleep(60)

    db = SessionLocal()
    try:
        order = db.get(Order, order_id)
        if not order:
            return

        # Если заказ уже не в created, ничего не делаем
        if order.status != "created":
            return

        old_status = order.status
        order.status = "delivered"
        order.updated_at = datetime.now(timezone.utc)

        db.add(
            OrderStatusHistory(
                order_id=order.id,
                old_status=old_status,
                new_status="delivered",
                changed_by=None,
            )
        )
        db.commit()
    finally:
        db.close()



def _get_cart(request: Request) -> dict[str, int]:
    cart = request.session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}
    return cart


def _save_cart(request: Request, cart: dict[str, int]) -> None:
    request.session["cart"] = dict(cart)


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

        price = Decimal(str(product.price))
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": price * quantity,
            }
        )

    return items


def _cart_total(cart_items: list[dict]) -> Decimal:
    return sum((item["line_total"] for item in cart_items), Decimal("0.00"))


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
    _save_cart(request, cart)

    return RedirectResponse(url=request.url_for("order_create"), status_code=303)


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
        return RedirectResponse(url=request.url_for("order_create"), status_code=303)

    new_quantity = cart[key] + delta
    if new_quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = new_quantity

    _save_cart(request, cart)
    return RedirectResponse(url=request.url_for("order_create"), status_code=303)


@router.post("/cart/set/{product_id}", name="cart_set")
def cart_set(
    request: Request,
    product_id: int,
    quantity: int = Form(...),
    user=Depends(require_user),
):
    cart = _get_cart(request)
    key = str(product_id)

    if quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = quantity

    _save_cart(request, cart)
    return RedirectResponse(url=request.url_for("order_create"), status_code=303)


@router.post("/cart/remove/{product_id}", name="cart_remove")
def cart_remove(
    request: Request,
    product_id: int,
    user=Depends(require_user),
):
    cart = _get_cart(request)
    cart.pop(str(product_id), None)
    _save_cart(request, cart)
    return RedirectResponse(url=request.url_for("order_create"), status_code=303)


@router.post("/cart/clear", name="cart_clear")
def cart_clear(
    request: Request,
    user=Depends(require_user),
):
    _save_cart(request, {})
    return RedirectResponse(url=request.url_for("order_create"), status_code=303)

@router.get("/cart", response_class=HTMLResponse, name="cart")
def cart_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    cart = _get_cart(request)
    cart_items = _load_cart_items(db, cart)
    total_price = _cart_total(cart_items)

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/cart.html",
        context={
            "request": request,
            "user": user,
            "cart_items": cart_items,
            "total_items": _cart_count(cart),
            "total_price": total_price,
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

    return RedirectResponse(url="/order/create", status_code=303)


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
        return RedirectResponse(url="/order/create", status_code=303)

    new_quantity = cart[key] + delta
    if new_quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = new_quantity

    request.session["cart"] = cart
    return RedirectResponse(url="/order/create", status_code=303)


@router.post("/cart/set/{product_id}", name="cart_set")
def cart_set(
    request: Request,
    product_id: int,
    quantity: int = Form(...),
    user=Depends(require_user),
):
    cart = _get_cart(request)
    key = str(product_id)

    if quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = quantity

    request.session["cart"] = cart
    return RedirectResponse(url="/order/create", status_code=303)


@router.post("/cart/remove/{product_id}", name="cart_remove")
def cart_remove(
    request: Request,
    product_id: int,
    user=Depends(require_user),
):
    cart = _get_cart(request)
    cart.pop(str(product_id), None)
    request.session["cart"] = cart
    return RedirectResponse(url="/order/create", status_code=303)


@router.post("/cart/clear", name="cart_clear")
def cart_clear(
    request: Request,
    user=Depends(require_user),
):
    request.session["cart"] = {}
    return RedirectResponse(url="/order/create", status_code=303)


@router.post("/orders/create", name="orders_create")
def orders_create(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(require_user),
    courier_id: int = Form(...),
    delivery_point: str = Form(...),
    comment: str | None = Form(None),
):
    cart = request.session.get("cart", {})
    if not cart:
        return RedirectResponse(url="/order/create", status_code=303)

    product_ids = [int(pid) for pid in cart.keys()]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    cart_items = []
    total_price = Decimal("0.00")

    for pid_str, quantity in cart.items():
        pid = int(pid_str)
        product = product_map.get(pid)
        if not product:
            continue

        line_total = Decimal(str(product.price)) * quantity
        total_price += line_total

        cart_items.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": line_total,
            }
        )

    courier = db.get(Courier, courier_id)
    if not courier or not courier.is_approved:
        raise HTTPException(status_code=400, detail="Invalid courier")

    order = Order(
        user_id=user.id,
        courier_id=courier.id,
        status="created",
        delivery_point=delivery_point,
        total_price=total_price,
        comment=comment,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()  # чтобы получить order.id до commit

    for item in cart_items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item["product"].id,
                quantity=item["quantity"],
                price_snapshot=item["product"].price,
            )
        )

    db.add(
        OrderStatusHistory(
            order_id=order.id,
            old_status=None,
            new_status="created",
            changed_by=user.id,
        )
    )

    db.commit()
    request.session["cart"] = {}

    background_tasks.add_task(complete_order_later, order.id)

    return RedirectResponse(url=request.url_for("profile"), status_code=303)

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




@router.get("/order/create", response_class=HTMLResponse, name="order_create")
def order_create(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    cart = _get_cart(request)
    cart_items = _load_cart_items(db, cart)
    total_price = _cart_total(cart_items)

    couriers = (
        db.query(Courier)
        .filter(Courier.is_approved.is_(True))
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/order_create.html",
        context={
            "request": request,
            "user": user,
            "cart_items": cart_items,
            "total_items": _cart_count(cart),
            "total_price": total_price,
            "couriers": couriers,
            "delivery_points": [
                "Главный корпус",
                "Общежитие",
                "Столовая",
                "Библиотека",
            ],
        },
    )

@router.get("/profile", name="profile")
def profile(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    rows = (
        db.query(Order, Courier, User)
        .join(Courier, Order.courier_id == Courier.id, isouter=True)
        .join(User, Courier.user_id == User.id, isouter=True)
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    orders = []
    for order, courier, courier_user in rows:
        orders.append(
            {
                "id": order.id,
                "status": order.status,
                "created_at": order.created_at,
                "total_price": order.total_price,
                "courier_name": courier_user.username if courier_user else "Не назначен",
            }
        )

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/profile.html",
        context={
            "request": request,
            "user": user,
            "orders": orders,
            "recent_orders": orders,
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

    return RedirectResponse(url="/order/create", status_code=303)


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
        return RedirectResponse(url="/order/create", status_code=303)

    new_quantity = cart[key] + delta
    if new_quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = new_quantity

    request.session["cart"] = cart
    return RedirectResponse(url="/order/create", status_code=303)


@router.post("/cart/remove/{product_id}", name="cart_remove")
def cart_remove(
    request: Request,
    product_id: int,
    user=Depends(require_user),
):
    cart = _get_cart(request)
    cart.pop(str(product_id), None)
    request.session["cart"] = cart
    return RedirectResponse(url="/order/create", status_code=303)


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


def _order_status_label(status: str) -> str:
    return {
        "created": "Создан",
        "accepted": "Принят",
        "delivering": "Доставляется",
        "delivered": "Доставлен",
        "cancelled": "Отменён",
    }.get(status, status)


def _format_dt(value: datetime | None) -> str:
    return value.strftime("%d.%m.%Y %H:%M") if value else "—"


def _can_access_order(user: User, order: Order) -> bool:
    if user.role == "admin":
        return True
    if order.user_id == user.id:
        return True
    if user.role == "courier" and order.courier_id is not None:
        courier = getattr(order, "courier", None)
        if courier and courier.user_id == user.id:
            return True
    return False


@router.get("/orders/{order_id}", response_class=HTMLResponse, name="order_detail")
def order_detail(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = (
        db.query(Order)
        .options(
            selectinload(Order.courier).selectinload(Courier.user),
            selectinload(Order.user),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not _can_access_order(user, order):
        raise HTTPException(status_code=403, detail="Access denied")

    messages = (
        db.query(Message)
        .filter(Message.order_id == order.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    prepared_messages = []
    for msg in messages:
        prepared_messages.append(
            {
                "id": msg.id,
                "sender_name": msg.sender.username if msg.sender else "Пользователь",
                "is_mine": msg.sender_id == user.id,
                "text": msg.text,
                "created_at": _format_dt(msg.created_at),
            }
        )

    courier_name = None
    if order.courier and order.courier.user:
        courier_name = order.courier.user.username

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/order_detail.html",
        context={
            "request": request,
            "user": user,
            "order": {
                "id": order.id,
                "status": order.status.value if hasattr(order.status, "value") else str(order.status),
                "status_label": _order_status_label(
                    order.status.value if hasattr(order.status, "value") else str(order.status)
                ),
                "delivery_point": order.delivery_point,
                "courier_name": courier_name,
                "comment": order.comment,
                "total_price": order.total_price,
                "created_at": _format_dt(order.created_at),
                "updated_at": _format_dt(order.updated_at),
            },
            "messages": prepared_messages,
        },
    )


@router.get("/orders/{order_id}/track", response_class=HTMLResponse, name="order_track")
def order_track(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    return order_detail(request=request, order_id=order_id, db=db, user=user)


@router.post("/orders/{order_id}/messages", name="order_message_send")
def order_message_send(
    request: Request,
    order_id: int,
    text: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not _can_access_order(user, order):
        raise HTTPException(status_code=403, detail="Access denied")

    text = text.strip()
    if not text:
        return RedirectResponse(url=f"/orders/{order_id}", status_code=303)

    receiver_id = order.user_id
    if user.id == order.user_id and order.courier and order.courier.user_id:
        receiver_id = order.courier.user_id
    elif user.role == "courier" and order.user_id:
        receiver_id = order.user_id
    elif user.role == "admin":
        receiver_id = order.user_id

    message = Message(
        order_id=order.id,
        sender_id=user.id,
        receiver_id=receiver_id,
        text=text,
    )
    db.add(message)
    db.commit()

    return RedirectResponse(url=f"/orders/{order_id}", status_code=303)


@router.post("/orders/{order_id}/confirm", name="order_confirm_receipt")
def order_confirm_receipt(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    status_value = order.status.value if hasattr(order.status, "value") else str(order.status)
    if status_value != "delivered":
        return RedirectResponse(url=f"/orders/{order_id}", status_code=303)

    old_status = order.status
    order.status = "delivered"
    order.updated_at = datetime.utcnow()

    history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status="delivered",
        changed_by=user.id,
    )
    db.add(history)
    db.commit()

    return RedirectResponse(url=f"/orders/{order_id}", status_code=303)