import discord
import re
import os
from datetime import datetime, timedelta, timezone

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("No TOKEN found.")

ALLOWED_CHANNELS = [
1471792196582637728,
1474078126630768822,
1479241150996152340
]

FOUR_PLUS_CHANNEL = 1443356395935240302
TOTALS_CHANNEL = 1446203029916356649
TEST_CHANNEL = 1471792196582637728

EST = timezone(timedelta(hours=-5))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


# ==============================
# 4+ PARSER
# ==============================

async def parse_four_plus(channel,start,end,limit=None):

    wins=0
    losses=0
    washes=0

    normal_w=0
    normal_l=0

    nuke_w=0
    nuke_l=0

    caution_w=0
    caution_l=0

    seen=set()

    async for msg in channel.history(limit=limit):

        msg_time = msg.created_at.astimezone(EST)

        if start and not(start<=msg_time<end):
            continue

        for line in msg.content.split("\n"):

            line=line.strip()

            if "vs" not in line:
                continue

            if "U @" in line or "U@" in line:
                continue

            if line in seen:
                continue

            seen.add(line)

            is_nuke="☢️" in line
            is_caution="⚠️" in line

            if "🧼" in line:
                washes+=1
                continue

            if "✅" in line:

                wins+=1

                if is_nuke:
                    nuke_w+=1
                elif is_caution:
                    caution_w+=1
                else:
                    normal_w+=1

            elif "❌" in line:

                losses+=1

                if is_nuke:
                    nuke_l+=1
                elif is_caution:
                    caution_l+=1
                else:
                    normal_l+=1

    return wins,losses,washes,normal_w,normal_l,caution_w,caution_l,nuke_w,nuke_l


# ==============================
# TOTALS PARSER
# ==============================

async def parse_totals(channel,start,end,limit=None):

    wins=0
    losses=0
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
                units+=stake/1.2

            elif "❌" in line:

                losses+=1
                units-=stake

            elif "🪝" in line:

                losses+=1
                units-=stake

    return wins,losses,units


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):

    if message.author.bot:
        return

    content = message.content.lower().strip()

# ==============================
# RECAP COMMANDS
# ==============================

    if content.startswith("!recap"):

        now=datetime.now(EST)

        if "test" in content:

            start=None
            end=None
            limit=50
            title=f"TEST RECAP — {now.strftime('%b')} {now.day} (EST)"

        elif "daily" in content:

            start=(now-timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
            end=start+timedelta(days=1)

            title=f"DAILY RECAP — {start.strftime('%b')} {start.day} (EST)"
            limit=None

        elif "monthly" in content:

            start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
            end=now

            title=f"MONTHLY RECAP — {now.strftime('%b %Y')}"
            limit=None

        else:
            return

        if message.channel.id==TEST_CHANNEL:
            four_channel=message.channel
            totals_channel=message.channel
        else:
            four_channel=client.get_channel(FOUR_PLUS_CHANNEL)
            totals_channel=client.get_channel(TOTALS_CHANNEL)

        fw,fl,fwash,nw,nl,cw,cl,kw,kl=await parse_four_plus(four_channel,start,end,limit)
        tw,tl,tunits=await parse_totals(totals_channel,start,end,limit)

        four_units=(fw*1.1)-(fl*3)

        recap=f"📊 **{title}**\n\n"

        recap+="🏓 **4+ PLAYS**\n"
        recap+=f"Record: {fw}-{fl}"

        if fwash>0:
            recap+=f" ({fwash} Wash)"

        recap+=f"\nUnits: {four_units:+.2f}U\n\n"

        recap+=f"Normal {nw}-{nl}\n"
        recap+=f"⚠️ {cw}-{cl}\n"
        recap+=f"☢️ {kw}-{kl}\n\n"

        recap+="🏓 **TOTAL PLAYS**\n"

        if tw+tl==0:
            recap+="No plays graded."
        else:
            recap+=f"Record: {tw}-{tl}\n"
            recap+=f"Units: {tunits:+.2f}U"

        await message.channel.send(recap)
        return


    if message.channel.id not in ALLOWED_CHANNELS:
        return

    if content=="ping":
        await message.channel.send("pong")
        return


client.run(TOKEN)
