import os
import logging
from app import app, db
import models
from werkzeug.security import generate_password_hash

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def reset_database():
    """Reset the database and create new tables with the updated schema"""
    logger.info("Resetting database...")
    
    with app.app_context():
        # Drop all tables
        db.drop_all()
        logger.info("All tables dropped.")
        
        # Create all tables with new schema
        db.create_all()
        logger.info("Database tables created with new schema.")
        
        # Create default admin account
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
    
    logger.info("Database reset complete!")

if __name__ == "__main__":
    reset_database()