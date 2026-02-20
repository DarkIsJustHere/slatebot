import discord
import os
import re

# =========================
# CONFIG
# =========================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_ROLE = "RW Official"

ALLOWED_CHANNELS = [
    1474078126630768822,  # Main
    1471792196582637728   # Test
]

# =========================
# DISCORD SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

current_slate_messages = []

# =========================
# HELPER FUNCTIONS
# =========================

def normalize_league(raw):
    raw = raw.upper()
    if "ELITE" in raw:
        return "ELITE"
    if "SETKA" in raw:
        return "SETKA"
    if "CUP" in raw:
        return "CUP"
    if "CZECH" in raw:
        return "CZECH"
    return raw

def strip_date(time_str):
    # Removes 02/20 from 02/20 7:45 AM
    parts = time_str.split(" ")
    if len(parts) >= 2:
        return " ".join(parts[1:])
    return time_str

def calculate_units(percentage, sample_size):
    # Sample scaling logic

    if sample_size >= 30:
        if percentage >= 0.95:
            return 3
        elif percentage >= 0.93:
            return 2.5
        elif percentage >= 0.90:
            return 2
        elif percentage >= 0.85:
            return 1.5
        elif percentage >= 0.81:
            return 1.25
        else:
            return 1
    else:
        # More conservative for <30
        if percentage >= 0.95:
            return 2
        elif percentage >= 0.90:
            return 1.75
        elif percentage >= 0.85:
            return 1.5
        elif percentage >= 0.80:
            return 1.25
        else:
            return 1

# =========================
# CSV PROCESSING
# =========================

def process_csv(raw_text):
    four_plus = []
    totals = []
    seen_matchups = set()

    lines = raw_text.splitlines()

    for line in lines:
        if not line.strip():
            continue

        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue

        league_raw = parts[0]
        time_pst_raw = parts[1]
        time_est_raw = parts[2]
        player1 = parts[3]
        player2 = parts[4]
        play_type = parts[5]
        history = parts[6]

        league = normalize_league(league_raw)
        time_est = strip_date(time_est_raw)
        time_pst = strip_date(time_pst_raw)

        match = re.search(r"\((\d+)/(\d+)\)", history)
        if not match:
            continue

        left = int(match.group(1))
        right = int(match.group(2))

        matchup_key = f"{league}-{player1}-{player2}-{time_est}"

        # ================= 4+ LOGIC =================
        if "4+" in play_type.upper():

            new_left = right - left
            percentage = new_left / right if right > 0 else 0

            emoji = ""
            if right >= 30 and percentage >= 0.95:
                emoji = " ☢️"
            elif right >= 20 and percentage <= 0.80:
                emoji = " ⚠️"

            formatted = f"{league} – {player1} vs {player2}{emoji} @ {time_est} EST / {time_pst} PST ({new_left}/{right})"

            if matchup_key not in seen_matchups:
                four_plus.append(formatted)
                seen_matchups.add(matchup_key)

        # ================= TOTALS LOGIC =================
        elif "OVER" in play_type.upper() or "UNDER" in play_type.upper():

            if matchup_key in seen_matchups:
                continue  # prioritize 4+

            percentage = left / right if right > 0 else 0
            units = calculate_units(percentage, right)

            formatted = f"{league} – {player1} vs {player2} {play_type.upper()} {units}U @ {time_est} EST / {time_pst} PST ({left}/{right})"

            totals.append(formatted)

    return four_plus, totals

# =========================
# EVENTS
# =========================

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    global current_slate_messages

    if message.author == client.user:
        return

    if not any(role.name == ALLOWED_ROLE for role in message.author.roles):
        return

    if message.channel.id not in ALLOWED_CHANNELS:
        return

    if message.content.strip().lower() == "ping":
        await message.channel.send("pong")
        return

    # CSV Upload
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(".csv"):

                file_bytes = await attachment.read()
                raw_text = file_bytes.decode("utf-8")

                try:
                    await message.delete()
                except:
                    pass

                for old in current_slate_messages:
                    try:
                        await old.delete()
                    except:
                        pass

                current_slate_messages = []

                four_plus, totals = process_csv(raw_text)

                if four_plus:
                    h1 = await message.channel.send("## 🔥 4+ PLAYS 🔥")
                    b1 = await message.channel.send("\n\n".join(four_plus))
                    current_slate_messages.extend([h1, b1])

                if totals:
                    h2 = await message.channel.send("## 🔥 TOTALS 🔥")
                    b2 = await message.channel.send("\n\n".join(totals))
                    current_slate_messages.extend([h2, b2])

                return

client.run(DISCORD_TOKEN)
