 
# Discord Music BOT

A simple Discord music bot built with [Nextcord](https://github.com/nextcord/nextcord) and [yt-dlp](https://github.com/yt-dlp/yt-dlp) that plays audio from YouTube. The bot supports modern slash commands for an intuitive and user-friendly experience.

## Features

- **Voice Channel Management**:  
  - Join and leave voice channels automatically.
  - Automatically disconnects after 10 minutes of inactivity.

- **Music Playback**:  
  - Play audio from YouTube URLs (supports cookies for age-restricted or region-specific content).
  - Pause, resume, stop, and skip current playback.
  - Manage a song queue with commands to add, remove, and clear the queue.

- **Commands**:  
  - `/join` – Connects the bot to your voice channel.
  - `/leave` – Disconnects the bot from the voice channel.
  - `/play` – Plays a song from a YouTube URL or adds it to the queue if a song is already playing.
  - `/skip` – Skips the current song.
  - `/stop` – Stops playback and clears the queue.
  - `/queue` – Displays the current song queue.
  - `/remove` – Removes a song from the queue by its index.
  - `/clearqueue` – Clears the entire song queue.

## Requirements

- **Python**: Version 3.8 or higher  
- **Dependencies**:
  - [Nextcord](https://github.com/nextcord/nextcord)
  - [yt-dlp](https://github.com/yt-dlp/yt-dlp)
  - [python-dotenv](https://github.com/theskumar/python-dotenv)

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/Pietro00x/Discord-Music-BOT.git
   cd Discord-Music-BOT
   ```

2. **Create and activate a virtual environment** (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install the required packages**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your environment variables**:  
   Create a `.env` file in the root directory of the project with the following content:

   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   YOUTUBE_COOKIES_PATH=your_cookies_file.txt  # Optional: sometimes needed
   ```

5. **(Optional) Prepare your YouTube cookies file**:  
   If required, place your YouTube cookies file in the project directory (or update the path in the `.env` file).

## Usage

1. **Run the Bot**:

   ```bash
   python bot.py
   ```

2. **Invite the Bot to Your Server**:  
   Make sure the bot has the necessary permissions (including access to voice channels and slash commands). Use the OAuth2 URL Generator in the Discord Developer Portal to generate an invite link.

3. **Use Slash Commands**:  
   In your Discord server, use commands like `/join`, `/play`, `/skip`, etc., to control the bot.

 
