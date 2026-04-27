from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db, require_user
from app.db.models import (
    Courier,
    Message,
    MessageType,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    Product,
    SystemEventType,
    User,
)

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _enum_value(value) -> str:
    return value.value if hasattr(value, 'value') else str(value)


def _format_dt(value: datetime | None) -> str:
    return value.strftime('%d.%m.%Y %H:%M') if value else '—'


def _order_status_label(status: str) -> str:
    return {
        'created': 'Создан',
        'pending_courier': 'Ожидает курьера',
        'accepted': 'Принят',
        'picked_up': 'Забран',
        'delivering': 'Доставляется',
        'delivered': 'Доставлен',
        'received': 'Получен',
        'rejected_by_courier': 'Отклонён курьером',
        'cancelled_by_client': 'Отменён клиентом',
        'cancelled_by_system': 'Отменён системой',
        'cancelled': 'Отменён',
    }.get(status, status)


def _get_cart(request: Request) -> dict[str, int]:
    cart = request.session.get('cart', {})
    return cart if isinstance(cart, dict) else {}


def _save_cart(request: Request, cart: dict[str, int]) -> None:
    request.session['cart'] = dict(cart)


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
        product = product_map.get(int(pid_str))
        if not product:
            continue
        price = Decimal(str(product.price))
        items.append({'product': product, 'quantity': quantity, 'line_total': price * quantity})
    return items


def _cart_total(cart_items: list[dict]) -> Decimal:
    return sum((item['line_total'] for item in cart_items), Decimal('0.00'))


def _get_order_or_404(db: Session, order_id: int) -> Order:
    order = (
        db.query(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.courier).selectinload(Courier.user),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.messages).selectinload(Message.sender),
            selectinload(Order.status_history).selectinload(OrderStatusHistory.changer),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    return order


def _courier_user_id(order: Order) -> int | None:
    if order.courier and order.courier.user:
        return order.courier.user.id
    return None


def _can_access_order(user: User, order: Order) -> bool:
    if user.role_value == 'admin':
        return True
    if user.role_value == 'client':
        return order.user_id == user.id
    if user.role_value == 'courier':
        return _courier_user_id(order) == user.id
    return False


def _require_access(user: User, order: Order) -> None:
    if not _can_access_order(user, order):
        raise HTTPException(status_code=403, detail='Access denied')


def _require_owner(user: User, order: Order) -> None:
    if user.role_value != 'admin' and order.user_id != user.id:
        raise HTTPException(status_code=403, detail='Only order owner can do this')


def _require_courier(user: User, order: Order) -> Courier:
    if user.role_value == 'admin':
        return order.courier  # type: ignore[return-value]
    if user.role_value != 'courier':
        raise HTTPException(status_code=403, detail='Only courier can do this')

    courier = order.courier
    if not courier or not courier.user or courier.user.id != user.id:
        raise HTTPException(status_code=403, detail='Only assigned courier can do this')
    return courier


def _resolve_receiver_id(order: Order, user: User) -> int | None:
    courier_user_id = _courier_user_id(order)
    if user.role_value == 'client':
        return courier_user_id
    if user.role_value == 'courier':
        return order.user_id
    if user.role_value == 'admin':
        return courier_user_id or order.user_id
    return None


def _serialize_message(message: Message, current_user: User) -> dict:
    sender_name = 'Система'
    if message.sender and message.sender.username:
        sender_name = message.sender.username

    return {
        'id': message.id,
        'sender_id': message.sender_id,
        'receiver_id': message.receiver_id,
        'sender_name': sender_name,
        'kind': 'system' if message.type == MessageType.system or message.sender_id is None else 'user',
        'is_mine': message.sender_id == current_user.id,
        'text': message.text,
        'created_at': _format_dt(message.created_at),
    }


def _serialize_order(order: Order) -> dict:
    courier_name = order.courier.user.username if order.courier and order.courier.user else None
    status = _enum_value(order.status)
    return {
        'id': order.id,
        'status': status,
        'status_label': _order_status_label(status),
        'delivery_point': order.delivery_point,
        'courier_name': courier_name,
        'comment': order.comment,
        'total_price': order.total_price,
        'created_at': _format_dt(order.created_at),
        'updated_at': _format_dt(order.updated_at),
        'courier_id': order.courier_id,
    }


def _serialize_order_for_poll(order: Order, current_user: User) -> dict:
    messages = [_serialize_message(message, current_user) for message in sorted(order.messages, key=lambda message: message.created_at or _now())]
    payload = _serialize_order(order)
    payload['total_price'] = float(order.total_price or 0)
    payload['messages'] = messages
    return payload


def _status_meta(new_status: OrderStatus) -> tuple[SystemEventType, str]:
    mapping = {
        OrderStatus.created: (SystemEventType.order_created, 'Заказ создан.'),
        OrderStatus.pending_courier: (SystemEventType.courier_assigned, 'Заказ ожидает курьера.'),
        OrderStatus.accepted: (SystemEventType.courier_accepted, 'Курьер принял заказ.'),
        OrderStatus.picked_up: (SystemEventType.order_picked_up, 'Курьер забрал заказ.'),
        OrderStatus.delivering: (SystemEventType.order_delivering, 'Курьер везёт заказ.'),
        OrderStatus.delivered: (SystemEventType.order_delivered, 'Курьер отметил заказ как доставленный.'),
        OrderStatus.received: (SystemEventType.order_received, 'Клиент подтвердил получение заказа.'),
        OrderStatus.rejected_by_courier: (SystemEventType.courier_rejected, 'Курьер отклонил заказ.'),
        OrderStatus.cancelled_by_client: (SystemEventType.order_cancelled, 'Клиент отменил заказ.'),
        OrderStatus.cancelled_by_system: (SystemEventType.order_cancelled, 'Заказ отменён системой.'),
    }
    return mapping.get(new_status, (SystemEventType.status_changed, 'Статус заказа изменён.'))


def _append_status_change(
    db: Session,
    order: Order,
    new_status: OrderStatus,
    changed_by: int | None,
) -> None:
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            old_status=order.status,
            new_status=new_status,
            changed_by=changed_by,
        )
    )

    order.status = new_status
    order.updated_at = _now()

    if new_status == OrderStatus.accepted:
        order.accepted_at = _now()
    elif new_status == OrderStatus.delivered:
        order.delivered_at = _now()
    elif new_status == OrderStatus.received:
        order.received_at = _now()

    event, text = _status_meta(new_status)
    db.add(
        Message(
            order_id=order.id,
            sender_id=None,
            receiver_id=None,
            type=MessageType.system,
            system_event=event,
            text=text,
            created_at=_now(),
        )
    )


def _apply_status_change(
    db: Session,
    order: Order,
    new_status: OrderStatus,
    changed_by: int | None,
) -> None:
    _append_status_change(db, order, new_status, changed_by)
    db.commit()


def _latest_accessible_order(db: Session, user: User) -> Order | None:
    query = (
        db.query(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.courier).selectinload(Courier.user),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.messages).selectinload(Message.sender),
        )
        .order_by(Order.created_at.desc())
    )

    if user.role_value == 'admin':
        return query.first()

    if user.role_value == 'courier':
        courier = db.query(Courier).filter(Courier.user_id == user.id).first()
        if courier:
            return query.filter(Order.courier_id == courier.id).first()
        return None

    return query.filter(Order.user_id == user.id).first()


def _order_context(request, order, user, can_confirm_receipt=False) -> dict:
    messages = [_serialize_message(message, current_user) for message in sorted(order.messages, key=lambda message: message.created_at or _now())]
    items = [
        {
            'product_name': item.product.name if item.product else f'Товар #{item.product_id}',
            'quantity': item.quantity,
            'price_snapshot': item.price_snapshot,
            'line_total': Decimal(str(item.price_snapshot)) * item.quantity,
        }
        for item in order.items
    ]
    return {
        'request': request,
        'user': current_user,
        'user_role': current_user.role_value,
        'can_confirm_receipt': current_user.role_value == 'admin' or order.user_id == current_user.id,
        'is_assigned_courier': _courier_user_id(order) == current_user.id,
        'order': _serialize_order(order),
        'messages': messages,
        'items': items,
        "user_role": user.role_value,
    }


@router.get('/', response_class=HTMLResponse, name='home')
def home(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    products = db.query(Product).limit(6).all()
    couriers = db.query(Courier).filter(Courier.is_approved.is_(True)).limit(4).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name='pages/home.html',
        context={
            'request': request,
            'user': user,
            'popular_products': products,
            'couriers': couriers,
        },
    )


@router.get('/catalog', response_class=HTMLResponse, name='catalog')
def catalog(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    products = db.query(Product).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name='pages/catalog.html',
        context={
            'request': request,
            'products': products,
            'categories': [],
            'filters': {},
            'user': user,
        },
    )


@router.get('/order/create', response_class=HTMLResponse, name='order_create')
def order_create(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    cart = _get_cart(request)
    cart_items = _load_cart_items(db, cart)
    total_price = _cart_total(cart_items)
    couriers = db.query(Courier).filter(Courier.is_approved.is_(True)).all()

    return request.app.state.templates.TemplateResponse(
        request=request,
        name='pages/order_create.html',
        context={
            'request': request,
            'user': user,
            'cart_items': cart_items,
            'total_items': _cart_count(cart),
            'total_price': total_price,
            'couriers': couriers,
            'delivery_points': ['Главный корпус', 'Общежитие', 'Столовая', 'Библиотека'],
        },
    )


@router.post('/cart/add/{product_id}', name='cart_add')
def cart_add(
    request: Request,
    product_id: int,
    quantity: int = Form(1),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail='Product not found')

    if quantity < 1:
        quantity = 1

    cart = _get_cart(request)
    key = str(product_id)
    cart[key] = cart.get(key, 0) + quantity
    _save_cart(request, cart)

    return RedirectResponse(url=request.url_for('order_create'), status_code=303)


@router.post('/cart/update/{product_id}', name='cart_update')
def cart_update(
    request: Request,
    product_id: int,
    delta: int = Form(...),
    user=Depends(require_user),
):
    cart = _get_cart(request)
    key = str(product_id)
    if key not in cart:
        return RedirectResponse(url=request.url_for('order_create'), status_code=303)

    new_quantity = cart[key] + delta
    if new_quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = new_quantity
    _save_cart(request, cart)
    return RedirectResponse(url=request.url_for('order_create'), status_code=303)


@router.post('/cart/set/{product_id}', name='cart_set')
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
    return RedirectResponse(url=request.url_for('order_create'), status_code=303)


@router.post('/cart/remove/{product_id}', name='cart_remove')
def cart_remove(
    request: Request,
    product_id: int,
    user=Depends(require_user),
):
    cart = _get_cart(request)
    cart.pop(str(product_id), None)
    _save_cart(request, cart)
    return RedirectResponse(url=request.url_for('order_create'), status_code=303)


@router.post('/cart/clear', name='cart_clear')
def cart_clear(
    request: Request,
    user=Depends(require_user),
):
    request.session['cart'] = {}
    return RedirectResponse(url=request.url_for('order_create'), status_code=303)


@router.post('/orders/create', name='orders_create')
def orders_create(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
    courier_id: int = Form(...),
    delivery_point: str = Form(...),
    comment: str | None = Form(None),
):
    cart = _get_cart(request)
    if not cart:
        return RedirectResponse(url=request.url_for('order_create'), status_code=303)

    cart_items = _load_cart_items(db, cart)
    if not cart_items:
        return RedirectResponse(url=request.url_for('order_create'), status_code=303)

    couriers = db.query(Courier).filter(Courier.is_approved.is_(True)).all()
    courier = next((c for c in couriers if c.id == courier_id), None)
    if not courier:
        raise HTTPException(status_code=400, detail='Invalid courier')

    total_price = _cart_total(cart_items)
    order = Order(
        user_id=user.id,
        courier_id=courier.id,
        status=OrderStatus.created,
        delivery_point=delivery_point,
        total_price=total_price,
        comment=comment.strip() if comment else None,
        updated_at=_now(),
    )
    db.add(order)
    db.flush()

    for item in cart_items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price_snapshot=item['product'].price,
            )
        )

    _append_status_change(db, order, OrderStatus.created, user.id)
    db.commit()
    _save_cart(request, {})

    return RedirectResponse(url=request.url_for('order_detail', order_id=order.id), status_code=303)


@router.get('/profile', name='profile')
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

    orders: list[dict] = []
    for order, courier, courier_user in rows:
        orders.append(
            {
                'id': order.id,
                'status': _enum_value(order.status),
                'created_at': order.created_at,
                'total_price': order.total_price,
                'courier_name': courier_user.username if courier_user else 'Не назначен',
            }
        )

    return request.app.state.templates.TemplateResponse(
        request=request,
        name='pages/profile.html',
        context={
            'request': request,
            'user': user,
            'orders': orders,
            'recent_orders': orders[:5],
        },
    )


@router.get('/orders/history', name='orders_history')
def orders_history(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    return profile(request=request, db=db, user=user)


@router.get('/chat', response_class=HTMLResponse, name='chat')
def chat(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
    order_id: int | None = None,
):
    order: Order | None = None
    if order_id is not None:
        order = _get_order_or_404(db, order_id)
        _require_access(user, order)
    else:
        order = _latest_accessible_order(db, user)

    if not order:
        return request.app.state.templates.TemplateResponse(
            request=request,
            name='pages/chat.html',
            context={'request': request, 'user': user, 'order': None, 'courier': None, 'messages': []},
        )

    order = _get_order_or_404(db, order.id)
    _require_access(user, order)

    return request.app.state.templates.TemplateResponse(
        request=request,
        name='pages/chat.html',
        context={
            'request': request,
            'user': user,
            'order': _serialize_order(order),
            'courier': order.courier,
            'messages': [_serialize_message(message, user) for message in sorted(order.messages, key=lambda message: message.created_at or _now())],
        },
    )


@router.get('/cart', response_class=HTMLResponse, name='cart')
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
        name='pages/cart.html',
        context={
            'request': request,
            'user': user,
            'cart_items': cart_items,
            'total_price': total_price,
            'total_items': _cart_count(cart),
        },
    )


@router.get('/orders/{order_id}', response_class=HTMLResponse, name='order_detail')
def order_detail(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    _require_access(user, order)

    status_value = order.status.value if hasattr(order.status, "value") else str(order.status)

    can_confirm_receipt = (
        user.role_value == "client"
        and order.user_id == user.id
        and status_value == "delivered"
    )

    context = _order_context(request, order, user)
    context["can_confirm_receipt"] = can_confirm_receipt
    context["user_role"] = user.role_value
    return request.app.state.templates.TemplateResponse(
        request=request,
        name='pages/order_detail.html',
        context=context,
    )
@router.get('/orders/{order_id}/track', response_class=HTMLResponse, name='order_track')
def order_track(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    _require_access(user, order)

    history = sorted(order.status_history, key=lambda item: item.created_at or _now())
    return request.app.state.templates.TemplateResponse(
        request=request,
        name='pages/order_track.html',
        context={
            'request': request,
            'user': user,
            'order': _serialize_order(order),
            'courier': order.courier,
            'history': history,
            'last_updated': _format_dt(order.updated_at),
            'status': _enum_value(order.status),
            'label': _order_status_label(_enum_value(order.status)),
        },
    )


@router.post('/orders/{order_id}/messages', name='order_message_send')
def order_message_send(
    request: Request,
    order_id: int,
    text: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    _require_access(user, order)

    text = text.strip()
    if not text:
        return RedirectResponse(url=request.url_for('order_detail', order_id=order.id), status_code=303)

    message = Message(
        order_id=order.id,
        sender_id=user.id,
        receiver_id=_resolve_receiver_id(order, user),
        type=MessageType.user,
        system_event=None,
        text=text,
        created_at=_now(),
    )
    db.add(message)
    db.commit()

    return RedirectResponse(url=request.url_for('order_detail', order_id=order.id), status_code=303)


@router.post('/orders/{order_id}/confirm', name='order_confirm_receipt')
def order_confirm_receipt(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    _require_owner(user, order)

    if _enum_value(order.status) != 'delivered':
        return RedirectResponse(url=request.url_for('order_detail', order_id=order.id), status_code=303)

    _append_status_change(db, order, OrderStatus.received, user.id)
    db.commit()
    return RedirectResponse(url=request.url_for('order_detail', order_id=order.id), status_code=303)


@router.get('/courier/orders', response_class=HTMLResponse, name='courier_orders')
def courier_orders(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    if user.role_value not in {'courier', 'admin'}:
        raise HTTPException(status_code=403, detail='Access denied')

    courier_profile = None
    if user.role_value == 'courier':
        courier_profile = db.query(Courier).filter(Courier.user_id == user.id).first()

    query = (
        db.query(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.courier).selectinload(Courier.user),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.messages).selectinload(Message.sender),
        )
        .order_by(Order.created_at.desc())
    )

    if user.role_value == 'courier':
        if courier_profile:
            query = query.filter(or_(Order.courier_id == courier_profile.id, Order.status.in_([OrderStatus.created, OrderStatus.pending_courier])))
        else:
            query = query.filter(Order.status.in_([OrderStatus.created, OrderStatus.pending_courier]))

    orders = query.all()
    payload = []
    for order in orders:
        payload.append(
            {
                'id': order.id,
                'status': _enum_value(order.status),
                'status_label': _order_status_label(_enum_value(order.status)),
                'client_name': order.user.username if order.user else '—',
                'delivery_point': order.delivery_point,
                'created_at': _format_dt(order.created_at),
                'total_price': order.total_price,
                'order_items': [
                    {
                        'product_name': item.product.name if item.product else f'Товар #{item.product_id}',
                        'quantity': item.quantity,
                        'line_total': Decimal(str(item.price_snapshot)) * item.quantity,
                        'price_snapshot': item.price_snapshot,
                    }
                    for item in order.items
                ],
                'messages': [_serialize_message(message, user) for message in sorted(order.messages, key=lambda message: message.created_at or _now())],
            }
        )

    return request.app.state.templates.TemplateResponse(
        request=request,
        name='pages/courier_orders.html',
        context={
            'request': request,
            'user': user,
            'orders': payload,
        },
    )


@router.post('/courier/orders/{order_id}/accept', name='courier_order_accept')
def courier_order_accept(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    if user.role_value != 'courier':
        raise HTTPException(status_code=403, detail='Only courier can do this')

    courier = db.query(Courier).filter(Courier.user_id == user.id).first()
    if not courier:
        raise HTTPException(status_code=403, detail='Courier profile not found')

    if order.courier_id not in (None, courier.id):
        raise HTTPException(status_code=409, detail='Order already assigned')

    if _enum_value(order.status) not in {'created', 'pending_courier'}:
        raise HTTPException(status_code=400, detail='Order cannot be accepted now')

    order.courier_id = courier.id
    _append_status_change(db, order, OrderStatus.accepted, user.id)
    db.commit()
    return RedirectResponse(url=request.url_for('courier_orders'), status_code=303)


@router.post('/courier/orders/{order_id}/reject', name='courier_order_reject')
def courier_order_reject(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    if user.role_value != 'courier':
        raise HTTPException(status_code=403, detail='Only courier can do this')

    courier = db.query(Courier).filter(Courier.user_id == user.id).first()
    if not courier:
        raise HTTPException(status_code=403, detail='Courier profile not found')

    if order.courier_id not in (None, courier.id):
        raise HTTPException(status_code=409, detail='Order already assigned')

    if _enum_value(order.status) not in {'created', 'pending_courier', 'accepted'}:
        raise HTTPException(status_code=400, detail='Order cannot be rejected now')

    order.courier_id = courier.id
    _append_status_change(db, order, OrderStatus.rejected_by_courier, user.id)
    db.commit()
    return RedirectResponse(url=request.url_for('courier_orders'), status_code=303)


@router.post('/courier/orders/{order_id}/mark-delivering', name='courier_order_mark_delivering')
def courier_order_mark_delivering(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    _require_courier(user, order)

    if _enum_value(order.status) not in {'accepted', 'picked_up'}:
        raise HTTPException(status_code=400, detail='Order cannot be moved to delivering now')

    _append_status_change(db, order, OrderStatus.delivering, user.id)
    db.commit()
    return RedirectResponse(url=request.url_for('courier_orders'), status_code=303)


@router.post('/courier/orders/{order_id}/mark-delivered', name='courier_order_mark_delivered')
def courier_order_mark_delivered(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    _require_courier(user, order)

    if _enum_value(order.status) not in {'accepted', 'picked_up', 'delivering'}:
        raise HTTPException(status_code=400, detail='Order cannot be marked as delivered now')

    _append_status_change(db, order, OrderStatus.delivered, user.id)
    db.commit()
    return RedirectResponse(url=request.url_for('courier_orders'), status_code=303)