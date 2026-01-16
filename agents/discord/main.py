import asyncio
import json
import os  # For loading the token from environment variables
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Load environment variables from .env
load_dotenv(dotenv_path=ROOT_DIR / ".env")

from services.hala_ws import query_hala
from services.whoop_briefing import build_daily_briefing_payload, build_discord_embed_dict

# Set up intents
intents = discord.Intents.default()
intents.message_content = True  # Enable if you enabled it in the portal

# Create the bot with a command prefix (e.g., !)
bot = commands.Bot(command_prefix='!', intents=intents)

# In-memory session mapping per channel
SESSION_BY_CHANNEL = {}
HEALTH_CHANNEL_NAME = os.getenv("HEALTH_CHANNEL_NAME", "health-💪")
HEALTH_CHANNEL_ID = os.getenv("HEALTH_CHANNEL_ID")
HEALTH_BRIEFING_TIME = os.getenv("HEALTH_BRIEFING_TIME", "11:00")
HEALTH_TIMEZONE = os.getenv("HEALTH_TIMEZONE")
LAST_BRIEFING_DATE = None


def _is_health_channel(channel) -> bool:
    if HEALTH_CHANNEL_ID:
        try:
            return channel.id == int(HEALTH_CHANNEL_ID)
        except ValueError:
            return False
    return channel.name == HEALTH_CHANNEL_NAME


def _get_health_channel() -> Optional[discord.abc.GuildChannel]:
    if HEALTH_CHANNEL_ID:
        try:
            channel_id = int(HEALTH_CHANNEL_ID)
        except ValueError:
            return None
        return bot.get_channel(channel_id)

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == HEALTH_CHANNEL_NAME:
                return channel
    return None


def _get_schedule_parts() -> Tuple[int, int, object]:
    try:
        hour_str, minute_str = HEALTH_BRIEFING_TIME.split(":", 1)
        hour = int(hour_str)
        minute = int(minute_str)
    except ValueError:
        hour = 11
        minute = 0

    tzinfo = None
    if HEALTH_TIMEZONE:
        try:
            tzinfo = ZoneInfo(HEALTH_TIMEZONE)
        except Exception:
            tzinfo = None

    if tzinfo is None:
        tzinfo = datetime.now().astimezone().tzinfo

    return hour, minute, tzinfo


async def _send_health_briefing(channel) -> None:
    payload = await build_daily_briefing_payload()
    if payload.get("error"):
        await channel.send(payload["error"])
        return

    embed_dict = build_discord_embed_dict(payload)
    embed = discord.Embed.from_dict(embed_dict)
    await channel.send(embed=embed)


@tasks.loop(minutes=1)
async def daily_briefing_task():
    global LAST_BRIEFING_DATE

    channel = _get_health_channel()
    if not channel:
        return

    hour, minute, tzinfo = _get_schedule_parts()
    now = datetime.now(tzinfo)
    if now.hour != hour or now.minute != minute:
        return

    today = now.date().isoformat()
    if LAST_BRIEFING_DATE == today:
        return

    LAST_BRIEFING_DATE = today
    await _send_health_briefing(channel)

# Event: Runs when the bot is ready
@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}!')
    if not daily_briefing_task.is_running():
        daily_briefing_task.start()

# Basic command example: Responds to !hello
@bot.command()
async def hello(ctx):
    await ctx.send('Hello from your bot!')

def split_discord_messages(text, limit=2000):
    chunks = []
    remaining = text.strip()
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user and bot.user in message.mentions:
        if _is_health_channel(message.channel):
            try:
                async with message.channel.typing():
                    payload = await build_daily_briefing_payload()
            except (asyncio.TimeoutError, RuntimeError, OSError, json.JSONDecodeError) as exc:
                await message.channel.send(f"Briefing error: {exc}")
                return

            if payload.get("error"):
                await message.channel.send(payload["error"])
                return

            embed_dict = build_discord_embed_dict(payload)
            embed = discord.Embed.from_dict(embed_dict)
            await message.channel.send(embed=embed)
            return

        content = message.content
        content = re.sub(rf"<@!?{bot.user.id}>", "", content).strip()
        if not content:
            await message.channel.send("Please mention me with a question, e.g. `@HalaAI what is...`")
            return

        channel_id = message.channel.id
        session_id = SESSION_BY_CHANNEL.get(channel_id)
        if not session_id:
            session_id = str(uuid.uuid4())
            SESSION_BY_CHANNEL[channel_id] = session_id
            start_session = True
        else:
            start_session = False

        try:
            async with message.channel.typing():
                response = await query_hala(
                    content,
                    session_id=session_id,
                    start_session=start_session,
                    include_history=False,
                )
        except (asyncio.TimeoutError, RuntimeError, OSError, json.JSONDecodeError) as exc:
            await message.channel.send(f"LLM error: {exc}")
            return

        if not response:
            await message.channel.send("No response returned from HalaAI.")
            return

        for chunk in split_discord_messages(response):
            await message.channel.send(chunk)

    await bot.process_commands(message)

# Run the bot with your token (use os.getenv for security)
token = os.getenv('DISCORD_TOKEN')
if not token:
    raise RuntimeError("Missing DISCORD_TOKEN in environment or .env file.")
bot.run(token)  # Or hardcode for testing: bot.run('YOUR_TOKEN_HERE')
