"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Brand information (static for this app)
class Brand(BaseModel):
    name: str = Field(..., description="Brand name displayed on receipts")
    phone: Optional[str] = Field(None, description="Contact phone number")
    logo_url: Optional[str] = Field(None, description="Public URL to brand logo image")

class ReceiptItem(BaseModel):
    name: str = Field(..., description="Item name/description")
    quantity: int = Field(1, ge=1, description="Quantity of the item")
    price: float = Field(..., ge=0, description="Unit price of the item")

class Receipt(BaseModel):
    """
    Receipts collection schema
    Collection name: "receipt"
    """
    number: int = Field(..., ge=1, description="Sequential receipt number")
    brand: Brand
    customer_name: Optional[str] = Field(None, description="Customer name")
    items: List[ReceiptItem] = Field(default_factory=list)
    notes: Optional[str] = Field(None, description="Optional notes")
    subtotal: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Example schemas kept for reference (not used by the app)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
