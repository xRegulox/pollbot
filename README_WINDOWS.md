# Regulo PollBot - Windows Setup Guide

## Quick Start

1. **Download and extract** the Regulo PollBot files to a folder
2. **Double-click** `start_regulo_pollbot.bat` to run the automatic setup
3. **Follow the setup prompts** - the script will:
   - Check for Python installation
   - Create a virtual environment
   - Install all required dependencies
   - Initialize the database
   - Start the bot

## What You Need

- **Windows 10/11**
- **Python 3.8 or higher** (download from [python.org](https://python.org))
  - ⚠️ **Important**: Check "Add Python to PATH" during installation
- **Internet connection** (for downloading dependencies)
- **Discord Bot Token** (get from [Discord Developer Portal](https://discord.com/developers/applications))

## Files Included

- `start_regulo_pollbot.bat` - Main setup and launcher script
- `quick_start.bat` - Quick launcher (after first setup)
- `requirements.txt` - Python dependencies list
- `README_WINDOWS.md` - This guide

## First Time Setup

1. **Run the setup**: Double-click `start_regulo_pollbot.bat`
2. **Configure your bot**:
   - Open your web browser to `http://localhost:5000`
   - Login with: `admin` / `admin`
   - Go to "Bot Configuration" and enter your Discord bot token
   - Configure your server settings

## Daily Usage

After the first setup, you can use `quick_start.bat` for faster startup.

## Troubleshooting

### "Python is not installed"
- Download Python from [python.org](https://python.org)
- During installation, check "Add Python to PATH"
- Restart your computer after installation

### "Failed to install dependencies"
- Check your internet connection
- Try running as Administrator
- Disable antivirus temporarily during setup

### "Bot token not configured"
- Get your bot token from [Discord Developer Portal](https://discord.com/developers/applications)
- Add your bot to your Discord server
- Enter the token in the web dashboard

### Web dashboard not loading
- Make sure no other application is using port 5000
- Try accessing `http://127.0.0.1:5000` instead
- Check Windows Firewall settings

## Getting Your Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Copy the bot token (keep it secret!)
5. Go to "OAuth2" > "URL Generator"
6. Select "bot" scope and required permissions
7. Use the generated URL to invite your bot to your server

## Support

If you encounter issues:
1. Check the console output for error messages
2. Ensure your Discord bot has proper permissions
3. Verify your bot token is correct
4. Make sure your Discord server allows the bot

## Security Notes

- Keep your bot token secret
- Change the default admin password after first login
- Only run the bot on trusted networks