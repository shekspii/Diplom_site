from flask import Flask
import click
from config import Config
from extensions import db, migrate, jwt
from models import *
from routes import admin_bp, auth_bp, questions_bp, surveys_bp
from flask_cors import CORS
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.json.ensure_ascii = False
    CORS(
        app,
        resources={
            r"/*": {
                "origins": [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173"
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"]
            }
        }
    )
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(surveys_bp)

    @app.cli.command("create-admin")
    @click.option("--email", default=None, help="Email администратора")
    @click.option("--password", default=None, help="Пароль администратора")
    def create_admin_command(email, password):
        admin_email = email or app.config.get("ADMIN_EMAIL")
        admin_password = password or app.config.get("ADMIN_PASSWORD")

        if not admin_email or not admin_password:
            raise click.ClickException(
                "Укажите --email и --password или задайте ADMIN_EMAIL/ADMIN_PASSWORD в .env"
            )

        user = User.query.filter_by(email=admin_email).first()
        if user:
            user.password_hash = generate_password_hash(admin_password)
            user.role = "admin"
            action = "updated"
        else:
            user = User(
                email=admin_email,
                password_hash=generate_password_hash(admin_password),
                role="admin"
            )
            db.session.add(user)
            action = "created"

        db.session.commit()
        click.echo(f"Admin {action}: {admin_email}")

    @app.errorhandler(OperationalError)
    def handle_database_error(error):
        app.logger.exception("Database error")
        return {
            "error": "Не удалось подключиться к базе данных. Проверьте DATABASE_URL и запущен ли PostgreSQL."
        }, 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if isinstance(error, HTTPException):
            return error

        app.logger.exception("Unexpected error")
        return {"error": str(error) or "Внутренняя ошибка сервера"}, 500

    @jwt.unauthorized_loader
    def handle_missing_token(error):
        return {"error": "Требуется авторизация. Войдите в аккаунт."}, 401

    @jwt.invalid_token_loader
    def handle_invalid_token(error):
        return {"error": "Токен недействителен. Войдите заново."}, 401

    @jwt.expired_token_loader
    def handle_expired_token(jwt_header, jwt_payload):
        return {"error": "Сессия истекла. Войдите заново."}, 401

    return app


app = create_app()
