from flask import Blueprint, request
from extensions import db
from models import User
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {"error": "Email и пароль обязательны"}, 400

    if User.query.filter_by(email=email).first():
        return {"error": "Пользователь с таким email уже существует"}, 400

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        role="user"
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"error": "Не удалось создать пользователя"}, 400

    return {
        "message": "Пользователь создан",
        "user": {
            "email": user.email,
            "role": user.role
        }
    }, 201

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {"error": "Email и пароль обязательны"}, 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return {"error": "Неверный email или пароль"}, 401

    access_token = create_access_token(identity=str(user.id))

    return {
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        }
    }

@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()

    user = User.query.get(user_id)

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role
    }
