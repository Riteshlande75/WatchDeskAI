import os
import logging
from flask import Flask, render_template, request, jsonify
from app.models import init_db

def create_app():
    """
    Application Factory for WatchDesk Flask App.
    Initializes Flask application, registers blueprints, creates database schema,
    and configures global error handling.
    """
    app_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(app_dir, 'templates')
    static_dir = os.path.join(app_dir, 'static')

    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)
    app.secret_key = 'monitorexam_secret_key'

    # Initialize Database Schema
    init_db()

    # Configure Logging
    logging.basicConfig(level=logging.INFO)

    # Register Blueprints from app.routes
    from app.routes.auth import auth_bp
    from app.routes.exam import exam_bp
    from app.routes.events import events_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(events_bp)

    # ── Global HTTP Error Handlers ─────────────────────────────────────────────
    def wants_json_response():
        return (
            request.path.startswith('/api/') or 
            '/api/' in request.path or 
            request.is_json or 
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        )

    @app.errorhandler(400)
    def bad_request_error(e):
        if wants_json_response():
            return jsonify({'success': False, 'message': 'Bad Request: Invalid payload or parameters.'}), 400
        return render_template('errors/404.html'), 400

    @app.errorhandler(403)
    def forbidden_error(e):
        if wants_json_response():
            return jsonify({'success': False, 'message': 'Forbidden: Access Restricted.'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(e):
        if wants_json_response():
            return jsonify({'success': False, 'message': 'Resource not found.'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"Internal Server Error on {request.path}: {e}")
        if wants_json_response():
            return jsonify({'success': False, 'message': 'Internal Server Error encountered.'}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        app.logger.error(f"Unhandled Exception on {request.path}: {e}", exc_info=True)
        if wants_json_response():
            return jsonify({'success': False, 'message': 'An unexpected error occurred.'}), 500
        return render_template('errors/500.html'), 500

    return app

