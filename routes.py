import os
import datetime
import logging
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import json
import io

from app import app, db
from models import User, Server, Channel, Role, Poll, Vote, BotConfig
from auth import requires_admin
from polls import create_poll, get_poll_results, generate_chart
from bot import post_poll, close_poll, update_poll_embed, handle_poll_closing
from scheduler import schedule_backup
from charts import generate_results_chart

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    with app.app_context():
        config = BotConfig.query.first()
        if not config or not config.setup_completed:
            return redirect(url_for('setup'))
        
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        return redirect(url_for('login'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    with app.app_context():
        config = BotConfig.query.first()
        
        # If setup is already completed, redirect to login
        if config and config.setup_completed:
            flash('Setup has already been completed.', 'info')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            token = request.form.get('token')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if not token or not password:
                flash('Please fill in all required fields.', 'danger')
                return render_template('setup.html')
            
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('setup.html')
            
            # Create or update config
            if not config:
                config = BotConfig(
                    token=token,
                    dashboard_password=generate_password_hash(password),
                    setup_completed=True
                )
                db.session.add(config)
            else:
                config.token = token
                config.dashboard_password = generate_password_hash(password)
                config.setup_completed = True
                
            # Make sure to commit the changes to database
            db.session.commit()
            
            # Create admin user
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@regulo-pollbot.local',
                    password_hash=generate_password_hash(password),
                    is_admin=True
                )
                db.session.add(admin)
            else:
                admin.password_hash = generate_password_hash(password)
            
            db.session.commit()
            flash('Setup completed successfully. Please restart the application for the bot to connect.', 'success')
            return redirect(url_for('login'))
        
        return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    with app.app_context():
        # Get statistics for dashboard
        total_polls = Poll.query.count()
        active_polls = Poll.query.filter_by(status='active').count()
        total_votes = Vote.query.count()
        total_servers = Server.query.count()
        
        # Get recent polls
        recent_polls = Poll.query.order_by(Poll.created_at.desc()).limit(5).all()
        
        # Get poll activity data for chart
        polls_by_day = {}
        votes_by_day = {}
        
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=7)
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            polls_by_day[date_str] = 0
            votes_by_day[date_str] = 0
            current_date += datetime.timedelta(days=1)
        
        # Count polls created per day
        polls = Poll.query.filter(Poll.created_at >= start_date).all()
        for poll in polls:
            date_str = poll.created_at.strftime('%Y-%m-%d')
            if date_str in polls_by_day:
                polls_by_day[date_str] += 1
        
        # Count votes cast per day
        votes = Vote.query.filter(Vote.voted_at >= start_date).all()
        for vote in votes:
            date_str = vote.voted_at.strftime('%Y-%m-%d')
            if date_str in votes_by_day:
                votes_by_day[date_str] += 1
        
        return render_template(
            'dashboard.html',
            total_polls=total_polls,
            active_polls=active_polls,
            total_votes=total_votes,
            total_servers=total_servers,
            recent_polls=recent_polls,
            polls_by_day=json.dumps(list(polls_by_day.items())),
            votes_by_day=json.dumps(list(votes_by_day.items()))
        )

@app.route('/create_poll', methods=['GET', 'POST'])
@login_required
def create_poll_route():
    with app.app_context():
        servers = Server.query.all()
        
        if not servers:
            flash('No Discord servers found. Make sure the bot is added to at least one server.', 'warning')
        
        if request.method == 'POST':
            server_id = request.form.get('server_id')
            channel_id = request.form.get('channel_id')
            question = request.form.get('question')
            description = request.form.get('description')
            
            # Get options from form
            options = []
            for i in range(1, 11):  # Max 10 options
                option = request.form.get(f'option_{i}')
                if option:
                    options.append(option)
            
            # Use default server/channel if not specified
            if not server_id:
                # Get the first available server with a default channel
                default_server = Server.query.filter(Server.default_channel_id.isnot(None)).first()
                if default_server:
                    server_id = str(default_server.id)
                    if not channel_id:
                        channel_id = str(default_server.default_channel_id)
            elif not channel_id:
                # If server is specified but channel is not, use server's default channel
                server = Server.query.get(int(server_id))
                if server and server.default_channel_id:
                    channel_id = str(server.default_channel_id)
            
            if not server_id or not channel_id or not question or len(options) < 1:
                flash('Please fill in all required fields and provide at least one option. Make sure you have configured a default server and channel in Bot Config.', 'danger')
                return redirect(url_for('create_poll_route'))
            
            # Parse expiration time
            expiration_type = request.form.get('expiration_type')
            expires_at = None
            
            if expiration_type == 'duration':
                duration_value = request.form.get('duration_value')
                duration_unit = request.form.get('duration_unit')
                
                if duration_value and duration_unit:
                    duration_value = int(duration_value)
                    now = datetime.datetime.now()
                    
                    if duration_unit == 'minutes':
                        expires_at = now + datetime.timedelta(minutes=duration_value)
                    elif duration_unit == 'hours':
                        expires_at = now + datetime.timedelta(hours=duration_value)
                    elif duration_unit == 'days':
                        expires_at = now + datetime.timedelta(days=duration_value)
                    elif duration_unit == 'weeks':
                        expires_at = now + datetime.timedelta(weeks=duration_value)
            
            elif expiration_type == 'datetime':
                expiration_date = request.form.get('expiration_date')
                expiration_time = request.form.get('expiration_time')
                
                if expiration_date and expiration_time:
                    try:
                        expires_at = datetime.datetime.strptime(
                            f'{expiration_date} {expiration_time}',
                            '%Y-%m-%d %H:%M'
                        )
                    except:
                        flash('Invalid date or time format.', 'danger')
                        return redirect(url_for('create_poll_route'))
            
            # Parse scheduling
            schedule_type = request.form.get('schedule_type')
            scheduled_for = None
            
            if schedule_type == 'scheduled':
                schedule_date = request.form.get('schedule_date')
                schedule_time = request.form.get('schedule_time')
                
                if schedule_date and schedule_time:
                    try:
                        scheduled_for = datetime.datetime.strptime(
                            f'{schedule_date} {schedule_time}',
                            '%Y-%m-%d %H:%M'
                        )
                    except:
                        flash('Invalid schedule date or time format.', 'danger')
                        return redirect(url_for('create_poll_route'))
            
            # Other poll settings
            is_anonymous = 'is_anonymous' in request.form
            allow_multiple = 'allow_multiple' in request.form
            allow_vote_change = 'allow_vote_change' in request.form
            show_live_results = 'show_live_results' in request.form
            
            # Get max votes (only applies when allow_multiple is enabled)
            max_votes = 0  # Default to unlimited
            if allow_multiple and 'max_votes' in request.form:
                try:
                    max_votes = int(request.form.get('max_votes', 0))
                    if max_votes < 0:
                        max_votes = 0  # Ensure non-negative value
                except ValueError:
                    max_votes = 0  # Default to unlimited if invalid input
            
            try:
                # Check if server exists in database, if not create it
                server = Server.query.get(int(server_id))
                if not server:
                    server = Server(
                        id=int(server_id),
                        name=f"Server-{server_id}",  # Placeholder name
                    )
                    db.session.add(server)
                
                # Check if channel exists in database, if not create it
                channel = Channel.query.get(int(channel_id))
                if not channel:
                    # Create channel record if it doesn't exist
                    channel = Channel(
                        id=int(channel_id),
                        server_id=int(server_id),
                        name=f"Channel-{channel_id}",  # Placeholder name
                        type='text'
                    )
                    db.session.add(channel)
                
                # Create poll
                poll = Poll(
                    server_id=int(server_id),
                    channel_id=int(channel_id),
                    question=question,
                    description=description,
                    options=json.dumps(options),
                    expires_at=expires_at,
                    scheduled_for=scheduled_for,
                    is_anonymous=is_anonymous,
                    allow_multiple=allow_multiple,
                    max_votes=max_votes,
                    allow_vote_change=allow_vote_change,
                    show_live_results=show_live_results,
                    status='active'
                )
                
                db.session.add(poll)
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating poll: {str(e)}")
                flash('Error creating poll. Please try again.', 'danger')
                return redirect(url_for('create_poll_route'))
            
            # If not scheduled, the poll will be posted by the bot's check_polls task
            # No need to post immediately here as the task runs every minute
            
            flash('Poll created successfully!', 'success')
            return redirect(url_for('manage_polls'))
        
        return render_template('create_poll.html', servers=servers)

@app.route('/get_channels/<int:server_id>')
@login_required
def get_channels(server_id):
    with app.app_context():
        channels = Channel.query.filter_by(server_id=server_id, type='text').all()
        return jsonify([{'id': channel.id, 'name': channel.name} for channel in channels])

@app.route('/manage_polls')
@login_required
def manage_polls():
    with app.app_context():
        # Get polls with sorting and filtering
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'desc')
        status_filter = request.args.get('status', 'all')
        
        query = Poll.query
        
        # Apply status filter
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)
        
        # Apply sorting
        if order == 'asc':
            query = query.order_by(getattr(Poll, sort_by).asc())
        else:
            query = query.order_by(getattr(Poll, sort_by).desc())
        
        polls = query.all()
        
        # Get server names for each poll
        for poll in polls:
            server = Server.query.get(poll.server_id)
            poll.server_name = server.name if server else 'Unknown Server'
            
            channel = Channel.query.get(poll.channel_id)
            poll.channel_name = channel.name if channel else 'Unknown Channel'
        
        return render_template(
            'manage_polls.html',
            polls=polls,
            sort_by=sort_by,
            order=order,
            status=status_filter
        )

@app.route('/poll/<int:poll_id>')
@login_required
def view_poll(poll_id):
    with app.app_context():
        poll = Poll.query.get_or_404(poll_id)
        
        server = Server.query.get(poll.server_id)
        poll.server_name = server.name if server else 'Unknown Server'
        
        channel = Channel.query.get(poll.channel_id)
        poll.channel_name = channel.name if channel else 'Unknown Channel'
        
        # Get poll options and results
        options = poll.get_options()
        results = poll.get_results()
        total_votes = sum(results.values())
        
        # Get votes with user information if not anonymous
        votes = []
        if not poll.is_anonymous:
            votes = Vote.query.filter_by(poll_id=poll.id).all()
        
        # Format results for chart
        chart_labels = json.dumps(options)
        chart_data = json.dumps([results.get(option, 0) for option in options])
        
        return render_template(
            'results.html',
            poll=poll,
            options=options,
            results=results,
            total_votes=total_votes,
            votes=votes,
            chart_labels=chart_labels,
            chart_data=chart_data
        )

@app.route('/poll/<int:poll_id>/close', methods=['POST'])
@login_required
def close_poll_route(poll_id):
    with app.app_context():
        poll = Poll.query.get_or_404(poll_id)
        
        if poll.status != 'active':
            flash('This poll is not active.', 'warning')
            return redirect(url_for('manage_polls'))
        
        # Mark poll for closing - background task will handle Discord message updates
        poll.status = 'closed'
        db.session.commit()
        
        # Import and use the async function properly
        from bot import bot
        import asyncio
        
        def close_poll_async():
            try:
                # Get the bot's event loop
                if bot.loop and not bot.loop.is_closed():
                    # Schedule the close on the bot's event loop
                    future = asyncio.run_coroutine_threadsafe(handle_poll_closing(poll_id), bot.loop)
                    return future.result(timeout=10)
                else:
                    return False
            except Exception as e:
                logger.error(f"Error in close_poll_async: {str(e)}")
                return False
        
        # Run the close operation
        success = close_poll_async()
        
        flash('Poll closed successfully!', 'success')
        return redirect(url_for('view_poll', poll_id=poll.id))

@app.route('/poll/<int:poll_id>/delete', methods=['POST'])
@login_required
def delete_poll(poll_id):
    with app.app_context():
        poll = Poll.query.get_or_404(poll_id)
        
        # Delete votes first (foreign key constraint)
        Vote.query.filter_by(poll_id=poll.id).delete()
        
        # Delete poll
        db.session.delete(poll)
        db.session.commit()
        
        flash('Poll deleted successfully!', 'success')
        return redirect(url_for('manage_polls'))

@app.route('/poll/<int:poll_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_poll(poll_id):
    with app.app_context():
        poll = Poll.query.get_or_404(poll_id)
        
        if request.method == 'POST':
            # Update poll details
            poll.question = request.form.get('question')
            poll.description = request.form.get('description')
            
            # Update options
            options = []
            for i in range(1, 11):  # Support up to 10 options
                option = request.form.get(f'option_{i}')
                if option and option.strip():
                    options.append(option.strip())
            
            if len(options) < 2:
                flash('Poll must have at least 2 options!', 'danger')
                return redirect(url_for('edit_poll', poll_id=poll_id))
            
            poll.set_options(options)
            
            # Update settings
            poll.is_anonymous = 'is_anonymous' in request.form
            poll.allow_multiple = 'allow_multiple' in request.form
            poll.show_live_results = 'show_live_results' in request.form
            
            # Mark poll for reposting (will update status immediately after posting)
            poll.status = 'draft'
            poll.message_id = None  # Clear old message ID
            
            db.session.commit()
            
            flash('Poll updated successfully! It will be posted to Discord shortly.', 'success')
            return redirect(url_for('manage_polls'))
        
        # GET request - show edit form
        servers = Server.query.all()
        return render_template('edit_poll.html', poll=poll, servers=servers)

@app.route('/poll/<int:poll_id>/resend', methods=['GET', 'POST'])
@login_required
def resend_poll_route(poll_id):
    with app.app_context():
        poll = Poll.query.get_or_404(poll_id)
        
        if request.method == 'POST':
            new_channel_id = request.form.get('channel_id')
            
            # Update poll channel if new one is provided
            if new_channel_id and int(new_channel_id) != poll.channel_id:
                poll.channel_id = int(new_channel_id)
            
            # Mark poll to be resent by setting it as draft - the background task will handle posting
            poll.status = 'draft'
            poll.message_id = None  # Clear old message ID so it gets a new one
            db.session.commit()
            
            flash('Poll marked for resending! It will be posted to Discord within a minute.', 'success')
            return redirect(url_for('manage_polls'))
        
        # GET request - show resend form
        server = Server.query.get(poll.server_id)
        channels = Channel.query.filter_by(server_id=poll.server_id, type='text').all()
        
        return render_template('resend_poll.html', poll=poll, server=server, channels=channels)

@app.route('/roles')
@login_required
@requires_admin
def manage_roles():
    with app.app_context():
        servers = Server.query.all()
        
        # Get server_id from query params or use first server
        server_id = request.args.get('server_id')
        if not server_id and servers:
            server_id = servers[0].id
        
        roles = []
        if server_id:
            roles = Role.query.filter_by(server_id=server_id).order_by(Role.position.desc()).all()
        
        return render_template('roles.html', servers=servers, roles=roles, current_server_id=server_id)

@app.route('/roles/update', methods=['POST'])
@login_required
@requires_admin
def update_role_weights():
    with app.app_context():
        server_id = request.form.get('server_id')
        
        if not server_id:
            flash('Server ID is required.', 'danger')
            return redirect(url_for('manage_roles'))
        
        # Update role weights
        for key, value in request.form.items():
            if key.startswith('weight_'):
                role_id = key.split('_')[1]
                weight = int(value)
                
                role = Role.query.get(role_id)
                if role and role.server_id == int(server_id):
                    role.vote_weight = weight
        
        db.session.commit()
        flash('Role weights updated successfully!', 'success')
        return redirect(url_for('manage_roles', server_id=server_id))

@app.route('/config', methods=['GET', 'POST'])
@login_required
@requires_admin
def bot_config():
    with app.app_context():
        config = BotConfig.query.first()
        servers = Server.query.all()
        
        if request.method == 'POST':
            token = request.form.get('token')
            theme = request.form.get('theme')
            backup_frequency = request.form.get('backup_frequency')
            
            if config:
                if token:
                    config.token = token
                config.theme = theme
                config.backup_frequency = backup_frequency
            else:
                config = BotConfig(
                    token=token,
                    theme=theme,
                    backup_frequency=backup_frequency,
                    setup_completed=True
                )
                db.session.add(config)
            
            db.session.commit()
            flash('Configuration updated successfully! Please restart the application for changes to take effect.', 'success')
            return redirect(url_for('bot_config'))
        
        # Get client ID from token for invite link
        client_id = None
        if config and config.token:
            try:
                import base64
                import json
                token_parts = config.token.split('.')
                if len(token_parts) > 0:
                    padded = token_parts[0] + '=' * (4 - len(token_parts[0]) % 4)
                    decoded = base64.b64decode(padded)
                    payload = json.loads(decoded)
                    client_id = payload.get('client_id', None)
            except:
                pass
                
        return render_template('bot_config.html', config=config, servers=servers, client_id=client_id)

@app.route('/server_config')
@login_required
@requires_admin
def server_config_page():
    with app.app_context():
        config = BotConfig.query.first()
        servers = Server.query.all()
        
        # Get client ID from token for invite link
        client_id = None
        if config and config.token:
            try:
                import base64
                import json
                token_parts = config.token.split('.')
                if len(token_parts) > 0:
                    try:
                        padded = token_parts[0] + '=' * (4 - len(token_parts[0]) % 4)
                        decoded = base64.b64decode(padded)
                        payload = json.loads(decoded)
                        client_id = payload.get('client_id', None)
                    except:
                        # If this fails, try to extract from first part directly
                        client_id = token_parts[0]
            except:
                pass
        
        return render_template('server_config.html', config=config, servers=servers, client_id=client_id)

@app.route('/server/<int:server_id>/settings', methods=['POST'])
@login_required
@requires_admin
def update_server_settings(server_id):
    with app.app_context():
        server = Server.query.get_or_404(server_id)
        
        # Update default channel
        default_channel_id = request.form.get('default_channel_id')
        if default_channel_id:
            server.default_channel_id = int(default_channel_id)
            db.session.commit()
            flash(f'Settings for server "{server.name}" updated successfully!', 'success')
        else:
            server.default_channel_id = None
            db.session.commit()
            flash(f'Default channel for server "{server.name}" cleared.', 'info')
            
        return redirect(url_for('server_config_page'))

@app.route('/update_bot_token', methods=['POST'])
@login_required
@requires_admin
def update_bot_token():
    with app.app_context():
        token = request.form.get('token')
        
        if not token:
            flash('Bot token is required.', 'danger')
            return redirect(url_for('server_config_page'))
            
        # Get or create config
        config = BotConfig.query.first()
        if not config:
            config = BotConfig(
                token=token,
                theme='dark',
                backup_frequency='daily',
                setup_completed=True
            )
            db.session.add(config)
        else:
            config.token = token
            
        # Very important to commit the changes!
        db.session.commit()
        
        flash('Bot token updated successfully!', 'success')
        return redirect(url_for('server_config_page'))

@app.route('/restart_bot', methods=['POST'])
@login_required
@requires_admin
def restart_bot():
    try:
        # Import bot module here to avoid circular imports
        from bot import run_bot
        import threading
        
        # Start bot in a new thread
        threading.Thread(target=run_bot, daemon=True).start()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    with app.app_context():
        if request.method == 'POST':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not current_password or not new_password or not confirm_password:
                flash('Please fill in all password fields.', 'danger')
                return redirect(url_for('settings'))
            
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('settings'))
            
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('settings'))
            
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            flash('Password updated successfully!', 'success')
            return redirect(url_for('settings'))
        
        return render_template('settings.html')

@app.route('/backup', methods=['POST'])
@login_required
@requires_admin
def backup_database():
    # Create database backup
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"regulo_pollbot_backup_{timestamp}.db"
    
    # Path to current database
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    
    # Create a copy of the database
    import shutil
    backup_path = os.path.join(os.getcwd(), backup_filename)
    shutil.copy2(db_path, backup_path)
    
    # Send the file to the user
    return send_file(
        backup_path,
        as_attachment=True,
        download_name=backup_filename,
        mimetype='application/octet-stream'
    )

@app.route('/export/poll/<int:poll_id>/csv')
@login_required
def export_poll_csv(poll_id):
    with app.app_context():
        poll = Poll.query.get_or_404(poll_id)
        
        # Generate CSV data
        options = poll.get_options()
        results = poll.get_results()
        
        csv_data = io.StringIO()
        csv_data.write("Option,Votes,Percentage\n")
        
        total_votes = sum(results.values())
        for option in options:
            votes = results.get(option, 0)
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            csv_data.write(f'"{option}",{votes},{percentage:.1f}%\n')
        
        # Create response
        csv_data.seek(0)
        return send_file(
            io.BytesIO(csv_data.getvalue().encode()),
            as_attachment=True,
            download_name=f"poll_{poll_id}_results.csv",
            mimetype='text/csv'
        )

@app.route('/export/poll/<int:poll_id>/chart')
@login_required
def export_poll_chart(poll_id):
    with app.app_context():
        poll = Poll.query.get_or_404(poll_id)
        
        # Generate chart image
        options = poll.get_options()
        results = poll.get_results()
        
        # Convert results to lists for plotting
        labels = options
        values = [results.get(option, 0) for option in options]
        
        # Generate chart image
        chart_img = generate_results_chart(poll.question, labels, values)
        
        # Return the image
        return send_file(
            chart_img,
            as_attachment=True,
            download_name=f"poll_{poll_id}_chart.png",
            mimetype='image/png'
        )

# Register the routes with the app
with app.app_context():
    pass
