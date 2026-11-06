
from sqlalchemy.orm import Session
from backend import models, schemas
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


# Find a user by email
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(
        models.User.email == email
    ).first()


# Create a new user
def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = password_hash.hash(user.password)

    new_user = models.User(
        name=user.name,
        email=user.email,
        phone=user.phone,
        password_hash=hashed_password,
        role=user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# Verify a password
def verify_password(plain_password: str, hashed_password: str):
    return password_hash.verify(plain_password, hashed_password)
