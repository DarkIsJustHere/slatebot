# ============================================================
# 🔥 SLATEBOT v6.2 — OWNER CALIBRATED ENGINE
# ============================================================

import discord
import re
import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

current_slate = []


# ============================================================
# 📊 TOTALS UNIT SIZING (UNCHANGED)
# ============================================================

def calculate_units(percent):
    if percent < 80:
        return None
    elif percent < 85:
        return "1U"
    elif percent < 90:
        return "1.25U"
    elif percent < 93:
        return "1.5U"
    elif percent < 95:
        return "2U"
    else:
        return "2.5U"


# ============================================================
# 🧠 4+ CLASSIFICATION ENGINE v6.2
# ============================================================

def classify_4plus(percent, sample):

    # ☢️ NUKE LOGIC (Owner calibrated)
    if (
        (percent >= 92 and sample >= 50) or
        (percent >= 95 and sample >= 40) or
        (percent >= 90 and sample >= 65)
    ):
        return "☢️"

    # ⚠️ CAUTION LOGIC
    if (
        sample <= 22 or
        percent < 88 or
        (88 <= percent <= 91 and sample < 40)
    ):
        return "⚠️"

    return ""


# ============================================================
# 🏷 LEAGUE CLEANER
# ============================================================

def clean_league(name):
    name = name.upper()

    if "CZECH" in name:
        return "CZECH"
    if "SETKA" in name:
        return "SETKA"
    if "ELITE" in name:
        return "ELITE"
    if "CUP" in name:
        return "CUP"

    return name


# ============================================================
# 🧠 CSV PROCESSOR
# ============================================================

def process_csv(text):

    lines = text.split("\n")
    four_plus = []
    totals = []

    seen_matchups_4plus = set()
    seen_totals = set()

    for line in lines:

        if "League" in line or not line.strip():
            continue

        parts = line.split(",")

        if len(parts) < 7:
            continue

        league = clean_league(parts[0])

        time_pst = parts[1].split(" ")[1] + " " + parts[1].split(" ")[2]
        time_est = parts[2].split(" ")[1] + " " + parts[2].split(" ")[2]

        player1 = parts[3].strip()
        player2 = parts[4].strip()
        play_type = parts[5].strip()
        history = parts[6]

        history_match = re.search(r"\((\d+)/(\d+)\)", history)
        if not history_match:
            continue

        raw_left = int(history_match.group(1))
        sample = int(history_match.group(2))

        matchup_key = tuple(sorted([player1, player2]))

        # 4+ Logic
        if "4+ SET" in play_type:

            left = sample - raw_left
            percent = round((left / sample) * 100)

            emoji = classify_4plus(percent, sample)
            emoji_text = f" {emoji}" if emoji else ""

            formatted = (
                f"{league} – {player1} vs {player2}{emoji_text} "
                f"@ {time_est} EST / {time_pst} PST ({left}/{sample})"
            )

            four_plus.append(formatted)
            seen_matchups_4plus.add(matchup_key)

        # Totals Logic
        elif "UNDER" in play_type or "OVER" in play_type:

            if matchup_key in seen_matchups_4plus:
                continue

            left = raw_left
            percent = round((left / sample) * 100)

            units = calculate_units(percent)
            if not units:
                continue

            totals_key = (matchup_key, play_type)
            if totals_key in seen_totals:
                continue

            seen_totals.add(totals_key)

            formatted = (
                f"{league} – {player1} vs {player2} "
                f"{play_type} {units} "
                f"@ {time_est} EST / {time_pst} PST ({left}/{sample})"
            )

            totals.append(formatted)

    return four_plus, totals


# ============================================================
# 🚀 DISCORD EVENTS
# ============================================================

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):

    global current_slate

    if message.author == client.user:
        return

    if message.content.startswith("!slate"):

        raw_text = message.content.replace("!slate", "").strip()

        # Delete user message
        try:
            await message.delete()
        except:
            pass

        # Delete previous slate
        for old in current_slate:
            try:
                await old.delete()
            except:
                pass

        current_slate = []

        four_plus, totals = process_csv(raw_text)

        if four_plus:
            h1 = await message.channel.send("# 🔥 4+ PLAYS 🔥")
            b1 = await message.channel.send("\n\n".join(four_plus))
            current_slate.extend([h1, b1])

        if totals:
            h2 = await message.channel.send("# 🔥 TOTALS 🔥")
            b2 = await message.channel.send("\n\n".join(totals))
            current_slate.extend([h2, b2])

        if not current_slate:
            msg = await message.channel.send("No valid plays found.")
            current_slate.append(msg)

 
client.run(DISCORD_TOKEN)

