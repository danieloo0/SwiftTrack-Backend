
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend import crud, schemas, models
from backend.database import get_db, test_connection
from backend.auth import create_access_token, get_current_user


app = FastAPI(
    title="Package Tracking System",
    version="1.0.0",
    description="Backend API for package delivery management"
)

# CORS CONFIGURATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# HOME
@app.get("/")
def home():
    return {"message": "Package Tracking System API is running!"}


# HEALTH CHECK
@app.get("/health")
def health_check():
    return {"status": "OK"}


# DATABASE HEALTH
@app.get("/db-health")
def database_health():
    test_connection()
    return {"database": "Connected"}


# REGISTER
@app.post("/register", status_code=201)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = crud.get_user_by_email(db, user.email)

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = crud.create_user(db, user)

    return {
        "message": "Account created successfully!",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "phone": new_user.phone,
            "role": new_user.role
        }
    }


# LOGIN
@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    existing_user = crud.get_user_by_email(db, user.email)

    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    password_is_correct = crud.verify_password(
        user.password,
        existing_user.password_hash
    )

    if not password_is_correct:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(existing_user.id, existing_user.role)

    return {
        "message": "Login successful!",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": existing_user.id,
            "name": existing_user.name,
            "email": existing_user.email,
            "role": existing_user.role
        }
    }


# CREATE ORDER
@app.post("/orders", status_code=201)
def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can create orders")

    new_order = models.Order(
        customer_id=current_user.id,
        pickup_address=order.pickup_address,
        delivery_address=order.delivery_address,
        package_details=order.package_details,
        delivery_time=order.delivery_time,
        status="Pending"
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return {
        "message": "Order created successfully!",
        "order": {
            "id": new_order.id,
            "customer_id": new_order.customer_id,
            "pickup_address": new_order.pickup_address,
            "delivery_address": new_order.delivery_address,
            "package_details": new_order.package_details,
            "delivery_time": new_order.delivery_time,
            "status": new_order.status
        }
    }


# GET CUSTOMER ORDERS
@app.get("/orders/my-orders")
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can view their orders")

    orders = db.query(models.Order).filter(
        models.Order.customer_id == current_user.id
    ).all()

    return {
        "message": "Orders retrieved successfully!",
        "total_orders": len(orders),
        "orders": [
            {
                "id": order.id,
                "pickup_address": order.pickup_address,
                "delivery_address": order.delivery_address,
                "package_details": order.package_details,
                "delivery_time": order.delivery_time,
                "status": order.status
            }
            for order in orders
        ]
    }


# GET ORDER DETAILS
@app.get("/orders/{order_id}")
def get_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can view these order details")

    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.customer_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "id": order.id,
        "pickup_address": order.pickup_address,
        "delivery_address": order.delivery_address,
        "package_details": order.package_details,
        "delivery_time": order.delivery_time,
        "status": order.status
    }


# CANCEL ORDER
@app.delete("/orders/{order_id}")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can cancel orders")

    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.customer_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending orders can be cancelled")

    order.status = "Cancelled"
    db.commit()

    return {"message": "Order cancelled successfully!"}


# GET COURIER ORDERS
@app.get("/courier/orders")
def get_courier_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "courier":
        raise HTTPException(status_code=403, detail="Only couriers can view assigned orders")

    assignments = db.query(models.Assignment).filter(
        models.Assignment.courier_id == current_user.id
    ).all()

    result = []

    for assignment in assignments:
        order = db.query(models.Order).filter(
            models.Order.id == assignment.order_id
        ).first()

        if order:
            result.append({
                "assignment_id": assignment.id,
                "order_id": order.id,
                "assignment_status": assignment.assignment_status,
                "order_status": order.status,
                "pickup_address": order.pickup_address,
                "delivery_address": order.delivery_address,
                "package_details": order.package_details
            })

    return {"total_orders": len(result), "orders": result}


# COURIER ACCEPT OR DECLINE ASSIGNMENT
@app.put("/courier/assignments/{assignment_id}")
def decide_assignment(
    assignment_id: int,
    decision: schemas.AssignmentDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "courier":
        raise HTTPException(status_code=403, detail="Only couriers can accept or decline assignments")

    assignment = db.query(models.Assignment).filter(
        models.Assignment.id == assignment_id,
        models.Assignment.courier_id == current_user.id
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.assignment_status != "Assigned":
        raise HTTPException(status_code=400, detail="This assignment has already been processed")

    order = db.query(models.Order).filter(
        models.Order.id == assignment.order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    assignment.assignment_status = decision.status

    if decision.status == "Accepted":
        order.status = "Accepted"
        history_note = "Courier accepted the assignment"
    else:
        order.status = "Pending"
        history_note = "Courier declined the assignment"

    history = models.OrderStatusHistory(
        order_id=order.id,
        changed_by=current_user.id,
        status=order.status,
        note=history_note
    )

    db.add(history)
    db.commit()

    return {
        "message": f"Assignment {decision.status.lower()} successfully!",
        "assignment_id": assignment.id,
        "order_id": order.id,
        "assignment_status": assignment.assignment_status,
        "order_status": order.status
    }


# COURIER UPDATE DELIVERY STATUS
@app.put("/courier/orders/{order_id}/status")
def update_delivery_status(
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "courier":
        raise HTTPException(status_code=403, detail="Only couriers can update delivery status")

    assignment = db.query(models.Assignment).filter(
        models.Assignment.order_id == order_id,
        models.Assignment.courier_id == current_user.id,
        models.Assignment.assignment_status == "Accepted"
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Accepted assignment not found")

    order = db.query(models.Order).filter(
        models.Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed_transitions = {
        "Accepted": "Picked Up",
        "Picked Up": "In Transit",
        "In Transit": "Delivered"
    }

    expected_status = allowed_transitions.get(order.status)

    if status_update.status != expected_status:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status change. Expected: {expected_status}"
        )

    order.status = status_update.status

    history = models.OrderStatusHistory(
        order_id=order.id,
        changed_by=current_user.id,
        status=order.status,
        note=status_update.note
    )

    db.add(history)
    db.commit()

    return {
        "message": "Delivery status updated successfully!",
        "order_id": order.id,
        "status": order.status
    }


# ADMIN VIEW ALL ORDERS
@app.get("/admin/orders")
def admin_get_all_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view all orders")

    orders = db.query(models.Order).all()
    result = []

    for order in orders:
        customer = db.query(models.User).filter(
            models.User.id == order.customer_id
        ).first()

        result.append({
            "id": order.id,
            "customer_id": order.customer_id,
            "customer_name": customer.name if customer else None,
            "pickup_address": order.pickup_address,
            "delivery_address": order.delivery_address,
            "package_details": order.package_details,
            "delivery_time": order.delivery_time,
            "status": order.status
        })

    return {"total_orders": len(result), "orders": result}


# ADMIN VIEW ALL ASSIGNMENTS
@app.get("/admin/assignments")
def admin_get_all_assignments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view assignments")

    assignments = db.query(models.Assignment).all()
    result = []

    for assignment in assignments:
        order = db.query(models.Order).filter(
            models.Order.id == assignment.order_id
        ).first()

        courier = db.query(models.User).filter(
            models.User.id == assignment.courier_id
        ).first()

        result.append({
            "assignment_id": assignment.id,
            "order_id": assignment.order_id,
            "order_status": order.status if order else None,
            "courier_id": assignment.courier_id,
            "courier_name": courier.name if courier else None,
            "assignment_status": assignment.assignment_status,
            "assigned_at": assignment.assigned_at
        })

    return {"total_assignments": len(result), "assignments": result}


# ADMIN UPDATE ORDER DETAILS
@app.put("/admin/orders/{order_id}")
def admin_update_order(
    order_id: int,
    order_data: schemas.OrderAdminUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update orders")

    order = db.query(models.Order).filter(
        models.Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    updates = order_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No order details provided for update")

    for field, value in updates.items():
        setattr(order, field, value)

    db.commit()
    db.refresh(order)

    return {
        "message": "Order updated successfully!",
        "order_id": order.id,
        "pickup_address": order.pickup_address,
        "delivery_address": order.delivery_address,
        "package_details": order.package_details,
        "delivery_time": order.delivery_time,
        "status": order.status
    }


# ADMIN DELETE ORDER
@app.delete("/admin/orders/{order_id}")
def admin_delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete orders")

    order = db.query(models.Order).filter(
        models.Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.query(models.OrderStatusHistory).filter(
        models.OrderStatusHistory.order_id == order_id
    ).delete(synchronize_session=False)

    db.query(models.Assignment).filter(
        models.Assignment.order_id == order_id
    ).delete(synchronize_session=False)

    db.delete(order)
    db.commit()

    return {"message": "Order deleted successfully!", "order_id": order_id}


# ADMIN ASSIGN ORDER TO COURIER
@app.post("/admin/assign-order")
def assign_order_to_courier(
    assignment: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can assign orders")

    order = db.query(models.Order).filter(
        models.Order.id == assignment.order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    courier = db.query(models.User).filter(
        models.User.id == assignment.courier_id,
        models.User.role == "courier"
    ).first()

    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")

    if order.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending orders can be assigned")

    existing_assignment = db.query(models.Assignment).filter(
        models.Assignment.order_id == assignment.order_id
    ).first()

    if existing_assignment:
        raise HTTPException(
            status_code=400,
            detail="This order already has an assignment. Use the reassign endpoint."
        )

    new_assignment = models.Assignment(
        order_id=order.id,
        courier_id=courier.id,
        assignment_status="Assigned"
    )

    db.add(new_assignment)
    order.status = "Assigned"

    history = models.OrderStatusHistory(
        order_id=order.id,
        changed_by=current_user.id,
        status="Assigned",
        note="Order assigned to courier"
    )

    db.add(history)
    db.commit()
    db.refresh(new_assignment)

    return {
        "message": "Order assigned successfully!",
        "assignment_id": new_assignment.id,
        "order_id": order.id,
        "courier_id": courier.id,
        "courier_name": courier.name,
        "status": order.status
    }


# ADMIN REASSIGN ORDER TO ANOTHER COURIER
@app.put("/admin/reassign-order")
def admin_reassign_order(
    assignment_data: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can reassign orders")

    order = db.query(models.Order).filter(
        models.Order.id == assignment_data.order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ["Pending", "Assigned"]:
        raise HTTPException(
            status_code=400,
            detail="Only pending or assigned orders can be reassigned"
        )

    courier = db.query(models.User).filter(
        models.User.id == assignment_data.courier_id,
        models.User.role == "courier"
    ).first()

    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")

    existing_assignment = db.query(models.Assignment).filter(
        models.Assignment.order_id == assignment_data.order_id
    ).first()

    if existing_assignment:
        existing_assignment.courier_id = courier.id
        existing_assignment.assignment_status = "Assigned"
        order.status = "Assigned"
        assignment_id = existing_assignment.id
    else:
        new_assignment = models.Assignment(
            order_id=order.id,
            courier_id=courier.id,
            assignment_status="Assigned"
        )
        db.add(new_assignment)
        assignment_id = None
        order.status = "Assigned"

    history = models.OrderStatusHistory(
        order_id=order.id,
        changed_by=current_user.id,
        status="Assigned",
        note=f"Order assigned or reassigned to courier {courier.id}"
    )

    db.add(history)
    db.commit()

    if assignment_id is None:
        db.refresh(new_assignment)
        assignment_id = new_assignment.id

    return {
        "message": "Order reassigned successfully!",
        "assignment_id": assignment_id,
        "order_id": order.id,
        "courier_id": courier.id,
        "courier_name": courier.name,
        "status": order.status
    }
