import discord
import os
import csv
import re
from io import StringIO

TOKEN = os.getenv("DISCORD_TOKEN")

RW_ROLE_NAME = "RW Official"
ALLOWED_CHANNEL_IDS = [
    1471792196582637728,  # test channel
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)


# =============================
# SAFE RECORD EXTRACTION
# =============================
def extract_record(history):
    match = re.search(r"\((\d+)/(\d+)\)", history)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


# =============================
# 4+ CLASSIFICATION
# =============================
def classify_4plus(wins, total):
    if total == 0:
        return "normal"

    pct = wins / total

    # Nuke
    if pct >= 0.93 and total >= 40:
        return "nuke"

    # Caution = volatile mid tier small samples
    if total < 30 and 0.85 <= pct < 0.91:
        return "caution"

    return "normal"


# =============================
# TOTALS UNIT SIZING
# =============================
def get_totals_units(wins, total):
    if total == 0:
        return 1

    pct = round(wins / total, 4)

    if total >= 30:
        if pct >= 0.95:
            return 2.5
        elif pct >= 0.91:
            return 2
        elif pct >= 0.86:
            return 1.5
        elif pct >= 0.81:
            return 1.25
        else:
            return 1
    else:
        if pct >= 0.95:
            return 2
        elif pct >= 0.91:
            return 1.75
        elif pct >= 0.86:
            return 1.5
        elif pct >= 0.81:
            return 1.25
        else:
            return 1


def format_units(u):
    if float(u).is_integer():
        return f"{int(u)}U"
    return f"{u}U"


# =============================
# LEAGUE CLEANUP
# =============================
def normalize_league(name):
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


# =============================
# READY
# =============================
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


# =============================
# MESSAGE HANDLER
# =============================
@client.event
async def on_message(message):

    if message.author == client.user:
        return

    if message.channel.id not in ALLOWED_CHANNEL_IDS:
        return

    if not any(role.name == RW_ROLE_NAME for role in message.author.roles):
        return

    if message.content.lower().strip() == "ping":
        await message.channel.send("pong")
        return

    if not message.attachments:
        return

    csv_file = None
    for attachment in message.attachments:
        if attachment.filename.lower().endswith(".csv"):
            csv_file = attachment
            break

    if not csv_file:
        return

    file_bytes = await csv_file.read()
    file_text = file_bytes.decode("utf-8", errors="ignore").lstrip("\ufeff")

    reader = csv.DictReader(StringIO(file_text))

    four_plus = {}
    totals = {}

    for row in reader:

        league = normalize_league(row.get("League", "").strip())
        pst_time = row.get("Time (Pacific)", "").strip()
        est_time = row.get("Time (Eastern)", "").strip()
        p1 = row.get("Player 1", "").strip()
        p2 = row.get("Player 2", "").strip()
        play = row.get("Play", "").strip().upper()
        history = row.get("History", "").strip()

        wins_raw, total = extract_record(history)
        if wins_raw is None:
            continue

        # Clean time (remove date but keep AM/PM)
        if " " in pst_time:
            pst_time = pst_time.split(" ", 1)[1]
        if " " in est_time:
            est_time = est_time.split(" ", 1)[1]

        key = f"{league}-{p1}-{p2}-{est_time}"

        # =============================
        # 4+ HANDLING
        # =============================
        if "4+" in play:

            # Convert sweep rate → 4+ wins
            wins = total - wins_raw

            if key not in four_plus:
                tier = classify_4plus(wins, total)
                four_plus[key] = (
                    league, p1, p2, est_time, pst_time,
                    wins, total, tier
                )

            continue

        # =============================
        # TOTALS HANDLING
        # =============================
        if play in ["OVER", "UNDER"]:

            # Only skip if TRUE same matchup has 4+
            if key in four_plus:
                continue

            units = get_totals_units(wins_raw, total)

            totals[key] = (
                league, p1, p2, play,
                units, est_time, pst_time,
                wins_raw, total
            )

    # =============================
    # BUILD OUTPUT
    # =============================
    output = ""

    if four_plus:
        output += "4+ PLAYS 🔥\n\n"
        for v in four_plus.values():
            league, p1, p2, est, pst, wins, total, tier = v

            emoji = ""
            if tier == "nuke":
                emoji = " ☢️"
            elif tier == "caution":
                emoji = " ⚠️"

            output += (
                f"{league} – {p1} vs {p2} @ "
                f"{est} EST / {pst} PST "
                f"({wins}/{total}){emoji}\n\n"
            )

    if totals:
        output += "TOTALS 🔥\n\n"
        for v in totals.values():
            league, p1, p2, play, units, est, pst, wins, total = v

            output += (
                f"{league} – {p1} vs {p2} {play} "
                f"{format_units(units)} @ "
                f"{est} EST / {pst} PST "
                f"({wins}/{total})\n\n"
            )

    if output:
        await message.delete()
        await message.channel.send(output.strip())


client.run(TOKEN)
