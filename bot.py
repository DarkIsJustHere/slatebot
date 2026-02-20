import discord
import os
import re

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Store last slate messages so we can delete them
current_slate = []


def process_csv(raw_text):
    four_plus = []
    totals = []

    lines = raw_text.splitlines()

    for line in lines:
        if not line.strip():
            continue

        # Try CSV-style first
        parts = [p.strip() for p in line.split(",")]

        if len(parts) >= 7:
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


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):

    if message.author == client.user:
        return

    # 🔒 ROLE RESTRICTION
    ALLOWED_ROLE = "RW Official"
    if not any(role.name == ALLOWED_ROLE for role in message.author.roles):
        return

    # 🔒 CHANNEL RESTRICTION
    ALLOWED_CHANNELS = [
        1474078126630768822,  # Main Server
        1471792196582637728   # Test Server
    ]

    if message.channel.id not in ALLOWED_CHANNELS:
        return

    # 🧪 HEALTH CHECK
    if message.content.strip().lower() == "ping":
        await message.channel.send("pong")
        return

    # 📎 CSV ATTACHMENT HANDLER
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(".csv"):

                file_bytes = await attachment.read()
                raw_text = file_bytes.decode("utf-8")

                try:
                    await message.delete()
                except:
                    pass

                global current_slate
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

                return

    # 🔥 MANUAL COMMAND FALLBACK
    if message.content.startswith("!slate"):

        raw_text = message.content.replace("!slate", "").strip()

        try:
            await message.delete()
        except:
            pass

        global current_slate
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
