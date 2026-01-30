from flask import Flask
from app.api.auth.routes import bp as auth_bp

def register_blueprints(app: Flask):
    app.register_blueprint(auth_bp)
