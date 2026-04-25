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
    email = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.client, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    orders = relationship("Order", back_populates="user")

    @property
    def is_verified(self):
        return False


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(DECIMAL, nullable=False)
    description = Column(Text)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.created, nullable=False)
    total_price = Column(DECIMAL, nullable=False, default=0)

    user = relationship("User", back_populates="orders")