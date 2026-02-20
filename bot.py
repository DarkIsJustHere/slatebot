import discord
import os
import csv
from io import StringIO

TOKEN = os.getenv("DISCORD_TOKEN")

RW_ROLE_NAME = "RW Official"
ALLOWED_CHANNEL_ID = 1471792196582637728  # ← change if needed

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)


# ==============================
# 4+ CLASSIFICATION (LOCKED)
# ==============================
def classify_4plus(wins, total):
    if total == 0:
        return "normal"

    pct = wins / total

    # ☢️ NUKE
    if (pct >= 0.93 and total >= 40) or (pct >= 0.95 and total >= 30):
        return "nuke"

    # ⚠️ Small sample strong band
    if total <= 25 and 18 <= wins <= 22:
        return "caution"

    # ⚠️ Mid tier consistency band
    if 0.83 <= pct <= 0.89 and total >= 25:
        return "caution"

    return "normal"


# ==============================
# TOTALS UNIT SIZING
# ==============================
def get_totals_units(wins, total):
    if total == 0:
        return 1.0

    pct = wins / total

    if total >= 30:
        if pct >= 0.95:
            return 2.5
        elif pct >= 0.91:
            return 2.0
        elif pct >= 0.86:
            return 1.5
        elif pct >= 0.81:
            return 1.25
        else:
            return 1.0
    else:
        if pct >= 0.95:
            return 2.0
        elif pct >= 0.91:
            return 1.75
        elif pct >= 0.86:
            return 1.5
        elif pct >= 0.81:
            return 1.25
        else:
            return 1.0


def format_units(u):
    if u == int(u):
        return f"{int(u)}U"
    return f"{u}U"


# ==============================
# LEAGUE NORMALIZATION
# ==============================
def normalize_league(league):
    league = league.lower()
    if "elite" in league:
        return "ELITE"
    if "cup" in league and "setka" not in league:
        return "CUP"
    if "setka" in league:
        return "SETKA"
    if "czech" in league:
        return "CZECH"
    return league.upper()


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

    if message.author == client.user:
        return

    # Channel restriction
    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    # Role restriction
    if not any(role.name == RW_ROLE_NAME for role in message.author.roles):
        return

    # Ping test
    if message.content.strip().lower() == "ping":
        await message.channel.send("pong")
        return

    # CSV detection
    if not message.attachments:
        return

    attachment = message.attachments[0]

    if not attachment.filename.endswith(".csv"):
        return

    file_bytes = await attachment.read()
    file_text = file_bytes.decode("utf-8")

    reader = csv.DictReader(StringIO(file_text))

    four_plus = {}
    totals = {}

    for row in reader:
        league = normalize_league(row["League"])
        pst_time = row["Time (Pacific)"].split(" ")[1]
        est_time = row["Time (Eastern)"].split(" ")[1]
        p1 = row["Player 1"]
        p2 = row["Player 2"]
        play = row["Play"]

        history = row["History"]
        wins = int(history.split("(")[1].split("/")[0])
        total = int(history.split("/")[1].split(")")[0])

        key = f"{league}-{p1}-{p2}-{est_time}"

        # 4+ SET
        if "4+" in play:
            if key not in four_plus:
                classification = classify_4plus(wins, total)
                four_plus[key] = (league, p1, p2, est_time, pst_time, wins, total, classification)

        # TOTALS
        if play in ["OVER", "UNDER"]:
            if key not in four_plus:  # 4+ overrides totals
                units = get_totals_units(wins, total)
                totals[key] = (league, p1, p2, play, units, est_time, pst_time, wins, total)

    # ==============================
    # BUILD OUTPUT
    # ==============================
    output = ""

    if four_plus:
        output += "4+ PLAYS 🔥\n"
        for v in four_plus.values():
            league, p1, p2, est, pst, wins, total, classification = v

            emoji = ""
            if classification == "nuke":
                emoji = " ☢️"
            elif classification == "caution":
                emoji = " ⚠️"

            output += f"{league} – {p1} vs {p2} @ {est} EST / {pst} PST ({wins}/{total}){emoji}\n\n"

    if totals:
        output += "TOTALS 🔥\n"
        for v in totals.values():
            league, p1, p2, play, units, est, pst, wins, total = v
            output += f"{league} – {p1} vs {p2} {play} {format_units(units)} @ {est} EST / {pst} PST ({wins}/{total})\n\n"

    if output:
        await message.delete()
        await message.channel.send(output.strip())


client.run(TOKEN)
