"""
Circle Bot - A Discord bot that analyses circle drawings and maintains daily leaderboards.

This bot allows users to submit circle drawings, analyses their circularity,
and maintains a daily leaderboard system with automatic prompts.
"""

import json
import os
import signal
import sqlite3
import sys
from datetime import datetime, UTC
import zoneinfo

import aiohttp
import cv2
import discord
from discord import app_commands
import numpy as np
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# =============================================================================
# CONFIGURATION
# =============================================================================

# Version
VERSION = "1.0.0"

# File paths
CONFIG_FILE = "bot_config.json"
DATABASE_FILE = "circle_scores.db"

# Bot configuration
PROMPT_CHANNEL_ID = 0  # Will be loaded from config file
scheduler = None

# =============================================================================
# CONFIGURATION FUNCTIONS
# =============================================================================


def load_config():
    """
    Load configuration from file or create default.
    
    Returns:
        dict: Configuration dictionary containing bot settings
    """
    default_config = {
        'discord_token': '',
        'prompt_channel_id': 0,
        'challenge_timezone': 'Europe/London'
    }
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Ensure challenge_timezone key exists
            if 'challenge_timezone' not in config:
                config['challenge_timezone'] = 'Europe/London'
                save_config(config)
            print(f"📋 Loaded configuration from {CONFIG_FILE}")
            return config
    except FileNotFoundError:
        print(f"📋 No configuration file found. Creating default {CONFIG_FILE}")
        save_config(default_config)
        return default_config
    except json.JSONDecodeError as e:
        print(f"⚠️  Warning: Invalid configuration file format: {e}")
        print("   Creating new configuration file...")
        save_config(default_config)
        return default_config


def save_config(config):
    """
    Save configuration to file.
    
    Args:
        config (dict): Configuration dictionary to save
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"💾 Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")


def get_discord_token():
    """
    Get Discord token from config file or environment variable.
    
    Returns:
        str: Discord bot token
        
    Raises:
        ValueError: If no token is found
    """
    # First try to get from config file
    config = load_config()
    token = config.get('discord_token', '').strip()
    
    if token:
        return token
    
    # Fallback to environment variable
    token = os.getenv("DISCORD_TOKEN", "").strip()
    
    if token:
        # Save to config file for future use
        config['discord_token'] = token
        save_config(config)
        return token
    
    # No token found
    print("❌ ERROR: Discord token not found!")
    print("   Please add your Discord bot token to the configuration file:")
    print(f"   Edit {CONFIG_FILE} and add:")
    print('   {')
    print('     "discord_token": "your_bot_token_here"')
    print('   }')
    print("")
    print("   Or set the DISCORD_TOKEN environment variable:")
    print("   $env:DISCORD_TOKEN='your_token_here'")
    sys.exit(1)

def set_challenge_timezone(tz_str):
    config = load_config()
    config['challenge_timezone'] = tz_str
    save_config(config)

def get_challenge_timezone():
    config = load_config()
    return config.get('challenge_timezone', 'Europe/London')  # Default to Europe/London

# =============================================================================
# BOT SETUP
# =============================================================================

# Configure Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

# Create bot instance
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# =============================================================================
# IMAGE ANALYSIS
# =============================================================================


async def analyse_image(image_bytes):
    """
    Analyses the circularity of a shape in an image.
    
    Args:
        image_bytes: Raw image data as bytes
        
    Returns:
        float: Circularity percentage (0-100) or None if analysis fails
    """
    try:
        # Convert bytes to OpenCV image
        image_array = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if image is None:
            print("⚠️  Image analysis failed: Could not decode image")
            return None

        # Convert to grayscale and apply threshold
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print("⚠️  Image analysis failed: No shapes found in image")
            return 0.0

        # Find the largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        if area == 0:
            print("⚠️  Image analysis failed: Shape has no area")
            return 0.0

        # Calculate circularity
        (x, y), radius = cv2.minEnclosingCircle(largest_contour)
        circle_area = np.pi * (radius ** 2)
        
        if circle_area == 0:
            print("⚠️  Image analysis failed: Could not calculate circle area")
            return 0.0
            
        circularity = area / circle_area
        percentage = circularity * 100
        
        print(f"✅ Image analysed successfully: {percentage:.2f}% circularity")
        return percentage
        
    except Exception as e:
        print(f"❌ Error analysing image: {e}")
        return None

# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================


def setup_database():
    """Initialises the SQLite database and creates the scores table."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                user_id INTEGER,
                score REAL,
                date TEXT,
                PRIMARY KEY (user_id, date)
            )
        """)
        conn.commit()
        conn.close()
        print("✅ Database initialised successfully")
    except Exception as e:
        print(f"❌ Database initialisation failed: {e}")
        raise

# =============================================================================
# SCHEDULED TASKS
# =============================================================================


async def daily_prompt():
    """Sends the daily circle drawing prompt."""
    global PROMPT_CHANNEL_ID
    
    try:
        if PROMPT_CHANNEL_ID == 0:
            print("⚠️  Daily prompt skipped: No channel configured")
            return
            
        channel = bot.get_channel(PROMPT_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🎯 Daily Circle Challenge",
                description="Good morning, artists! It's time for today's circle drawing challenge.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📝 Challenge", 
                value="Draw the most perfect circle you can! Upload your drawing as an image to participate.", 
                inline=False
            )
            challenge_tz = get_challenge_timezone()
            embed.add_field(
                name="⏰ Deadline", 
                value=f"You have until midnight {challenge_tz} to submit your circle!", 
                inline=False
            )
            embed.add_field(
                name="🏆 Scoring", 
                value="Your circle will be analysed for circularity. The closer to 100%, the better!", 
                inline=False
            )
            embed.set_footer(text="Reply to this message with your circle drawing!")
            
            await channel.send(embed=embed)
            print(f"✅ Daily prompt sent to #{channel.name}")
        else:
            print(f"❌ Daily prompt failed: Channel ID {PROMPT_CHANNEL_ID} not found")
    except Exception as e:
        print(f"❌ Error sending daily prompt: {e}")

# =============================================================================
# SLASH COMMANDS
# =============================================================================


@tree.command(name="set", description="Configure the challenge channel (Admin only)")
@app_commands.describe(channel="The channel for daily challenges (optional, uses current channel)")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """Sets the channel for daily prompts and circle submissions."""
    global PROMPT_CHANNEL_ID
    
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    if channel is None:
        channel = interaction.channel
    
    PROMPT_CHANNEL_ID = channel.id
    
    # Save to config file
    config = load_config()
    config['prompt_channel_id'] = channel.id
    save_config(config)
    
    embed = discord.Embed(
        title="✅ Channel Set Successfully!",
        description=f"Daily prompts and circle submissions will now be handled in {channel.mention}",
        color=discord.Color.green()
    )
    embed.add_field(name="Channel ID", value=str(channel.id), inline=True)
    embed.add_field(name="Channel Name", value=channel.name, inline=True)
    challenge_tz = get_challenge_timezone()
    embed.add_field(name="🕐 Daily Prompt Time", value=f"Midnight {challenge_tz}", inline=True)
    
    await interaction.response.send_message(embed=embed)
    print(f"✅ Channel configured: #{channel.name} (ID: {channel.id})")


@tree.command(name="leaderboard", description="View today's leaderboard")
async def leaderboard(interaction: discord.Interaction):
    """Displays today's leaderboard."""
    try:
        today = datetime.now(UTC).strftime('%Y-%m-%d')
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, score FROM scores WHERE date = ? ORDER BY score DESC", (today,))
        results = cursor.fetchall()
        conn.close()

        if not results:
            await interaction.response.send_message("📊 No entries for today's leaderboard yet.")
            return

        embed = discord.Embed(title=f"🏆 Leaderboard for {today}", color=discord.Color.gold())
        for i, (user_id, score) in enumerate(results, 1):
            try:
                user = await bot.fetch_user(user_id)
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                embed.add_field(name=f"{medal} {user.name}", value=f"Score: {score:.2f}%", inline=False)
            except:
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                embed.add_field(name=f"{medal} Unknown User", value=f"Score: {score:.2f}%", inline=False)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message("❌ Sorry, there was an error fetching the leaderboard.")
        print(f"❌ Error in leaderboard command: {e}")


@tree.command(name="challenge", description="Post the daily challenge message")
async def challenge(interaction: discord.Interaction):
    """Posts the daily challenge message."""
    try:
        await daily_prompt()
        await interaction.response.send_message("✅ Daily challenge message has been posted!")
        print(f"✅ Daily challenge posted by {interaction.user.name}")
    except Exception as e:
        await interaction.response.send_message("❌ Sorry, there was an error posting the daily challenge.")
        print(f"❌ Error in challenge command: {e}")


@tree.command(name="timezone", description="Set or view the challenge timezone (Admin only)")
@app_commands.describe(timezone="The timezone for daily challenges (e.g., Europe/London)")
async def timezone(interaction: discord.Interaction, timezone: str = None):
    """Set or view the challenge timezone (admin only)."""
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    if timezone is None:
        current = get_challenge_timezone()
        await interaction.response.send_message(f"🌍 Challenge timezone is set to `{current}`.", ephemeral=True)
        return
    
    # Validate timezone
    try:
        zoneinfo.ZoneInfo(timezone)
    except Exception:
        await interaction.response.send_message(f"❌ `{timezone}` is not a valid timezone. Please use a valid tz database name (e.g., Europe/London, America/New_York). See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones", ephemeral=True)
        return
    
    set_challenge_timezone(timezone)
    await interaction.response.send_message(f"✅ Challenge timezone has been set to `{timezone}`. Daily challenges will now post at midnight in this timezone.")

# =============================================================================
# MESSAGE HANDLING
# =============================================================================


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Only process images in the prompt channel
    if message.channel.id != PROMPT_CHANNEL_ID:
        return

    if message.attachments:
        attachment = message.attachments[0]
        if attachment.content_type.startswith('image/'):
            today = datetime.now(UTC).strftime('%Y-%m-%d')
            user_id = message.author.id
            user_name = message.author.name

            print(f"📸 Processing daily challenge image from {user_name}")

            # Check if the user has already submitted today
            try:
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM scores WHERE user_id = ? AND date = ?", (user_id, today))
                if cursor.fetchone():
                    await message.reply("❌ You've already submitted your circle for today. Try again tomorrow!")
                    conn.close()
                    print(f"⚠️  {user_name} attempted duplicate submission")
                    return
                conn.close()
            except Exception as e:
                await message.reply("❌ Sorry, there was an error checking your previous submissions.")
                print(f"❌ Database error checking submissions: {e}")
                return

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status == 200:
                            image_bytes = await resp.read()
                            score = await analyse_image(image_bytes)
                            if score is not None:
                                # Save score to database
                                try:
                                    conn = sqlite3.connect(DATABASE_FILE)
                                    cursor = conn.cursor()
                                    cursor.execute("INSERT INTO scores (user_id, date, score) VALUES (?, ?, ?)", (user_id, today, score))
                                    conn.commit()
                                    conn.close()
                                    
                                    embed = discord.Embed(
                                        title="🎯 Circle Analysis Complete!",
                                        description=f"Great job, {user_name}!",
                                        color=discord.Color.green()
                                    )
                                    embed.add_field(name="📊 Your Score", value=f"**{score:.2f}%** circularity", inline=True)
                                    embed.add_field(name="📅 Date", value=today, inline=True)
                                    embed.add_field(name="🏆 Status", value="✅ Saved to leaderboard!", inline=False)
                                    
                                    await message.reply(embed=embed)
                                    print(f"✅ {user_name} scored {score:.2f}% - saved to database")
                                except Exception as e:
                                    await message.reply("⚠️ Your circle was analysed, but there was an error saving your score.")
                                    print(f"❌ Database error saving score: {e}")
                            else:
                                await message.reply("❌ I couldn't analyse that image. Please try again with a simple black-on-white drawing.")
                                print(f"⚠️  {user_name} submitted unanalysable image")
                        else:
                            await message.reply("❌ Sorry, I couldn't download that image.")
                            print(f"⚠️  Failed to download image from {user_name}")
            except Exception as e:
                await message.reply("❌ Sorry, I had trouble processing that image.")
                print(f"❌ Error processing image from {user_name}: {e}")

# =============================================================================
# BOT EVENTS
# =============================================================================


@bot.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    print("\n" + "=" * 60)
    print(f"🎯 Circle Bot v{VERSION} - Daily Drawing Challenge Bot")
    print("=" * 60)
    print(f"✅ Logged in as: {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"📅 Started at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("-" * 60)
    
    # Initialise database
    setup_database()
    
    # Load configuration
    global PROMPT_CHANNEL_ID
    config = load_config()
    PROMPT_CHANNEL_ID = config.get('prompt_channel_id', 0)
    
    # Setup scheduler
    global scheduler
    scheduler = AsyncIOScheduler()
    challenge_tz = get_challenge_timezone()
    scheduler.add_job(daily_prompt, 'cron', hour=0, minute=0, timezone=challenge_tz)  # Midnight in configured timezone
    scheduler.start()
    print(f"⏰ Daily prompt scheduler started (midnight {challenge_tz})")
    
    # Sync slash commands
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"⚠️  Error syncing slash commands: {e}")
    
    # Status check
    if PROMPT_CHANNEL_ID == 0:
        print("⚠️  No channel configured - use /set to configure a channel")
    else:
        channel = bot.get_channel(PROMPT_CHANNEL_ID)
        if channel:
            print(f"📢 Challenge channel: #{channel.name}")
        else:
            print(f"⚠️  Configured channel ID {PROMPT_CHANNEL_ID} not found")
    
    print("=" * 60)
    print("🚀 Bot is ready! Use /set to configure a channel.")
    print("=" * 60)


@bot.event
async def on_disconnect():
    """Called when the bot disconnects from Discord."""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("⏹️  Scheduler shutdown")

# =============================================================================
# SHUTDOWN HANDLING
# =============================================================================


def signal_handler(sig, frame):
    """Handle graceful shutdown on Ctrl+C."""
    print("\n" + "=" * 60)
    print("🛑 Shutting down Circle Bot...")
    print("=" * 60)
    
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("⏹️  Scheduler stopped")
    
    print("👋 Goodbye!")
    print("🎯 Circle Bot has exited. Thank you for using Circle Bot! ��")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    try:
        print("🚀 Starting Circle Bot...")
        discord_token = get_discord_token()
        bot.run(discord_token)
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        sys.exit(1)
