import os
import discord
import asyncio
import logging
import datetime
import json
from discord.ext import commands, tasks
import matplotlib.pyplot as plt
import io
from app import app, db
from models import Server, Channel, Role, Poll, Vote, BotConfig

# Configure logging
logger = logging.getLogger(__name__)

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store emojis for poll options
OPTION_EMOJIS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

@bot.event
async def on_ready():
    logger.info(f'Bot logged in as {bot.user.name} ({bot.user.id})')
    
    # Start background tasks
    check_polls.start()
    sync_servers.start()
    
    # Set custom status
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="polls via dashboard"
    ))

@bot.event
async def on_guild_join(guild):
    with app.app_context():
        # Add server to database
        server = Server.query.get(guild.id)
        if not server:
            server = Server(
                id=guild.id,
                name=guild.name,
                icon=str(guild.icon.url) if guild.icon else None
            )
            db.session.add(server)
        
        # Add channels to database
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                db_channel = Channel.query.get(channel.id)
                if not db_channel:
                    db_channel = Channel(
                        id=channel.id,
                        server_id=guild.id,
                        name=channel.name,
                        type='text'
                    )
                    db.session.add(db_channel)
        
        # Add roles to database
        for role in guild.roles:
            db_role = Role.query.get(role.id)
            if not db_role:
                db_role = Role(
                    id=role.id,
                    server_id=guild.id,
                    name=role.name,
                    color=role.color.value if role.color else 0,
                    position=role.position,
                    vote_weight=1  # Default weight
                )
                db.session.add(db_role)
        
        db.session.commit()
        logger.info(f'Added server {guild.name} to database')

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    
    with app.app_context():
        # Check if reaction is for a poll
        poll = Poll.query.filter_by(message_id=payload.message_id).first()
        if not poll or not poll.is_active():
            return
        
        # Get the guild and member
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        # Get emoji and check if it's a valid poll option
        emoji = str(payload.emoji)
        
        options = poll.get_options()
        if emoji not in OPTION_EMOJIS[:len(options)]:
            # Remove invalid reaction
            channel = bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, member)
            return
        
        # Get option index from emoji
        option_index = OPTION_EMOJIS.index(emoji)
        if option_index >= len(options):
            return
        
        selected_option = options[option_index]
        
        # Get user's highest role for vote weight
        highest_role = None
        highest_weight = 1
        
        for role in member.roles:
            db_role = Role.query.get(role.id)
            if db_role and db_role.vote_weight > highest_weight:
                highest_weight = db_role.vote_weight
                highest_role = db_role
        
        # Check if user already voted
        # Get all user's votes for this poll
        user_votes = Vote.query.filter_by(
            poll_id=poll.id,
            user_id=payload.user_id
        ).all()
        
        # Check if user already voted for this specific option
        existing_vote = next((vote for vote in user_votes if vote.option == selected_option), None)
        
        if existing_vote:
            # User already voted for this option, do nothing
            return
            
        # Handle vote limits and changes
        if not poll.allow_multiple:
            # Single vote mode: replace existing vote if allowed
            if user_votes:
                if not poll.allow_vote_change:
                    # Remove the reaction if vote changing is not allowed
                    channel = bot.get_channel(payload.channel_id)
                    message = await channel.fetch_message(payload.message_id)
                    await message.remove_reaction(payload.emoji, member)
                    return
                
                # Remove old reaction
                channel = bot.get_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                
                # Find and remove old reaction
                for reaction in message.reactions:
                    if str(reaction.emoji) in OPTION_EMOJIS:
                        option_idx = OPTION_EMOJIS.index(str(reaction.emoji))
                        if option_idx < len(options) and options[option_idx] == user_votes[0].option:
                            try:
                                await reaction.remove(member)
                            except:
                                pass
                
                # Update vote
                user_votes[0].option = selected_option
                user_votes[0].voted_at = datetime.datetime.now()
                db.session.commit()
            else:
                # Create new vote
                new_vote = Vote(
                    poll_id=poll.id,
                    user_id=payload.user_id,
                    username=member.display_name,
                    option=selected_option,
                    weight=highest_weight
                )
                db.session.add(new_vote)
                db.session.commit()
        else:
            # Multiple votes mode
            
            # Check if max votes limit is reached
            if poll.max_votes > 0 and len(user_votes) >= poll.max_votes:
                # Remove the reaction if vote limit reached
                channel = bot.get_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                await message.remove_reaction(payload.emoji, member)
                
                # Send a DM to the user informing them of the vote limit
                try:
                    await member.send(f"You've reached the maximum number of votes ({poll.max_votes}) allowed for the poll: '{poll.question}'")
                except:
                    # Failed to send DM, user might have DMs disabled
                    pass
                    
                return
            
            # Add new vote for different option
            new_vote = Vote(
                poll_id=poll.id,
                user_id=payload.user_id,
                username=member.display_name,
                option=selected_option,
                weight=highest_weight
            )
            db.session.add(new_vote)
            db.session.commit()
        
        # Remove user reaction for anonymous polls to maintain privacy
        if poll.is_anonymous:
            channel = bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, member)
        
        # Update poll embed with live results if enabled
        if poll.show_live_results:
            await update_poll_embed(poll.id)

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return
    
    with app.app_context():
        # Check if reaction is for a poll
        poll = Poll.query.filter_by(message_id=payload.message_id).first()
        if not poll or not poll.is_active():
            return
        
        # Don't remove votes for anonymous polls when reactions are auto-removed
        if poll.is_anonymous:
            return
        
        # Get emoji and check if it's a valid poll option
        emoji = str(payload.emoji)
        
        options = poll.get_options()
        if emoji not in OPTION_EMOJIS[:len(options)]:
            return
        
        # Get option index from emoji
        option_index = OPTION_EMOJIS.index(emoji)
        if option_index >= len(options):
            return
        
        selected_option = options[option_index]
        
        # Remove vote
        vote = Vote.query.filter_by(
            poll_id=poll.id,
            user_id=payload.user_id,
            option=selected_option
        ).first()
        
        if vote:
            db.session.delete(vote)
            db.session.commit()
            
            # Get guild and member for potential notification
            guild = bot.get_guild(payload.guild_id)
            if guild:
                member = guild.get_member(payload.user_id)
                if member:
                    # Notify user about vote removal
                    try:
                        # Only send notification for single-vote polls when vote changing is enabled
                        # This avoids spamming users who are managing multiple votes
                        if not poll.allow_multiple and poll.allow_vote_change:
                            await member.send(f"Your vote for '{selected_option}' in poll '{poll.question}' has been removed. You can vote for another option.")
                    except:
                        # Failed to send DM, user might have DMs disabled
                        pass
        
        # Update poll embed with live results if enabled
        if poll.show_live_results:
            await update_poll_embed(poll.id)

@tasks.loop(minutes=1)
async def check_polls():
    with app.app_context():
        now = datetime.datetime.now()
        
        # Post scheduled polls and unscheduled draft polls (like resent polls)
        draft_polls = Poll.query.filter(
            Poll.status == "draft"
        ).filter(
            (Poll.scheduled_for == None) | (Poll.scheduled_for <= now)
        ).all()
        
        for poll in draft_polls:
            await post_poll(poll.id)
        
        # Close expired polls
        expired_polls = Poll.query.filter(
            Poll.status == "active",
            Poll.expires_at <= now
        ).all()
        
        for poll in expired_polls:
            await close_poll(poll.id)

@tasks.loop(hours=1)
async def sync_servers():
    with app.app_context():
        # Update server info
        for guild in bot.guilds:
            server = Server.query.get(guild.id)
            if not server:
                server = Server(
                    id=guild.id,
                    name=guild.name,
                    icon=str(guild.icon.url) if guild.icon else None
                )
                db.session.add(server)
            else:
                server.name = guild.name
                server.icon = str(guild.icon.url) if guild.icon else None
            
            # Update channels
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    db_channel = Channel.query.get(channel.id)
                    if not db_channel:
                        db_channel = Channel(
                            id=channel.id,
                            server_id=guild.id,
                            name=channel.name,
                            type='text'
                        )
                        db.session.add(db_channel)
                    else:
                        db_channel.name = channel.name
            
            # Update roles
            for role in guild.roles:
                db_role = Role.query.get(role.id)
                if not db_role:
                    db_role = Role(
                        id=role.id,
                        server_id=guild.id,
                        name=role.name,
                        color=role.color.value if role.color else 0,
                        position=role.position,
                        vote_weight=1  # Default weight
                    )
                    db.session.add(db_role)
                else:
                    db_role.name = role.name
                    db_role.color = role.color.value if role.color else 0
                    db_role.position = role.position
        
        db.session.commit()

async def post_poll(poll_id):
    with app.app_context():
        poll = Poll.query.get(poll_id)
        if not poll or poll.status != "draft":
            return
        
        try:
            # Try to get the channel by ID
            channel = bot.get_channel(poll.channel_id)
            
            # If channel not found, try to get it through the guild
            if not channel:
                # Get the server object
                guild = bot.get_guild(poll.server_id)
                if guild:
                    # Try to get the channel again with the guild context
                    channel = guild.get_channel(poll.channel_id)
                    
                    # If still not found, try to use server's default channel
                    if not channel:
                        server = Server.query.get(poll.server_id)
                        if server and server.default_channel_id:
                            channel = guild.get_channel(server.default_channel_id)
                            # Update the poll to use this channel
                            if channel:
                                poll.channel_id = server.default_channel_id
                                db.session.commit()
                                logger.info(f"Updated poll {poll_id} to use server's default channel")
            
            # If still no channel, cancel the poll
            if not channel:
                poll.status = "cancelled"
                db.session.commit()
                logger.error(f"Failed to post poll {poll_id}: Channel not found. Check your server and channel configurations.")
                return
                
        except Exception as e:
            logger.error(f"Error finding channel: {str(e)}")
            poll.status = "cancelled"
            db.session.commit()
            logger.error(f"Failed to post poll {poll_id}: {str(e)}")
            return
        
        # Create poll embed
        embed = discord.Embed(
            title=poll.question,
            description=poll.description or "",
            color=discord.Color.blurple()
        )
        
        options = poll.get_options()
        for i, option in enumerate(options):
            embed.add_field(
                name=f"{OPTION_EMOJIS[i]} {option}",
                value="\u200b",  # Zero-width space
                inline=False
            )
        
        # Add footer with poll details
        footer_text = []
        if poll.allow_multiple:
            footer_text.append("Multiple votes allowed")
        else:
            footer_text.append("One vote per person")
        
        if poll.is_anonymous:
            footer_text.append("Votes are anonymous")
        
        if poll.expires_at:
            expires_at = poll.expires_at.strftime("%Y-%m-%d %H:%M")
            footer_text.append(f"Closes: {expires_at}")
        
        embed.set_footer(text=" • ".join(footer_text))
        
        # Send poll message
        try:
            message = await channel.send(embed=embed)
            
            # Add reaction options
            for i in range(len(options)):
                await message.add_reaction(OPTION_EMOJIS[i])
            
            # Update poll status
            poll.message_id = message.id
            poll.status = "active"
            db.session.commit()
            
            logger.info(f"Posted poll {poll_id} to channel {channel.name}")
        except Exception as e:
            poll.status = "cancelled"
            db.session.commit()
            logger.error(f"Failed to post poll {poll_id}: {str(e)}")

async def update_poll_embed(poll_id):
    with app.app_context():
        poll = Poll.query.get(poll_id)
        if not poll or poll.status != "active" or not poll.message_id:
            return
        
        channel = bot.get_channel(poll.channel_id)
        if not channel:
            return
        
        try:
            message = await channel.fetch_message(poll.message_id)
            
            # Create updated embed
            embed = discord.Embed(
                title=poll.question,
                description=poll.description or "",
                color=discord.Color.blurple()
            )
            
            options = poll.get_options()
            results = poll.get_results()
            total_votes = sum(results.values())
            
            for i, option in enumerate(options):
                votes = results.get(option, 0)
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                
                bar = ""
                if total_votes > 0:
                    filled = int(percentage / 10)
                    bar = "█" * filled + "░" * (10 - filled)
                
                field_value = f"{bar} {votes} votes ({percentage:.1f}%)"
                embed.add_field(
                    name=f"{OPTION_EMOJIS[i]} {option}",
                    value=field_value,
                    inline=False
                )
            
            # Add footer with poll details
            footer_text = []
            if poll.allow_multiple:
                footer_text.append("Multiple votes allowed")
            else:
                footer_text.append("One vote per person")
            
            if poll.is_anonymous:
                footer_text.append("Votes are anonymous")
            
            if poll.expires_at:
                expires_at = poll.expires_at.strftime("%Y-%m-%d %H:%M")
                footer_text.append(f"Closes: {expires_at}")
            
            embed.set_footer(text=" • ".join(footer_text))
            
            # Update the message
            await message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Failed to update poll {poll_id} embed: {str(e)}")

async def handle_poll_closing(poll_id):
    """Handle the Discord message updates when a poll is closed"""
    with app.app_context():
        poll = Poll.query.get(poll_id)
        if not poll or poll.status != "closed":
            return
        
        channel = bot.get_channel(poll.channel_id)
        if not channel:
            return
        
        options = poll.get_options()
        results = poll.get_results()
        total_votes = sum(results.values())
        
        # Update original poll message to show it's closed with final results
        try:
            message = await channel.fetch_message(poll.message_id)
            
            # Create a new embed showing final results on the original message
            closed_embed = discord.Embed(
                title=f"🔒 POLL CLOSED: {poll.question}",
                description="Final Results:",
                color=discord.Color.red()
            )
            
            # Find the winner (option with most votes)
            if total_votes > 0:
                winner = max(results, key=results.get)
                winner_votes = results[winner]
                winner_percentage = (winner_votes / total_votes * 100)
                
                closed_embed.add_field(
                    name="🏆 Winner",
                    value=f"**{winner}** with {winner_votes} votes ({winner_percentage:.1f}%)",
                    inline=False
                )
            
            # Add all results with visual bars
            for option in options:
                votes = results.get(option, 0)
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                
                # Create visual progress bar
                bar_length = 15
                filled = int((percentage / 100) * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                # Add trophy emoji for winner
                trophy = "🏆 " if votes == max(results.values()) and total_votes > 0 else ""
                
                closed_embed.add_field(
                    name=f"{trophy}{option}",
                    value=f"{bar} {votes} votes ({percentage:.1f}%)",
                    inline=False
                )
            
            closed_embed.set_footer(text=f"Total votes: {total_votes} • Poll ended")
            
            await message.edit(embed=closed_embed)
            await message.clear_reactions()
            
            logger.info(f"Updated original poll message {poll.message_id} with final results")
            
        except Exception as e:
            logger.error(f"Failed to update original poll message: {str(e)}")

async def close_poll(poll_id):
    with app.app_context():
        poll = Poll.query.get(poll_id)
        if not poll or poll.status != "active":
            return
        
        channel = bot.get_channel(poll.channel_id)
        if not channel:
            poll.status = "closed"
            db.session.commit()
            return
        
        # Update poll status
        poll.status = "closed"
        db.session.commit()
        
        # Create results embed
        embed = discord.Embed(
            title=f"Poll Closed: {poll.question}",
            description="Here are the final results:",
            color=discord.Color.gold()
        )
        
        options = poll.get_options()
        results = poll.get_results()
        total_votes = sum(results.values())
        
        for option in options:
            votes = results.get(option, 0)
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            embed.add_field(
                name=option,
                value=f"{votes} votes ({percentage:.1f}%)",
                inline=False
            )
        
        embed.set_footer(text=f"Total votes: {total_votes}")
        
        # Generate results chart
        plt.figure(figsize=(10, 6))
        plt.bar(options, [results.get(option, 0) for option in options], color='cornflowerblue')
        plt.xlabel('Options')
        plt.ylabel('Votes')
        plt.title('Poll Results')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save chart to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Create Discord file from buffer
        chart_file = discord.File(buf, filename="poll_results.png")
        
        # Send results message with chart
        try:
            await channel.send(embed=embed, file=chart_file)
            
            # Update original poll message to show it's closed with final results
            try:
                message = await channel.fetch_message(poll.message_id)
                
                # Create a new embed showing final results on the original message
                closed_embed = discord.Embed(
                    title=f"🔒 POLL CLOSED: {poll.question}",
                    description="Final Results:",
                    color=discord.Color.red()
                )
                
                # Find the winner (option with most votes)
                if total_votes > 0:
                    winner = max(results, key=results.get)
                    winner_votes = results[winner]
                    winner_percentage = (winner_votes / total_votes * 100)
                    
                    closed_embed.add_field(
                        name="🏆 Winner",
                        value=f"**{winner}** with {winner_votes} votes ({winner_percentage:.1f}%)",
                        inline=False
                    )
                
                # Add all results with visual bars
                for option in options:
                    votes = results.get(option, 0)
                    percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                    
                    # Create visual progress bar
                    bar_length = 15
                    filled = int((percentage / 100) * bar_length)
                    bar = "█" * filled + "░" * (bar_length - filled)
                    
                    # Add trophy emoji for winner
                    trophy = "🏆 " if votes == max(results.values()) and total_votes > 0 else ""
                    
                    closed_embed.add_field(
                        name=f"{trophy}{option}",
                        value=f"{bar} {votes} votes ({percentage:.1f}%)",
                        inline=False
                    )
                
                closed_embed.set_footer(text=f"Total votes: {total_votes} • Poll ended")
                
                await message.edit(embed=closed_embed)
                await message.clear_reactions()
                
                logger.info(f"Updated original poll message {poll.message_id} with final results")
            except Exception as e:
                logger.error(f"Failed to update original poll message: {str(e)}")
            
            logger.info(f"Closed poll {poll_id} and posted results")
        except Exception as e:
            logger.error(f"Failed to post poll {poll_id} results: {str(e)}")

def run_bot():
    with app.app_context():
        config = BotConfig.query.first()
        if not config or not config.token:
            logger.warning("Bot token not configured. Bot will not start.")
            return
        
        token = config.token
    
    # Run the bot
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token. Please check your configuration.")
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")