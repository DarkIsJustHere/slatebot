import discord
import csv
import io
import re
import os
from datetime import datetime

# ==============================
# TOKEN (SAFE FOR HOSTING)
# ==============================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("No TOKEN found. Set it in your environment variables.")

# ==============================
# ALLOWED CHANNELS
# ==============================

ALLOWED_CHANNELS = [
    1471792196582637728,  # Testing server
    1474078126630768822   # Main server
]

# ==============================
# DISCORD SETUP
# ==============================

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

last_slate_messages = []

# ==============================
# UTIL FUNCTIONS
# ==============================

def format_units(u):
    if u == 1:
        return "1U"
    if u == 1.25:
        return "1.25U"
    if u == 1.5:
        return "1.5U"
    if u == 1.75:
        return "1.75U"
    if u == 2:
        return "2U"
    if u == 2.5:
        return "2.5U"
    if u == 3:
        return "3U"
    return f"{u}U"

def convert_league(name):
    name = name.lower()
    if "elite" in name:
        return "ELITE"
    if "setka" in name:
        return "SETKA"
    if "czech" in name:
        return "CZECH"
    if "cup" in name:
        return "CUP"
    return name.upper()

def parse_time(est_time):
    dt = datetime.strptime(est_time, "%m/%d %I:%M %p")
    est = dt.strftime("%I:%M %p")
    pst_dt = dt.replace(hour=(dt.hour - 3) % 24)
    pst = pst_dt.strftime("%I:%M %p")
    return est, pst

# ==============================
# BOT READY
# ==============================

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

# ==============================
# MESSAGE HANDLER
# ==============================

@client.event
async def on_message(message):
    global last_slate_messages

    if message.author.bot:
        return

    if message.channel.id not in ALLOWED_CHANNELS:
        return

    # Ping test
    if message.content.lower() == "ping":
        await message.channel.send("pong")
        return

    if not message.attachments:
        return

    attachment = message.attachments[0]
    if not attachment.filename.endswith(".csv"):
        return

    file_bytes = await attachment.read()
    decoded = file_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))

    four_plus = {}
    totals = {}

    for row in reader:
        league = convert_league(row["League"])
        p1 = row["Player 1"]
        p2 = row["Player 2"]
        play = row["Play"]
        history = row["History"]
        est_time = row["Time (Eastern)"]

        est, pst = parse_time(est_time)

        # 4+ logic
        if "4+" in play:
            match = re.search(r"\((\d+)/(\d+)\)", history)
            if not match:
                continue

            wins = int(match.group(2)) - int(match.group(1))
            total = int(match.group(2))

            tier = "normal"
            if wins >= 40:
                tier = "nuke"
            elif wins <= 22:
                tier = "caution"

            key = f"{league}{p1}{p2}{est}"
            four_plus[key] = (league, p1, p2, est, pst, wins, total, tier)

        # Totals logic
        elif "Over/Under" in history:
            match = re.search(r"\((\d+)/(\d+)\)", history)
            if not match:
                continue

            wins = int(match.group(1))
            total = int(match.group(2))
            pct = wins / total

            if total >= 30:
                if pct >= .95:
                    units = 2.5
                elif pct >= .91:
                    units = 2
                elif pct >= .86:
                    units = 1.5
                elif pct >= .81:
                    units = 1.25
                else:
                    units = 1
            else:
                if pct >= .95:
                    units = 2
                elif pct >= .91:
                    units = 1.75
                elif pct >= .86:
                    units = 1.5
                elif pct >= .81:
                    units = 1.25
                else:
                    units = 1

            key = f"{league}{p1}{p2}{est}{play}"
            totals[key] = (league, p1, p2, play, units, est, pst, wins, total)

    # ==============================
    # SEND NEW SLATE FIRST
    # ==============================

    old_messages = last_slate_messages.copy()
    last_slate_messages = []

    await message.delete()

    # 4+ Header
    msg1 = await message.channel.send("🏓 **4+ PLAYS** 🏓")
    last_slate_messages.append(msg1)

    # 4+ Body
    if four_plus:
        text = ""
        for v in four_plus.values():
            league, p1, p2, est, pst, wins, total, tier = v
            emoji = ""
            if tier == "nuke":
                emoji = " ☢️"
            elif tier == "caution":
                emoji = " ⚠️"

            text += f"{league} – {p1} vs {p2} @ {est} EST / {pst} PST ({wins}/{total}){emoji}\n\n"

        msg2 = await message.channel.send(text.strip())
    else:
        msg2 = await message.channel.send("No 4+ plays found.")

    last_slate_messages.append(msg2)

    # Totals Header
    msg3 = await message.channel.send("🏓 **TOTAL PLAYS** 🏓")
    last_slate_messages.append(msg3)

    # Totals Body
    if totals:
        text = ""
        for v in totals.values():
            league, p1, p2, play, units, est, pst, wins, total = v
            text += f"{league} – {p1} vs {p2} {play} {format_units(units)} @ {est} EST / {pst} PST ({wins}/{total})\n\n"

        msg4 = await message.channel.send(text.strip())
    else:
        msg4 = await message.channel.send("No total plays found.")

    last_slate_messages.append(msg4)

    # Delete old slate after new one is sent
    for msg in old_messages:
        try:
            await msg.delete()
        except:
            pass

# ==============================
# RUN BOT
# ==============================

client.run(TOKEN)
