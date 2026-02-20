import discord
import os
import csv
from io import StringIO

TOKEN = os.getenv("DISCORD_TOKEN")

RW_ROLE_NAME = "RW Official"
ALLOWED_CHANNEL_IDS = [
    1471792196582637728,  # test
    # add main channel ID here if needed
]

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

    if (pct >= 0.93 and total >= 40) or (pct >= 0.95 and total >= 30):
        return "nuke"

    if total <= 25 and 18 <= wins <= 22:
        return "caution"

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
    if "setka" in league:
        return "SETKA"
    if "cup" in league and "setka" not in league:
        return "CUP"
    if "czech" in league:
        return "CZECH"

    return league.upper()


# ==============================
# READY
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
    if message.channel.id not in ALLOWED_CHANNEL_IDS:
        return

    # Role restriction
    if not any(role.name == RW_ROLE_NAME for role in message.author.roles):
        return

    # Ping test
    if message.content.strip().lower() == "ping":
        await message.channel.send("pong")
        return

    if not message.attachments:
        return

    # Find CSV attachment
    csv_attachment = None
    for attachment in message.attachments:
        if ".csv" in attachment.filename.lower():
            csv_attachment = attachment
            break

    if not csv_attachment:
        return

    try:
        file_bytes = await csv_attachment.read()
        file_text = file_bytes.decode("utf-8", errors="ignore").lstrip("\ufeff")
    except:
        return

    try:
        reader = csv.DictReader(StringIO(file_text))
    except:
        return

    four_plus = {}
    totals = {}

    for row in reader:

        try:
            league = normalize_league(row.get("League", ""))
            pst_time_raw = row.get("Time (Pacific)", "")
            est_time_raw = row.get("Time (Eastern)", "")
            p1 = row.get("Player 1", "")
            p2 = row.get("Player 2", "")
            play = row.get("Play", "")
            history = row.get("History", "")
        except:
            continue

        if not history or "(" not in history:
            continue

        try:
            wins = int(history.split("(")[1].split("/")[0])
            total = int(history.split("/")[1].split(")")[0])
        except:
            continue

        pst_time = pst_time_raw.split(" ")[1] if " " in pst_time_raw else pst_time_raw
        est_time = est_time_raw.split(" ")[1] if " " in est_time_raw else est_time_raw

        key = f"{league}-{p1}-{p2}-{est_time}"

        # 4+ SET
        if "4+" in play:
            if key not in four_plus:
                classification = classify_4plus(wins, total)
                four_plus[key] = (
                    league, p1, p2, est_time, pst_time, wins, total, classification
                )

        # TOTALS
        if play in ["OVER", "UNDER"]:
            if key not in four_plus:
                units = get_totals_units(wins, total)
                totals[key] = (
                    league, p1, p2, play, units, est_time, pst_time, wins, total
                )

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

            output += (
                f"{league} – {p1} vs {p2} @ "
                f"{est} EST / {pst} PST "
                f"({wins}/{total}){emoji}\n\n"
            )

    if totals:
        output += "TOTALS 🔥\n"
        for v in totals.values():
            league, p1, p2, play, units, est, pst, wins, total = v

            output += (
                f"{league} – {p1} vs {p2} {play} "
                f"{format_units(units)} @ "
                f"{est} EST / {pst} PST "
                f"({wins}/{total})\n\n"
            )

    if output:
        try:
            await message.delete()
        except:
            pass

        await message.channel.send(output.strip())


client.run(TOKEN)
