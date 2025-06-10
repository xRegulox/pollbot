import os
import logging
from app import app, db
import models

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def update_database_schema():
    """Update the database schema with the new columns"""
    logger.info("Updating database schema...")
    
    with app.app_context():
        # Create all tables including the new columns
        db.create_all()
        logger.info("Database schema updated!")

if __name__ == "__main__":
    update_database_schema()