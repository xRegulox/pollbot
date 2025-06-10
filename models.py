import json
import datetime
from app import db
from flask_login import UserMixin
from sqlalchemy.sql import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=func.now())

class Server(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)  # Discord server ID
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(256), nullable=True)
    default_channel_id = db.Column(db.BigInteger, nullable=True)
    joined_at = db.Column(db.DateTime, default=func.now())
    
    # Relationships
    roles = db.relationship('Role', backref='server', lazy=True)
    channels = db.relationship('Channel', backref='server', lazy=True)
    polls = db.relationship('Poll', backref='server', lazy=True)

class Channel(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)  # Discord channel ID
    server_id = db.Column(db.BigInteger, db.ForeignKey('server.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # text, voice, etc.

class Role(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)  # Discord role ID
    server_id = db.Column(db.BigInteger, db.ForeignKey('server.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.Integer, nullable=True)
    position = db.Column(db.Integer, nullable=False)
    vote_weight = db.Column(db.Integer, default=1)  # Weight for votes from users with this role

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.BigInteger, db.ForeignKey('server.id'), nullable=False)
    channel_id = db.Column(db.BigInteger, db.ForeignKey('channel.id'), nullable=False)
    message_id = db.Column(db.BigInteger, nullable=True)  # Discord message ID once posted
    
    question = db.Column(db.String(1000), nullable=False)
    description = db.Column(db.Text, nullable=True)
    options = db.Column(db.Text, nullable=False)  # JSON string of options
    
    created_at = db.Column(db.DateTime, default=func.now())
    scheduled_for = db.Column(db.DateTime, nullable=True)  # If scheduled for future
    expires_at = db.Column(db.DateTime, nullable=True)  # When poll closes
    
    is_anonymous = db.Column(db.Boolean, default=False)
    allow_multiple = db.Column(db.Boolean, default=False)
    max_votes = db.Column(db.Integer, default=0)  # 0 = unlimited, >0 = max votes per user
    allow_vote_change = db.Column(db.Boolean, default=True)  # Allow users to change their votes
    show_live_results = db.Column(db.Boolean, default=True)
    
    status = db.Column(db.String(20), default="draft")  # draft, active, closed, cancelled
    
    # Relationships
    votes = db.relationship('Vote', backref='poll', lazy=True)
    
    def get_options(self):
        return json.loads(self.options)
    
    def set_options(self, options_list):
        self.options = json.dumps(options_list)
    
    def get_results(self):
        results = {option: 0 for option in self.get_options()}
        for vote in self.votes:
            if vote.option in results:
                results[vote.option] += vote.weight
        return results
    
    def is_active(self):
        now = datetime.datetime.now()
        return (
            self.status == "active" and 
            (self.expires_at is None or self.expires_at > now)
        )

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'), nullable=False)
    user_id = db.Column(db.BigInteger, nullable=False)  # Discord user ID
    username = db.Column(db.String(100), nullable=True)  # Discord username
    option = db.Column(db.String(1000), nullable=False)
    weight = db.Column(db.Integer, default=1)  # Vote weight based on user's role
    voted_at = db.Column(db.DateTime, default=func.now())

class BotConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), nullable=True)
    dashboard_password = db.Column(db.String(256), nullable=True)
    theme = db.Column(db.String(20), default="dark")
    setup_completed = db.Column(db.Boolean, default=False)
    backup_frequency = db.Column(db.String(20), default="daily")  # daily, weekly, monthly
    last_backup = db.Column(db.DateTime, nullable=True)
