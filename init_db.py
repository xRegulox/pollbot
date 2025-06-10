import os
import logging
from app import app, db
import models

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database tables and create default admin if needed"""
    logger.info("Initializing database...")
    
    with app.app_context():
        # Create all tables
        db.create_all()
        logger.info("Database tables created.")
        
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
    
    logger.info("Database initialization complete!")

if __name__ == "__main__":
    init_database()