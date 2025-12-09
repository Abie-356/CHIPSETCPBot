import discord
from discord.ext import commands, tasks
import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ---------- Google Sheets Setup ----------
SHEET_ID = "1qPoJ0uBdVCQZMZYWRS6Bt60YjJnYUkD4OePSTRMiSrI"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

google_creds_json = os.getenv("GOOGLE_CREDS")

if google_creds_json:
    google_creds = json.loads(google_creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)

client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID)

registered_users = {}  # {discord_username: real_name}
submissions_today = {}  # {discord_username: count}

def is_valid_day_sheet(title):
    try:
        datetime.datetime.strptime(title, "%Y-%m-%d")
        return True
    except:
        return False

def load_users():
    try:
        reg_sheet = sheet.worksheet("Registered_Users")
    except:
        reg_sheet = sheet.add_worksheet(title="Registered_Users", rows=200, cols=2)
        reg_sheet.append_row(["Discord Username", "Real Name"])
        return
    
    rows = reg_sheet.get_all_values()[1:]
    for row in rows:
        if len(row) >= 2:
            registered_users[row[0]] = row[1]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

def get_today_sheet():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        ws = sheet.worksheet(today)
    except:
        ws = sheet.add_worksheet(title=today, rows=200, cols=4)
        ws.append_row(["Date", "Username", "Screenshot", "Problem Name"])
    return ws


@bot.event
async def on_ready():
    load_users()
    print(f"Bot Ready ✔: {bot.user}")
    daily_reminder.start()


# ---------- Register ----------
@bot.command()
async def register(ctx):
    if ctx.guild is not None:
        return await ctx.reply("📩 DM me to register!")

    uname = ctx.author.name

    if uname in registered_users:
        return await ctx.reply("Already registered 🤝")

    await ctx.reply("Send your REAL FULL NAME 👇")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", timeout=60, check=check)
        real_name = msg.content.strip()
        registered_users[uname] = real_name

        reg_sheet = sheet.worksheet("Registered_Users")
        reg_sheet.append_row([uname, real_name])
        await ctx.reply(f"✔ Registered Successfully {real_name} 🎯")

    except:
        await ctx.reply("⏳ Timeout! Try /register again.")


# ---------- Submit ----------
@bot.command()
async def submit(ctx, *, problem_name="No Name"):
    if ctx.guild is not None:
        return await ctx.reply("Submit privately here 😄")

    uname = ctx.author.name

    if uname not in registered_users:
        return await ctx.reply("❌ Register first using `/register`")

    if not ctx.message.attachments:
        return await ctx.reply("⚠️ Attach screenshot also!")

    submissions_today[uname] = submissions_today.get(uname, 0) + 1

    ws = get_today_sheet()
    ws.append_row([
        str(datetime.datetime.now().date()),
        uname,
        ctx.message.attachments[0].url,
        problem_name
    ])

    await ctx.reply(f"🔥 Submission #{submissions_today[uname]} saved!")


# ---------- Status ----------
@bot.command()
async def status(ctx):
    if ctx.guild is not None:
        return await ctx.reply("DM me 😄")

    uname = ctx.author.name
    count = submissions_today.get(uname, 0)

    if count > 0:
        await ctx.reply(f"✔ You submitted {count} time(s) today! 🔥")
    else:
        await ctx.reply("❌ No submissions yet today 😬")


# ---------- Not Completed Today (Admin Only) ----------
@bot.command()
async def notcompleted(ctx):
    if ctx.guild is None:
        return await ctx.reply("Use this in server 😄")

    if not ctx.author.guild_permissions.administrator:
        return await ctx.reply("❌ Admin only!")

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    try:
        today_ws = sheet.worksheet(today)
    except:
        return await ctx.reply("⚠️ Nobody submitted today 😅")

    submitted = set(today_ws.col_values(2)[1:])
    not_done = [
        registered_users[u] for u in registered_users
        if u not in submitted
    ]

    if not not_done:
        return await ctx.reply("🎉 Everyone completed today!")

    result = "\n".join(f"• {name}" for name in not_done)
    await ctx.reply(f"❌ Pending Submissions:\n\n{result}")


# ---------- Daily DM Reminder ----------
@tasks.loop(time=datetime.time(hour=22, minute=0))
async def daily_reminder():
    for uname in registered_users:
        if uname not in submissions_today:
            user = discord.utils.get(bot.users, name=uname)
            if user:
                try:
                    await user.send("⏲️ Reminder: Submit today's CP!")
                except:
                    pass
    submissions_today.clear()


TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
