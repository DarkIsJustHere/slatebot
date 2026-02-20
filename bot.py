import discord
import os
import re
import csv
import io
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
# TOTALS SCALING (Historical Model)
# ==============================

def calculate_units(wins, total):
    percentage = (wins / total) * 100

    # SMALL SAMPLE
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

    # LARGE SAMPLE
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

    # Boost
    if total >= 40 and percentage >= 92:
        units += 0.25

    if total >= 50 and percentage >= 94:
        units += 0.25

    if units > 3:
        units = 3

    return units


# ==============================
# 4+ EMOJI LOGIC
# ==============================

def four_plus_emoji(adjusted_wins, total):
    percentage = (adjusted_wins / total) * 100

    if percentage >= 97 and total >= 40:
        return " ☢️"
    elif percentage >= 90:
        return " ⚠️"
    return ""


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
# EVENT
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

    if not message.attachments:
        return

    csv_file = None

    for attachment in message.attachments:
        if attachment.filename.endswith(".csv"):
            csv_file = attachment
            break

    if not csv_file:
        return

    file_bytes = await csv_file.read()
    decoded = file_bytes.decode("utf-8")

    reader = csv.DictReader(io.StringIO(decoded))

    four_plus_games = []
    totals_games = []

    for row in reader:
        league = normalize_league(row["League"])
        player1 = row["Player 1"]
        player2 = row["Player 2"]
        play = row["Play"].upper()
        history = row["History"]

        # Extract record
        record_match = re.search(r"\((\d+)\/(\d+)\)", history)
        if not record_match:
            continue

        wins = int(record_match.group(1))
        total = int(record_match.group(2))

        est_time = row["Time (Eastern)"]
        pst_time = row["Time (Pacific)"]

        # Remove date portion
        est_time = est_time.split(" ")[-2] + " " + est_time.split(" ")[-1]
        pst_time = pst_time.split(" ")[-2] + " " + pst_time.split(" ")[-1]

        formatted_time = f"{est_time} EST / {pst_time} PST"

        # 4+
        if "4+" in play:
            adjusted_wins = total - wins
            emoji = four_plus_emoji(adjusted_wins, total)

            formatted = (
                f"{league} – {player1} vs {player2} @ "
                f"{formatted_time} ({adjusted_wins}/{total}){emoji}"
            )

            four_plus_games.append(formatted)

        # TOTALS
        elif "UNDER" in play or "OVER" in play:
            units = calculate_units(wins, total)
            play_type = "UNDER" if "UNDER" in play else "OVER"

            formatted = (
                f"{league} – {player1} vs {player2} "
                f"{play_type} {units}U @ {formatted_time} "
                f"({wins}/{total})"
            )

            totals_games.append(formatted)

    if not four_plus_games and not totals_games:
        return

    await clear_old_slate()
    await message.delete()

    new_messages = []

    if four_plus_games:
        header = await message.channel.send("## **4+ PLAYS 🔥**")
        new_messages.append(header)

        body = await message.channel.send("\n\n".join(four_plus_games))
        new_messages.append(body)

    if totals_games:
        header = await message.channel.send("## **TOTALS 🔥**")
        new_messages.append(header)

        body = await message.channel.send("\n\n".join(totals_games))
        new_messages.append(body)

    last_slate_messages = new_messages


bot.run(DISCORD_TOKEN)
