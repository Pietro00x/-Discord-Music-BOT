import os
import logging
import asyncio
import yt_dlp
from typing import Optional, Tuple
import nextcord
from nextcord.ext import commands, tasks
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN: Optional[str] = os.getenv('DISCORD_TOKEN')
YOUTUBE_COOKIES_PATH: str = os.getenv('YOUTUBE_COOKIES_PATH', 'youtube_cookies.txt')
if not TOKEN:
    print("Error: DISCORD_TOKEN not found.")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Setup intents
intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Validate cookies file existence
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), YOUTUBE_COOKIES_PATH)
if not os.path.isfile(COOKIES_FILE):
    logger.error(f"Cookie file not found: {COOKIES_FILE}")
    exit(1)

# yt_dlp options
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': False,
    'cookiefile': COOKIES_FILE
}

# FFmpeg options (disable video)
FFMPEG_OPTIONS = {'options': '-vn'}

# Global dictionaries to store active voice clients and song queues
voice_clients = {}  # key: guild_id, value: {'vc': VoiceClient, 'last_active': timestamp}
music_queues = {}   # key: guild_id, value: list of song dicts with keys 'audio_url', 'title', 'channel'

async def get_voice_client(interaction: nextcord.Interaction) -> Optional[nextcord.VoiceClient]:
    guild = interaction.guild
    if not guild:
        await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
        return None
    member = guild.get_member(interaction.user.id)
    if not member or not member.voice:
        await interaction.followup.send("You need to be in a voice channel to use this command.", ephemeral=True)
        return None
    channel = member.voice.channel
    vc = guild.voice_client
    if vc:
        if vc.channel.id != channel.id:
            try:
                await vc.move_to(channel)
            except Exception as e:
                await interaction.followup.send("Failed to move to your voice channel.", ephemeral=True)
                return None
    else:
        try:
            vc = await channel.connect()
        except Exception as e:
            await interaction.followup.send("Failed to connect to your voice channel.", ephemeral=True)
            return None
    voice_clients[guild.id] = {'vc': vc, 'last_active': nextcord.utils.utcnow()}
    if guild.id not in music_queues:
        music_queues[guild.id] = []
    return vc

async def extract_info(url: str, retries: int = 3, delay: int = 5) -> Tuple[str, str]:
    for attempt in range(retries):
        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                # If it's a playlist, take the first entry
                info = info['entries'][0]
            return info['url'], info.get('title', 'Unknown Title')
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise e

def play_next_song(guild_id: int, vc: nextcord.VoiceClient):
    def after_playing(error: Optional[Exception]):
        async def coro():
            if error:
                logger.error(f"Error after playing: {error}")
            queue = music_queues.get(guild_id, [])
            if queue:
                next_song = queue.pop(0)
                source = nextcord.FFmpegPCMAudio(next_song['audio_url'], **FFMPEG_OPTIONS)
                vc.play(source, after=play_next_song(guild_id, vc))
                voice_clients[guild_id]['last_active'] = nextcord.utils.utcnow()
                try:
                    await next_song['channel'].send(f"Now playing: **{next_song['title']}**")
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
            else:
                voice_clients[guild_id]['last_active'] = nextcord.utils.utcnow()
        asyncio.run_coroutine_threadsafe(coro(), bot.loop)
    return after_playing

@tasks.loop(minutes=1)
async def check_inactivity():
    current_time = nextcord.utils.utcnow()
    for guild_id, data in list(voice_clients.items()):
        vc = data.get('vc')
        last_active = data.get('last_active')
        if not vc or not last_active:
            continue
        if not vc.is_playing() and (current_time - last_active).total_seconds() > 600:
            try:
                await vc.disconnect()
                del voice_clients[guild_id]
                music_queues.pop(guild_id, None)
            except Exception as e:
                logger.error(f"Error disconnecting from guild {guild_id}: {e}")

@check_inactivity.before_loop
async def before_inactivity():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    check_inactivity.start()
    logger.info(f"Bot is ready as {bot.user}")

@bot.event
async def on_voice_state_update(member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
    if member == bot.user and not after.channel:
        guild_id = member.guild.id
        voice_clients.pop(guild_id, None)
        music_queues.pop(guild_id, None)

@bot.slash_command(name="join", description="Bot joins your voice channel.")
async def join(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    vc = await get_voice_client(interaction)
    if vc:
        await interaction.followup.send(f"Connected to **{vc.channel}**", ephemeral=True)

@bot.slash_command(name="leave", description="Bot leaves the voice channel.")
async def leave(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    vc = interaction.guild.voice_client if interaction.guild else None
    if vc:
        try:
            await vc.disconnect()
            voice_clients.pop(interaction.guild.id, None)
            music_queues.pop(interaction.guild.id, None)
            await interaction.followup.send("Disconnected.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send("Failed to disconnect.", ephemeral=True)
    else:
        await interaction.followup.send("Not connected to any voice channel.", ephemeral=True)

@bot.slash_command(name="play", description="Plays a song from a YouTube URL.")
async def play(interaction: nextcord.Interaction, url: str):
    await interaction.response.defer()
    guild = interaction.guild
    if not guild:
        await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
        return
    vc = await get_voice_client(interaction)
    if not vc:
        return
    try:
        audio_url, title = await extract_info(url)
    except Exception as e:
        await interaction.followup.send(f"Failed to extract audio: {e}", ephemeral=True)
        return
    # If a song is already playing, add this song to the queue
    if vc.is_playing():
        music_queues[guild.id].append({
            'audio_url': audio_url,
            'title': title,
            'channel': interaction.channel
        })
        await interaction.followup.send(f"**{title}** added to the queue.", ephemeral=False)
    else:
        source = nextcord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        vc.play(source, after=play_next_song(guild.id, vc))
        voice_clients[guild.id]['last_active'] = nextcord.utils.utcnow()
        await interaction.followup.send(f"Now playing: **{title}**", ephemeral=False)

@bot.slash_command(name="skip", description="Skips the current song.")
async def skip(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    vc = interaction.guild.voice_client if interaction.guild else None
    if vc and vc.is_playing():
        vc.stop()
        voice_clients[interaction.guild.id]['last_active'] = nextcord.utils.utcnow()
        await interaction.followup.send("Song skipped.", ephemeral=True)
    else:
        await interaction.followup.send("No song is playing.", ephemeral=True)

@bot.slash_command(name="stop", description="Stops playback and clears the queue.")
async def stop(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    vc = interaction.guild.voice_client if interaction.guild else None
    if vc and vc.is_playing():
        vc.stop()
        music_queues[interaction.guild.id].clear()
        voice_clients[interaction.guild.id]['last_active'] = nextcord.utils.utcnow()
        await interaction.followup.send("Playback stopped and queue cleared.", ephemeral=True)
    else:
        await interaction.followup.send("No playback in progress.", ephemeral=True)

@bot.slash_command(name="queue", description="Shows the current song queue.")
async def queue_cmd(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if not guild:
        await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
        return
    queue_list = music_queues.get(guild.id, [])
    if not queue_list:
        await interaction.followup.send("The queue is empty.", ephemeral=True)
        return
    message = "Song Queue:\n"
    for i, song in enumerate(queue_list, start=1):
        message += f"{i}. {song['title']}\n"
    await interaction.followup.send(message, ephemeral=False)

@bot.slash_command(name="remove", description="Removes a song from the queue by index (e.g. 1).")
async def remove(interaction: nextcord.Interaction, index: int):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if not guild:
        await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
        return
    queue_list = music_queues.get(guild.id, [])
    if not queue_list or index < 1 or index > len(queue_list):
        await interaction.followup.send("Invalid index.", ephemeral=True)
        return
    removed = queue_list.pop(index - 1)
    await interaction.followup.send(f"Removed **{removed['title']}** from the queue.", ephemeral=True)

@bot.slash_command(name="clearqueue", description="Clears the song queue.")
async def clearqueue(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if guild and guild.id in music_queues:
        music_queues[guild.id].clear()
        await interaction.followup.send("Queue cleared.", ephemeral=True)
    else:
        await interaction.followup.send("The queue is already empty.", ephemeral=True)

try:
    bot.run(TOKEN)
except Exception as e:
    logger.critical(f"Failed to start the bot: {e}")
