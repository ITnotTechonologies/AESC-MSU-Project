from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.models import Product as ProductModel
from app.schemas.product import Product as ProductSchema
from app.api.deps import get_db

router = APIRouter()

@router.get("/products", response_model=list[ProductSchema])
def get_products(db: Session = Depends(get_db)):
    products = db.query(ProductModel).all()
    return products