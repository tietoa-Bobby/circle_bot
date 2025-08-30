# Circle Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

A Discord bot that analyzes circle drawings and maintains daily leaderboards. Users can submit circle drawings, get their circularity scores, and compete on daily leaderboards.

## Features

- Circle Analysis: Analyzes uploaded images to determine circularity percentage
- Daily Leaderboards: Tracks scores and displays rankings with medals
- Automatic Prompts: Posts daily challenges at midnight in configurable timezone
- Score Tracking: SQLite database for persistent score storage
- One Submission Per Day: Prevents spam and ensures fair competition
- Easy Configuration: Simple `/set` command for channel setup
- Rich Embeds: Beautiful Discord embeds for all responses

## Setup

### Prerequisites

- Python 3.8 or higher
- Discord bot token
- Administrator permissions in your Discord server

### Installation

```bash
# Clone or download the project
cd circle_bot

# Install dependencies
pip install -r requirements.txt
```

### Configuration Setup

The bot uses a configuration file to store settings. You have two options for setting up your Discord token:

#### Option A: Edit Configuration File (Recommended)

1. Create the configuration file `bot_config.json`:
   ```json
   {
     "discord_token": "your_bot_token_here",
     "prompt_channel_id": 0,
     "challenge_timezone": "Europe/London"
   }
   ```

2. Replace `your_bot_token_here` with your actual Discord bot token

Note: The `bot_config.json` file is included in `.gitignore` to protect your personal token. You'll need to create this file yourself after cloning the repository.

#### Option B: Environment Variable (Legacy)

You can still use environment variables as a fallback:

**Windows (PowerShell):**
```powershell
$env:DISCORD_TOKEN="your_bot_token_here"
```

**Windows (Command Prompt):**
```cmd
set DISCORD_TOKEN=your_bot_token_here
```

**Linux/Mac:**
```bash
export DISCORD_TOKEN="your_bot_token_here"
```

Note: If you use the environment variable, the bot will automatically save it to the configuration file for future use.

### Discord Bot Setup

1. Create a Discord Application:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Go to the "Bot" section and click "Add Bot"

2. Configure Bot Permissions:
   - In the "Bot" section, scroll down to "Privileged Gateway Intents"
   - Enable Message Content Intent (required)
   - Optionally enable "Server Members Intent" and "Presence Intent"

3. Invite Bot to Server:
   - Go to "OAuth2" → "URL Generator"
   - Select scopes: bot and applications.commands (required for slash commands)
   - Select bot permissions:
     - Send Messages
     - Read Message History
     - Attach Files
     - Embed Links
     - Manage Messages
     - Use Slash Commands
   - Copy the generated URL and open it in your browser
   - Select your server and authorize

### Run the Bot

```bash
python bot.py
```

You should see startup messages like:
```
==================================================
Circle Bot Starting Up...
==================================================
Logged in as: CircleBot#1234
Bot ID: 123456789012345678
Started at: 2024-01-01 12:00:00 UTC
--------------------------------------------------
Database initialized successfully
Loaded configuration: Channel ID 123456789
Daily prompt scheduler started (midnight Europe/London)
Challenge channel: #circle-challenge
==================================================
Bot is ready! Use /set to configure a channel.
Slash commands synced successfully!
==================================================
```

### Configure the Challenge Channel

Once the bot is running, use the `/set` command in the channel where you want daily challenges:

```
/set
```

Or specify a different channel:

```
/set #circle-challenge
```

## Commands

| Command | Description | Usage | Permissions |
|---------|-------------|-------|-------------|
| `/set [channel]` | Configure challenge channel | `/set` or `/set #channel` | Admin |
| `/leaderboard` | View today's rankings | `/leaderboard` | Anyone |
| `/challenge` | Post daily challenge message | `/challenge` | Anyone |
| `/timezone [timezone]` | Set or view challenge timezone | `/timezone Europe/London` | Admin |

### Command Details

#### `/set [channel]`
- Purpose: Sets the channel for daily prompts and circle submissions
- Permissions: Administrator required
- Usage: 
  - `/set` - Uses current channel
  - `/set #channel-name` - Uses specified channel
- Response: Confirmation embed with channel details

#### `/leaderboard`
- Purpose: Displays today's leaderboard with rankings
- Features:
  - Medal emojis for top 3 positions
  - Score percentages
  - User names
  - "No entries" message if empty

#### `/challenge`
- Purpose: Manually triggers the daily challenge message
- Permissions: Anyone can use
- Use Cases:
  - Testing the challenge message
  - If the scheduled message didn't post
  - Starting a new challenge outside of schedule
- Response: Confirmation that the message was posted

#### `/timezone [timezone]`
- Purpose: Set or view the server's challenge timezone (when daily challenges are posted)
- Permissions: Administrator required
- Usage:
  - `/timezone Europe/London` - Sets the challenge timezone
  - `/timezone` - Shows the current challenge timezone
- Validation: Must use a valid tz database name (e.g., Europe/London, America/New_York)
- Response: Confirmation or error message

## Timezone Support

Administrators can set the timezone for when daily challenges are posted. Use the `/timezone` command:

```
/timezone Europe/London
```

To see the current challenge timezone:
```
/timezone
```

A list of valid timezone names can be found [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

### Example bot_config.json
```json
{
  "discord_token": "your_bot_token_here",
  "prompt_channel_id": 0,
  "challenge_timezone": "Europe/London"
}
```

## Usage

### Daily Challenge Flow

1. Daily Prompt: At midnight in the configured timezone, the bot posts a challenge in the configured channel
2. Submit Circle: Users reply with an image of their circle drawing
3. Get Score: Bot analyzes the image and returns a circularity percentage
4. View Rankings: Use `/leaderboard` to see how you rank against others

### Submission Methods

#### Image Upload
- Draw a circle on paper or digitally
- Take a photo or screenshot
- Upload the image in the challenge channel
- Get instant score feedback

### Image Requirements

- Format: Any common image format (PNG, JPG, GIF, etc.)
- Content: Simple black drawing on white background works best
- Quality: Clear, well-lit images give better results
- Size: Reasonable file sizes (under 10MB)

### Scoring System

- 100%: Perfect circle
- 90-99%: Excellent circle
- 80-89%: Good circle
- 70-79%: Fair circle
- Below 70%: Needs improvement

## Technical Details

### How Circle Analysis Works

1. Image Processing: Converts image to grayscale
2. Thresholding: Creates binary image (black/white)
3. Contour Detection: Finds shapes in the image
4. Area Calculation: Measures actual shape area
5. Circularity: Compares to perfect circle area
6. Scoring: Returns percentage (0-100%)

### File Structure

```
circle_bot/
├── bot.py              # Main bot code
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── .gitignore         # Git ignore rules
├── bot_config.json    # Bot configuration (create this yourself)
└── circle_scores.db   # SQLite database (auto-generated)
```

Note: `bot_config.json` and `circle_scores.db` are not included in the repository for privacy. You'll need to create `bot_config.json` yourself, and the database will be created automatically when you first run the bot.

### Dependencies

- `discord.py` - Discord API wrapper
- `opencv-python-headless` - Image processing
- `numpy` - Numerical computations
- `apscheduler` - Task scheduling
- `aiohttp` - Async HTTP client
- `zoneinfo` (Python 3.9+) or `backports.zoneinfo` (Python 3.8) - Timezone support

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Discord token not found" | Add your token to `bot_config.json` or set DISCORD_TOKEN environment variable |
| "Message Content Intent" error | Enable Message Content Intent in Discord Developer Portal |
| Bot doesn't respond to commands | Check bot permissions and channel access |
| Image analysis fails | Try simpler, clearer images with good contrast |
| Channel not found | Use `!set` to reconfigure the channel |
| Database errors | Check file permissions and disk space |
| Configuration file errors | Delete `bot_config.json` and restart the bot to recreate it |

### Terminal Messages

The bot provides detailed terminal feedback:

- Success: Green checkmarks for successful operations
- Warning: Yellow warnings for non-critical issues
- Error: Red X for errors that need attention
- Info: Blue info for configuration and status updates

### Getting Help

1. Check terminal output for detailed error messages
2. Ensure proper permissions in Discord
3. Verify environment variables are set correctly
4. Check bot configuration with `/set`

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details. 