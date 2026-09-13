import os
from flask import Flask, jsonify, request
from config import Config
from .extensions import db, migrate, jwt, csrf, limiter, cors
from .routes.web import web_bp
from .routes.auth import auth_bp
from .routes.api import api_bp
from .routes.admin import admin_bp
from .routes.operator import operator_bp
from .routes.chatbot import chatbot_bp
from .models import *

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)
    os.makedirs(app.config['UPLOAD_DIR'], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    cors.init_app(app, resources={r'/api/*': {'origins': app.config['CORS_ORIGINS']}}, supports_credentials=True)

    csrf.exempt(auth_bp)
    csrf.exempt(api_bp)
    csrf.exempt(admin_bp)
    csrf.exempt(operator_bp)
    csrf.exempt(chatbot_bp)

    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(operator_bp, url_prefix='/api/operator')
    app.register_blueprint(chatbot_bp, url_prefix='/api/chatbot')

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(success=False, message='File too large', error_code='FILE_TOO_LARGE'), 413

    @app.errorhandler(404)
    def not_found(_):
        return jsonify(success=False, message='Resource not found', error_code='NOT_FOUND'), 404 if request.path.startswith('/api/') else ('Not found', 404)

    @app.errorhandler(Exception)
    def unhandled(exc):
        app.logger.exception('Unhandled application error')
        if request.path.startswith('/api/'):
            return jsonify(success=False, message='Internal server error', error_code='INTERNAL_ERROR'), 500
        return 'Internal server error', 500

    return app
