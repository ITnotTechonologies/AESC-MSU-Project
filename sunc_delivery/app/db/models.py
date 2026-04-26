from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class MessageType(str, enum.Enum):
    user = 'user'
    system = 'system'


class SystemEventType(str, enum.Enum):
    order_created = 'order_created'
    courier_assigned = 'courier_assigned'
    courier_accepted = 'courier_accepted'
    courier_rejected = 'courier_rejected'
    order_picked_up = 'order_picked_up'
    order_delivering = 'order_delivering'
    order_delivered = 'order_delivered'
    order_received = 'order_received'
    order_cancelled = 'order_cancelled'
    status_changed = 'status_changed'


class UserRole(str, enum.Enum):
    client = 'client'
    courier = 'courier'
    admin = 'admin'


class OrderStatus(str, enum.Enum):
    created = 'created'
    pending_courier = 'pending_courier'
    accepted = 'accepted'
    picked_up = 'picked_up'
    delivering = 'delivering'
    delivered = 'delivered'
    received = 'received'
    rejected_by_courier = 'rejected_by_courier'
    cancelled_by_client = 'cancelled_by_client'
    cancelled_by_system = 'cancelled_by_system'


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    products = relationship('Product', back_populates='category')


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole, name='user_role', native_enum=False), default=UserRole.client, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    orders = relationship('Order', back_populates='user')
    courier_profile = relationship('Courier', back_populates='user', uselist=False)

    @property
    def role_value(self) -> str:
        return self.role.value if hasattr(self.role, 'value') else str(self.role)


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String(500))
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    source_type = Column(String(50), nullable=False, default='internal')
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    category = relationship('Category', back_populates='products')


class Courier(Base):
    __tablename__ = 'couriers'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    rating = Column(Numeric(3, 2), default=5.00, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship('User', back_populates='courier_profile')
    orders = relationship('Order', back_populates='courier')


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    courier_id = Column(Integer, ForeignKey('couriers.id'), nullable=True)

    status = Column(Enum(OrderStatus, name='order_status', native_enum=False), default=OrderStatus.created, nullable=False)
    delivery_point = Column(String, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False, default=0.00)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship('User', back_populates='orders')
    courier = relationship('Courier', back_populates='orders')
    items = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    messages = relationship('Message', back_populates='order', cascade='all, delete-orphan')
    status_history = relationship('OrderStatusHistory', back_populates='order', cascade='all, delete-orphan')


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_snapshot = Column(Numeric(10, 2), nullable=False)

    order = relationship('Order', back_populates='items')
    product = relationship('Product')


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    receiver_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    type = Column(Enum(MessageType, name='message_type', native_enum=False), default=MessageType.user, nullable=False)
    system_event = Column(Enum(SystemEventType, name='system_event_type', native_enum=False), nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship('Order', back_populates='messages')
    sender = relationship('User', foreign_keys=[sender_id])
    receiver = relationship('User', foreign_keys=[receiver_id])


class OrderStatusHistory(Base):
    __tablename__ = 'order_status_history'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    old_status = Column(Enum(OrderStatus, name='order_status_hist_enum', native_enum=False), nullable=True)
    new_status = Column(Enum(OrderStatus, name='order_status_hist_enum2', native_enum=False), nullable=False)
    changed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship('Order', back_populates='status_history')
    changer = relationship('User')
