
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Literal


# USER REGISTRATION
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    role: Literal["customer", "courier"] = "customer"


# USER LOGIN
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# CREATE ORDER
class OrderCreate(BaseModel):
    pickup_address: str
    delivery_address: str
    package_details: str
    delivery_time: Optional[datetime] = None


# ADMIN UPDATE ORDER
class OrderAdminUpdate(BaseModel):
    pickup_address: Optional[str] = None
    delivery_address: Optional[str] = None
    package_details: Optional[str] = None
    delivery_time: Optional[datetime] = None


# UPDATE ORDER STATUS
class OrderStatusUpdate(BaseModel):
    status: Literal["Picked Up", "In Transit", "Delivered"]
    note: Optional[str] = None


# ASSIGN ORDER TO COURIER
class AssignmentCreate(BaseModel):
    order_id: int
    courier_id: int


# COURIER ACCEPT OR DECLINE ASSIGNMENT
class AssignmentDecision(BaseModel):
    status: Literal["Accepted", "Declined"]
