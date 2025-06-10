import os
import datetime
import shutil
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app import app, db
from models import BotConfig, Poll

# Configure logging
logger = logging.getLogger(__name__)

# Create scheduler
scheduler = BackgroundScheduler()

def schedule_backup():
    """
    Schedule database backups based on configuration
    """
    with app.app_context():
        config = BotConfig.query.first()
        if not config:
            return
        
        # Remove existing backup jobs
        for job in scheduler.get_jobs():
            if job.id == 'database_backup':
                scheduler.remove_job('database_backup')
        
        # Schedule new backup job based on frequency
        if config.backup_frequency == 'daily':
            scheduler.add_job(
                func=perform_backup,
                trigger='cron',
                hour=0,
                minute=0,
                id='database_backup'
            )
        elif config.backup_frequency == 'weekly':
            scheduler.add_job(
                func=perform_backup,
                trigger='cron',
                day_of_week=0,  # Monday
                hour=0,
                minute=0,
                id='database_backup'
            )
        elif config.backup_frequency == 'monthly':
            scheduler.add_job(
                func=perform_backup,
                trigger='cron',
                day=1,
                hour=0,
                minute=0,
                id='database_backup'
            )

def perform_backup():
    """
    Create a backup of the database
    """
    with app.app_context():
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"regulo_pollbot_backup_{timestamp}.db"
            
            # Path to current database
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(os.getcwd(), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create a copy of the database
            backup_path = os.path.join(backup_dir, backup_filename)
            shutil.copy2(db_path, backup_path)
            
            # Update last backup timestamp
            config = BotConfig.query.first()
            if config:
                config.last_backup = datetime.datetime.now()
                db.session.commit()
            
            logger.info(f"Database backup created: {backup_filename}")
            
            # Keep only the last 5 backups
            backup_files = sorted([
                os.path.join(backup_dir, f) for f in os.listdir(backup_dir)
                if f.startswith('regulo_pollbot_backup_') and f.endswith('.db')
            ])
            
            while len(backup_files) > 5:
                os.remove(backup_files.pop(0))
                
        except Exception as e:
            logger.error(f"Failed to create database backup: {str(e)}")

# Start scheduler
scheduler.start()
