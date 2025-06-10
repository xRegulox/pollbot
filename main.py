import logging
import threading
import os
from flask import Flask
from app import app, db
import routes
from bot import bot, run_bot
import models

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
        
        # Check if admin account exists, if not create default admin
        admin = models.User.query.filter_by(username='admin').first()
        if not admin:
            from werkzeug.security import generate_password_hash
            admin = models.User(
                username='admin',
                email='admin@regulo-pollbot.local',
                password_hash=generate_password_hash('admin'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            logger.info("Created default admin account (username: admin, password: admin)")
            logger.info("Please change the default password after first login!")
    
    # Start Discord bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask web server
    app.run(host='0.0.0.0', port=5000, debug=False)
