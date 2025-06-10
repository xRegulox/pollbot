import datetime
import json
import io
import matplotlib.pyplot as plt
from app import db
from models import Poll, Vote, Server, Channel

def create_poll(server_id, channel_id, question, options, **kwargs):
    """
    Create a new poll with the given options
    
    Parameters:
    - server_id: Discord server ID
    - channel_id: Discord channel ID
    - question: The poll question
    - options: List of poll options
    - kwargs: Additional poll settings (description, expires_at, scheduled_for, etc.)
    
    Returns:
    - The created Poll object
    """
    poll = Poll(
        server_id=server_id,
        channel_id=channel_id,
        question=question,
        options=json.dumps(options),
        status='draft',
        **kwargs
    )
    
    db.session.add(poll)
    db.session.commit()
    
    return poll

def get_poll_results(poll_id):
    """
    Get the results for a poll
    
    Parameters:
    - poll_id: ID of the poll
    
    Returns:
    - Dictionary with options as keys and vote counts as values
    - Total number of votes
    - List of votes with user details if not anonymous
    """
    poll = Poll.query.get(poll_id)
    if not poll:
        return None, 0, []
    
    options = poll.get_options()
    results = {option: 0 for option in options}
    
    votes = Vote.query.filter_by(poll_id=poll_id).all()
    
    # Count votes for each option
    for vote in votes:
        if vote.option in results:
            results[vote.option] += vote.weight
    
    total_votes = sum(results.values())
    
    return results, total_votes, votes if not poll.is_anonymous else []

def generate_chart(poll_id, chart_type='bar'):
    """
    Generate a chart for poll results
    
    Parameters:
    - poll_id: ID of the poll
    - chart_type: Type of chart ('bar' or 'pie')
    
    Returns:
    - BytesIO object containing the chart image
    """
    poll = Poll.query.get(poll_id)
    if not poll:
        return None
    
    options = poll.get_options()
    results, total_votes, _ = get_poll_results(poll_id)
    
    # Create figure
    plt.figure(figsize=(10, 6))
    
    if chart_type == 'pie':
        # Create pie chart
        plt.pie(
            [results.get(option, 0) for option in options],
            labels=[f"{option} ({results.get(option, 0)})" for option in options],
            autopct='%1.1f%%',
            startangle=90
        )
        plt.axis('equal')
    else:
        # Create bar chart
        plt.bar(options, [results.get(option, 0) for option in options], color='cornflowerblue')
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Votes')
    
    plt.title(f"Results: {poll.question}")
    plt.tight_layout()
    
    # Save chart to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    return buf
