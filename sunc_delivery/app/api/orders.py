# Legacy code

raise RuntimeError(
    "app/api/orders.py отключён. Используйте app/api/views.py как единственный source of truth."
)

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_user
from app.db.models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    Message,
    User,
    Courier,
    OrderStatus,
    MessageType,
    SystemEventType,
)

router = APIRouter()


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _can_view_order(user: User, order: Order, courier_user_id: Optional[int]) -> bool:
    if user.role == "admin":
        return True
    if user.role == "client":
        return order.user_id == user.id
    if user.role == "courier":
        return courier_user_id is not None and courier_user_id == user.id
    return False


def _require_view_access(user: User, order: Order, courier_user_id: Optional[int]) -> None:
    if not _can_view_order(user, order, courier_user_id):
        raise HTTPException(status_code=403, detail="Access denied")


def _require_owner(user: User, order: Order) -> None:
    if user.role != "admin" and order.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only order owner can do this")


def _require_courier(user: User, order: Order, courier_user_id: Optional[int]) -> None:
    if user.role == "admin":
        return
    if user.role != "courier" or courier_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only assigned courier can do this")


def _append_status_history(
    db: Session,
    order: Order,
    new_status: OrderStatus,
    changed_by: Optional[int],
) -> None:
    history = OrderStatusHistory(
        order_id=order.id,
        old_status=order.status,
        new_status=new_status,
        changed_by=changed_by,
        created_at=_now(),
    )
    db.add(history)


def _append_system_message(
    db: Session,
    order: Order,
    event: SystemEventType,
    text: str,
    receiver_id: Optional[int] = None,
) -> None:
    db.add(
        Message(
            order_id=order.id,
            sender_id=None,
            receiver_id=receiver_id,
            type=MessageType.system,
            system_event=event,
            text=text,
            created_at=_now(),
        )
    )


def _get_order_participants(db: Session, order: Order) -> tuple[Optional[Courier], Optional[User]]:
    courier = None
    courier_user = None
    if order.courier_id:
        courier = db.get(Courier, order.courier_id)
        if courier:
            courier_user = db.get(User, courier.user_id)
    return courier, courier_user


def _resolve_receiver_id(db: Session, order: Order, current_user: User) -> Optional[int]:
    """
    For MVP:
    - if client writes, receiver is courier user if assigned
    - if courier writes, receiver is order owner
    - admin can be treated as no receiver or the opposite side
    """
    courier, courier_user = _get_order_participants(db, order)

    if current_user.role == "client":
        return courier_user.id if courier_user else None
    if current_user.role == "courier":
        return order.user_id
    if current_user.role == "admin":
        if courier_user:
            return courier_user.id
        return order.user_id
    return None


def _status_to_event_and_text(status_value: OrderStatus) -> tuple[SystemEventType, str]:
    mapping = {
        OrderStatus.accepted: (
            SystemEventType.courier_accepted,
            "Курьер принял заказ.",
        ),
        OrderStatus.rejected_by_courier: (
            SystemEventType.courier_rejected,
            "Курьер отклонил заказ.",
        ),
        OrderStatus.picked_up: (
            SystemEventType.order_picked_up,
            "Курьер забрал заказ.",
        ),
        OrderStatus.delivering: (
            SystemEventType.order_delivering,
            "Заказ передан в доставку.",
        ),
        OrderStatus.delivered: (
            SystemEventType.order_delivered,
            "Курьер отметил заказ как доставленный.",
        ),
        OrderStatus.received: (
            SystemEventType.order_received,
            "Клиент подтвердил получение заказа.",
        ),
    }

    if status_value not in mapping:
        return SystemEventType.status_changed, "Статус заказа изменён."

    return mapping[status_value]


def _change_status(
    db: Session,
    order: Order,
    new_status: OrderStatus,
    changed_by: Optional[int],
    receiver_id: Optional[int],
) -> None:
    _append_status_history(db, order, new_status, changed_by)
    order.status = new_status
    order.updated_at = _now()

    event, text = _status_to_event_and_text(new_status)
    _append_system_message(db, order, event, text, receiver_id=receiver_id)


# ---------------------------------------------------------
# Actions
# ---------------------------------------------------------

@router.post("/orders/{order_id}/accept", name="order_accept")
def accept_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    courier, courier_user = _get_order_participants(db, order)

    if current_user.role != "courier":
        raise HTTPException(status_code=403, detail="Only courier can accept orders")

    if order.status not in (OrderStatus.created, OrderStatus.pending_courier):
        raise HTTPException(status_code=400, detail="Order cannot be accepted now")

    # Bind order to current courier
    current_courier = db.query(Courier).filter(Courier.user_id == current_user.id).first()
    if not current_courier:
        raise HTTPException(status_code=403, detail="Courier profile not found")

    if order.courier_id is not None and order.courier_id != current_courier.id:
        raise HTTPException(status_code=409, detail="Order already assigned")

    order.courier_id = current_courier.id

    receiver_id = order.user_id
    _change_status(
        db=db,
        order=order,
        new_status=OrderStatus.accepted,
        changed_by=current_user.id,
        receiver_id=receiver_id,
    )

    db.commit()
    return RedirectResponse(url=f"/orders/{order.id}", status_code=303)


@router.post("/orders/{order_id}/reject", name="order_reject")
def reject_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    order = _get_order_or_404(db, order_id)

    if current_user.role != "courier":
        raise HTTPException(status_code=403, detail="Only courier can reject orders")

    if order.status not in (OrderStatus.created, OrderStatus.pending_courier, OrderStatus.accepted):
        raise HTTPException(status_code=400, detail="Order cannot be rejected now")

    current_courier = db.query(Courier).filter(Courier.user_id == current_user.id).first()
    if not current_courier:
        raise HTTPException(status_code=403, detail="Courier profile not found")

    # Minimal MVP behavior:
    # if the order was not assigned yet, assign it to the rejecting courier for traceability
    if order.courier_id is None:
        order.courier_id = current_courier.id

    receiver_id = order.user_id
    _change_status(
        db=db,
        order=order,
        new_status=OrderStatus.rejected_by_courier,
        changed_by=current_user.id,
        receiver_id=receiver_id,
    )

    db.commit()
    return RedirectResponse(url=f"/orders/{order.id}", status_code=303)


@router.post("/orders/{order_id}/mark-delivered", name="order_mark_delivered")
def mark_delivered(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    courier, courier_user = _get_order_participants(db, order)

    _require_courier(current_user, order, courier_user.id if courier_user else None)

    if order.status not in (OrderStatus.accepted, OrderStatus.picked_up, OrderStatus.delivering):
        raise HTTPException(status_code=400, detail="Order cannot be marked as delivered now")

    receiver_id = order.user_id
    _change_status(
        db=db,
        order=order,
        new_status=OrderStatus.delivered,
        changed_by=current_user.id,
        receiver_id=receiver_id,
    )

    order.delivered_at = _now()
    db.commit()
    return RedirectResponse(url=f"/orders/{order.id}", status_code=303)


@router.post("/orders/{order_id}/confirm-received", name="order_confirm_received")
def confirm_received(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    courier, courier_user = _get_order_participants(db, order)

    _require_owner(current_user, order)

    if order.status != OrderStatus.delivered:
        raise HTTPException(status_code=400, detail="Order is not delivered yet")

    receiver_id = courier_user.id if courier_user else None
    _change_status(
        db=db,
        order=order,
        new_status=OrderStatus.received,
        changed_by=current_user.id,
        receiver_id=receiver_id,
    )

    order.received_at = _now()
    db.commit()
    return RedirectResponse(url=f"/orders/{order.id}", status_code=303)


# ---------------------------------------------------------
# Messages
# ---------------------------------------------------------

@router.get("/orders/{order_id}/messages", name="order_messages")
def get_order_messages(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    courier, courier_user = _get_order_participants(db, order)
    _require_view_access(current_user, order, courier_user.id if courier_user else None)

    messages = (
        db.query(Message)
        .filter(Message.order_id == order.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return {
        "order_id": order.id,
        "messages": [
            {
                "id": m.id,
                "type": m.type,
                "system_event": m.system_event,
                "text": m.text,
                "sender_id": m.sender_id,
                "receiver_id": m.receiver_id,
                "created_at": m.created_at,
                "read_at": m.read_at,
            }
            for m in messages
        ],
    }


@router.post("/orders/{order_id}/messages", name="order_messages_create")
def create_order_message(
    order_id: int,
    text: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    order = _get_order_or_404(db, order_id)
    courier, courier_user = _get_order_participants(db, order)
    _require_view_access(current_user, order, courier_user.id if courier_user else None)

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Extra safety: client can write only to own order, courier only to assigned order
    if current_user.role == "client" and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if current_user.role == "courier":
        if not courier_user or courier_user.id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    receiver_id = _resolve_receiver_id(db, order, current_user)

    message = Message(
        order_id=order.id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        type=MessageType.user,
        system_event=None,
        text=text,
        created_at=_now(),
    )
    db.add(message)
    db.commit()

    return RedirectResponse(url=f"/orders/{order.id}", status_code=303)