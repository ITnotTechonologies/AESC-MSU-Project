from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DECIMAL, Enum
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum


class UserRole(str, enum.Enum):
    client = "client"
    courier = "courier"
    admin = "admin"


class OrderStatus(str, enum.Enum):
    created = "created"
    accepted = "accepted"
    delivering = "delivering"
    delivered = "delivered"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    username = Column(String)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.client)
    is_active = Column(Boolean, default=True)

    orders = relationship("Order", back_populates="user")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(DECIMAL)
    description = Column(Text)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(OrderStatus), default=OrderStatus.created)
    total_price = Column(DECIMAL)

    user = relationship("User", back_populates="orders")