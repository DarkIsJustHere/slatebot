import discord
import os
import re
from discord.ext import commands

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

ALLOWED_ROLE = "RW Official"

ALLOWED_CHANNELS = [
    1474078126630768822,
    1471792196582637728
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

last_slate_messages = []


# ==============================
# LEAGUE NORMALIZER
# ==============================

def normalize_league(name):
    name = name.upper()
    if "ELITE" in name:
        return "ELITE"
    if "SETKA" in name:
        return "SETKA"
    if "CUP" in name:
        return "CUP"
    if "CZECH" in name:
        return "CZECH"
    return name


# ==============================
# TOTALS SCALING ENGINE
# ==============================

def calculate_units(wins, total):
    percentage = (wins / total) * 100

    # SMALL SAMPLE (<30)
    if total < 30:
        if percentage >= 95:
            return 1.75
        elif percentage >= 91:
            return 1.75
        elif percentage >= 86:
            return 1.5
        elif percentage >= 81:
            return 1.25
        else:
            return 1.0

    # LARGE SAMPLE (30+)
    units = 1.0

    if percentage >= 96:
        units = 2.5
    elif percentage >= 93:
        units = 2.0
    elif percentage >= 89:
        units = 1.75
    elif percentage >= 84:
        units = 1.5
    elif percentage >= 81:
        units = 1.25
    else:
        units = 1.0

    # Boost rules
    if total >= 40 and percentage >= 92:
        units += 0.25

    if total >= 50 and percentage >= 94:
        units += 0.25

    if units > 3:
        units = 3

    return units


# ==============================
# 4+ EMOJI ENGINE
# ==============================

def four_plus_emoji(wins, total):
    percentage = (wins / total) * 100

    if percentage >= 97 and total >= 40:
        return " ☢️"
    elif percentage >= 90:
        return " ⚠️"
    return ""


# ==============================
# FORMATTER
# ==============================

def format_slate(lines):
    four_plus_games = []
    totals_games = []

    for line in lines:
        if not line.strip():
            continue

        line = line.replace("–", "-")

        record_match = re.search(r"\((\d+)\/(\d+)", line)
        if not record_match:
            continue

        wins = int(record_match.group(1))
        total = int(record_match.group(2))

        parts = line.split("@")
        if len(parts) < 2:
            continue

        left = parts[0].strip()
        time_part = parts[1].split("(")[0].strip()

        if "-" not in left:
            continue

        league, matchup = left.split("-", 1)
        league = normalize_league(league.strip())
        matchup = matchup.strip()

        # TOTALS
        if "UNDER" in line.upper() or "OVER" in line.upper():
            units = calculate_units(wins, total)
            play_type = "UNDER" if "UNDER" in line.upper() else "OVER"

            formatted = f"{league} – {matchup} {play_type} {units}U @ {time_part} ({wins}/{total})"
            totals_games.append(formatted)

        # 4+
        else:
            adjusted_wins = total - wins
            emoji = four_plus_emoji(adjusted_wins, total)

            formatted = f"{league} – {matchup} @ {time_part} ({adjusted_wins}/{total}){emoji}"
            four_plus_games.append(formatted)

    return four_plus_games, totals_games


# ==============================
# CLEAR OLD SLATE
# ==============================

async def clear_old_slate():
    global last_slate_messages
    for msg in last_slate_messages:
        try:
            await msg.delete()
        except:
            pass
    last_slate_messages = []


# ==============================
# EVENTS
# ==============================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    global last_slate_messages

    if message.author.bot:
        return

    # Ping test
    if message.content.strip().lower() == "ping":
        await message.channel.send("pong")
        return

    if message.channel.id not in ALLOWED_CHANNELS:
        return

    if not any(role.name == ALLOWED_ROLE for role in message.author.roles):
        return

    content_lines = []

    # CSV Attachment Support
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(".csv"):
                file_bytes = await attachment.read()
                decoded = file_bytes.decode("utf-8")
                content_lines = decoded.split("\n")
                break

    # Normal text fallback
    if not content_lines:
        content_lines = message.content.split("\n")

    four_plus, totals = format_slate(content_lines)

    if not four_plus and not totals:
        return

    await clear_old_slate()
    await message.delete()

    new_messages = []

    if four_plus:
        header = await message.channel.send("## **4+ PLAYS 🔥**")
        new_messages.append(header)

        body = await message.channel.send("\n\n".join(four_plus))
        new_messages.append(body)

    if totals:
        header = await message.channel.send("## **TOTALS 🔥**")
        new_messages.append(header)

        body = await message.channel.send("\n\n".join(totals))
        new_messages.append(body)

    last_slate_messages = new_messages


bot.run(DISCORD_TOKEN)
