from flask import Flask, render_template, redirect, url_for, session
from flask_cors import CORS
from config import Config
from db_models import init_db
from auth_routes import auth_bp
from profile_routes import profile_bp
from presentation_routes import presentation_bp
import os
import logging

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Configure logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Initialize database
    init_db()
    
    # Create directories
    os.makedirs(os.path.join("static", "downloads"), exist_ok=True)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(presentation_bp)
    
    # Welcome and index routes
    @app.route('/welcome')
    def welcome():
        if 'user_id' in session:
            return redirect(url_for('profile.dashboard'))
        return render_template('welcome.html')
    
    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('profile.dashboard'))
        return redirect(url_for('welcome'))
    
    # Serve static files
    @app.route('/static/<path:path>')
    def serve_static(path):
        logger.debug(f"Serving static file: {path}")
        return app.send_static_file(path)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)