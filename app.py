from flask import Flask
from config import Config
from extensions import db, migrate, jwt
from models import *
from routes import auth_bp, questions_bp, surveys_bp
from dotenv import load_dotenv
load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["JWT_SECRET_KEY"] = "super-secret-key"

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(surveys_bp)

    return app


app = create_app()
