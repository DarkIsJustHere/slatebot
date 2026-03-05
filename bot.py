import discord
import csv
import io
import re
import os
from datetime import datetime, timedelta, timezone

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("No TOKEN found.")

# ==============================
# CHANNELS
# ==============================

ALLOWED_CHANNELS = [
    1471792196582637728,
    1474078126630768822,
    1479241150996152340
]

FOUR_PLUS_CHANNEL = 1443356395935240302
TOTALS_CHANNEL = 1446203029916356649

TEST_CHANNEL = 1471792196582637728

EST = timezone(timedelta(hours=-5))

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
    if u == 1: return "1U"
    if u == 1.25: return "1.25U"
    if u == 1.5: return "1.5U"
    if u == 1.75: return "1.75U"
    if u == 2: return "2U"
    if u == 2.5: return "2.5U"
    if u == 3: return "3U"
    return f"{u}U"

def convert_league(name):
    name = name.lower()
    if "elite" in name: return "ELITE"
    if "setka" in name: return "SETKA"
    if "czech" in name: return "CZECH"
    if "cup" in name: return "CUP"
    return name.upper()

def parse_time(est_time):
    dt = datetime.strptime(est_time,"%m/%d %I:%M %p")
    est = dt.strftime("%I:%M %p")
    pst_dt = dt.replace(hour=(dt.hour-3)%24)
    pst = pst_dt.strftime("%I:%M %p")
    return est,pst

# ==============================
# RECAP PARSERS
# ==============================

async def parse_four_plus(channel,start,end,limit=None):

    wins=0
    losses=0
    washes=0
    seen=set()

    async for msg in channel.history(limit=limit):

        msg_time = msg.created_at.astimezone(EST)

        if start and not(start<=msg_time<end):
            continue

        for line in msg.content.split("\n"):

            line=line.strip()

            if "vs" not in line:
                continue

            if line in seen:
                continue

            seen.add(line)

            if "✅" in line:
                wins+=1
            elif "❌" in line:
                losses+=1
            elif "🧼" in line:
                washes+=1

    units=(wins*1.1)-(losses*3)

    return wins,losses,washes,units

async def parse_totals(channel,start,end,limit=None):

    wins=0
    losses=0
    hooks=0
    units=0
    seen=set()

    async for msg in channel.history(limit=limit):

        msg_time = msg.created_at.astimezone(EST)

        if start and not(start<=msg_time<end):
            continue

        for line in msg.content.split("\n"):

            line=line.strip()

            if "vs" not in line:
                continue

            if line in seen:
                continue

            seen.add(line)

            unit_match=re.search(r'(\d+(\.\d+)?)U',line,re.IGNORECASE)

            if not unit_match:
                continue

            stake=float(unit_match.group(1))

            if "✅" in line:
                wins+=1
                units+=stake
            elif "❌" in line:
                losses+=1
                units-=stake
            elif "🪝" in line:
                hooks+=1

    return wins,losses,hooks,units

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

# ==============================
# RECAP COMMANDS
# ==============================

    if message.content.lower().startswith("!recap"):

        now=datetime.now(EST)

        if "test" in message.content.lower():

            start=None
            end=None
            limit=50
            title="TEST"

        elif "daily" in message.content.lower():

            start=(now-timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
            end=start+timedelta(days=1)
            limit=None
            title="DAILY"

        elif "monthly" in message.content.lower():

            start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
            end=now
            limit=None
            title="MONTHLY"

        else:
            return

        if message.channel.id==TEST_CHANNEL:
            four_channel=message.channel
            totals_channel=message.channel
        else:
            four_channel=client.get_channel(FOUR_PLUS_CHANNEL)
            totals_channel=client.get_channel(TOTALS_CHANNEL)

        fw,fl,fwash,funits=await parse_four_plus(four_channel,start,end,limit)
        tw,tl,thook,tunits=await parse_totals(totals_channel,start,end,limit)

        recap=f"📊 **{title} RECAP (EST)**\n\n"

        recap+="🏓 **4+ PLAYS**\n"

        if fw+fl+fwash==0:
            recap+="No plays graded.\n\n"
        else:
            recap+=f"Record: {fw}-{fl}"
            if fwash>0:
                recap+=f" ({fwash} Wash)"
            recap+=f"\nUnits: {funits:+.2f}U\n\n"

        recap+="🏓 **TOTAL PLAYS**\n"

        if tw+tl+thook==0:
            recap+="No plays graded."
        else:
            recap+=f"Record: {tw}-{tl}"
            if thook>0:
                recap+=f" ({thook} Hook)"
            recap+=f"\nUnits: {tunits:+.2f}U"

        await message.channel.send(recap)
        return

# ==============================
# ORIGINAL CHANNEL FILTER
# ==============================

    if message.channel.id not in ALLOWED_CHANNELS:
        return

    if message.content.lower()=="ping":
        await message.channel.send("pong")
        return

client.run(TOKEN)
