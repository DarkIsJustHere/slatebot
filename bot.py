import discord
import os
import re

# ==============================
# CONFIG
# ==============================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

ALLOWED_ROLE = "RW Official"

ALLOWED_CHANNELS = [
    1474078126630768822,  # Main Server Channel
    1471792196582637728   # Test Server Channel
]

# ==============================
# DISCORD SETUP
# ==============================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# Store last slate messages
current_slate_messages = []

# ==============================
# CSV PROCESSING
# ==============================

def process_csv(raw_text):
    four_plus = []
    totals = []

    lines = raw_text.splitlines()

    for line in lines:
        if not line.strip():
            continue

        parts = [p.strip() for p in line.split(",")]

        if len(parts) < 7:
            continue

        league = parts[0].replace("TT ", "").replace("Liga Pro", "").strip().upper()
        time_pst = parts[1]
        time_est = parts[2]
        player1 = parts[3]
        player2 = parts[4]
        play_type = parts[5]
        history = parts[6]

        match = re.search(r"\((\d+)/(\d+)\)", history)
        if not match:
            continue

        left = int(match.group(1))
        right = int(match.group(2))

        # Subtract left from right
        new_left = right - left

        formatted = f"{league} – {player1} vs {player2} @ {time_est} / {time_pst} ({new_left}/{right})"

        percentage = new_left / right

        emoji = ""
        if percentage >= 0.95:
            emoji = " ☢️"
        elif percentage <= 0.85:
            emoji = " ⚠️"

        if "4+" in play_type.upper():
            four_plus.append(formatted + emoji)
        elif "OVER" in play_type.upper() or "UNDER" in play_type.upper():
            totals.append(formatted + emoji)

    return four_plus, totals

# ==============================
# EVENTS
# ==============================

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    global current_slate_messages

    # Ignore bot messages
    if message.author == client.user:
        return

    # Role restriction
    if not any(role.name == ALLOWED_ROLE for role in message.author.roles):
        return

    # Channel restriction
    if message.channel.id not in ALLOWED_CHANNELS:
        return

    # Health check
    if message.content.strip().lower() == "ping":
        await message.channel.send("pong")
        return

    # ==============================
    # CSV ATTACHMENT HANDLER
    # ==============================
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(".csv"):

                file_bytes = await attachment.read()
                raw_text = file_bytes.decode("utf-8")

                # Delete user message
                try:
                    await message.delete()
                except:
                    pass

                # Delete previous slate
                for old_msg in current_slate_messages:
                    try:
                        await old_msg.delete()
                    except:
                        pass

                current_slate_messages = []

                four_plus, totals = process_csv(raw_text)

                if four_plus:
                    header = await message.channel.send("# 🔥 4+ PLAYS 🔥")
                    body = await message.channel.send("\n\n".join(four_plus))
                    current_slate_messages.extend([header, body])

                if totals:
                    header = await message.channel.send("# 🔥 TOTALS 🔥")
                    body = await message.channel.send("\n\n".join(totals))
                    current_slate_messages.extend([header, body])

                return

    # ==============================
    # MANUAL !slate FALLBACK
    # ==============================
    if message.content.startswith("!slate"):

        raw_text = message.content.replace("!slate", "").strip()

        # Delete user message
        try:
            await message.delete()
        except:
            pass

        # Delete previous slate
        for old_msg in current_slate_messages:
            try:
                await old_msg.delete()
            except:
                pass

        current_slate_messages = []

        four_plus, totals = process_csv(raw_text)

        if four_plus:
            header = await message.channel.send("# 🔥 4+ PLAYS 🔥")
            body = await message.channel.send("\n\n".join(four_plus))
            current_slate_messages.extend([header, body])

        if totals:
            header = await message.channel.send("# 🔥 TOTALS 🔥")
            body = await message.channel.send("\n\n".join(totals))
            current_slate_messages.extend([header, body])

        if not four_plus and not totals:
            msg = await message.channel.send("No valid plays found.")
            current_slate_messages.append(msg)

# ==============================
# RUN BOT
# ==============================

client.run(DISCORD_TOKEN)
