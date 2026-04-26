from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db, require_user
from app.db.models import Courier, Message, Order, User
from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
def ping():
    return {"status": "ok"}


def _format_dt(value: datetime | None) -> str:
    return value.strftime("%d.%m.%Y %H:%M") if value else "—"


def _order_status_label(status: str) -> str:
    return {
        "created": "Создан",
        "accepted": "Принят",
        "delivering": "Доставляется",
        "delivered": "Доставлен",
        "cancelled": "Отменён",
    }.get(status, status)


def _can_access_order(user: User, order: Order) -> bool:
    if user.role == "admin":
        return True
    if order.user_id == user.id:
        return True
    if user.role == "courier" and order.courier and order.courier.user_id == user.id:
        return True
    return False


@router.get("/orders/{order_id}/poll", name="order_poll")
def order_poll(
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

    order_status = order.status.value if hasattr(order.status, "value") else str(order.status)

    payload_messages = []
    for m in messages:
        sender_name = "Пользователь"
        if m.sender and m.sender.username:
            sender_name = m.sender.username

        payload_messages.append(
            {
                "id": m.id,
                "sender_name": sender_name,
                "is_mine": m.sender_id == user.id,
                "text": m.text,
                "created_at": _format_dt(m.created_at),
                "kind": "system" if m.sender_id is None else "user",
            }
        )

    courier_name = None
    if order.courier and order.courier.user:
        courier_name = order.courier.user.username

    return {
        "order": {
            "id": order.id,
            "status": order_status,
            "status_label": _order_status_label(order_status),
            "delivery_point": order.delivery_point,
            "courier_name": courier_name,
            "comment": order.comment,
            "total_price": float(order.total_price or 0),
            "updated_at": _format_dt(order.updated_at),
        },
        "messages": payload_messages,
    }