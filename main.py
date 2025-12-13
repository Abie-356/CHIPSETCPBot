import discord
from discord.ext import commands, tasks
import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests
import tempfile

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ------------------ GOOGLE SHEETS ------------------
SHEET_ID = "1qPoJ0uBdVCQZMZYWRS6Bt60YjJnYUkD4OePSTRMiSrI"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

google_creds_json = os.getenv("GOOGLE_CREDS")

if google_creds_json:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(google_creds_json), scope
    )
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "service_account.json", scope
    )

client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID)

# ------------------ GOOGLE DRIVE ------------------
drive_service = build("drive", "v3", credentials=creds)
DRIVE_FOLDER_ID = "1_5_PPNN9YLOOC00Z-Wg1uhmDKfcglN5G"

def upload_image_to_drive(url, filename):
    r = requests.get(url)
    r.raise_for_status()

    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(r.content)
    temp.close()

    media = MediaFileUpload(temp.name, resumable=True)
    file = drive_service.files().create(
        body={"name": filename, "parents": [DRIVE_FOLDER_ID]},
        media_body=media,
        fields="id"
    ).execute()

    drive_service.permissions().create(
        fileId=file["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()

    os.unlink(temp.name)
    return f"https://drive.google.com/file/d/{file['id']}/view"

# ------------------ BOT STATE ------------------
registered_users = {}        # {discord_username: real_name}
submissions_today = {}       # {discord_username: count}

# ------------------ BOT SETUP ------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

def get_today_sheet():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        return sheet.worksheet(today)
    except:
        ws = sheet.add_worksheet(title=today, rows=200, cols=4)
        ws.append_row(["Date", "Username", "Screenshot Link", "Problem Name"])
        return ws

def load_users():
    try:
        reg = sheet.worksheet("Registered_Users")
    except:
        reg = sheet.add_worksheet("Registered_Users", 200, 2)
        reg.append_row(["Discord Username", "Real Name"])
        return

    for r in reg.get_all_values()[1:]:
        registered_users[r[0]] = r[1]

@bot.event
async def on_ready():
    load_users()
    print(f"Bot online ✔ {bot.user}")
    daily_reminder.start()

# ------------------ REGISTER ------------------
@bot.command()
async def register(ctx):
    if ctx.guild:
        return await ctx.reply("📩 DM me to register")

    uname = ctx.author.name
    if uname in registered_users:
        return await ctx.reply("Already registered 🤝")

    await ctx.reply("Send your **FULL REAL NAME**")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    msg = await bot.wait_for("message", timeout=60, check=check)
    real_name = msg.content.strip()

    registered_users[uname] = real_name
    sheet.worksheet("Registered_Users").append_row([uname, real_name])

    await ctx.reply(f"✅ Registered: {real_name}")

# ------------------ SUBMIT ------------------
@bot.command()
async def submit(ctx, *, problem_name="No Name"):
    if ctx.guild:
        return await ctx.reply("Submit in DM only 😄")

    uname = ctx.author.name
    if uname not in registered_users:
        return await ctx.reply("❌ Register first")

    if not ctx.message.attachments:
        return await ctx.reply("⚠️ Attach screenshot")

    await ctx.reply("📤 Uploading...")

    attachment = ctx.message.attachments[0]
    filename = f"{uname}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    drive_link = upload_image_to_drive(attachment.url, filename)

    submissions_today[uname] = submissions_today.get(uname, 0) + 1

    ws = get_today_sheet()
    ws.append_row([
        str(datetime.datetime.now().date()),
        uname,
        drive_link,
        problem_name
    ])

    await ctx.reply("✅ Submission saved (permanent link)")

# ------------------ STATUS ------------------
@bot.command()
async def status(ctx):
    if ctx.guild:
        return await ctx.reply("DM me")

    count = submissions_today.get(ctx.author.name, 0)
    await ctx.reply(f"🔥 Submissions today: {count}")

# ------------------ NOT COMPLETED ------------------
@bot.command()
async def notcompleted(ctx):
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        return await ctx.reply("Admin only")

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    ws = sheet.worksheet(today)

    submitted = set(ws.col_values(2)[1:])
    pending = [
        real for uname, real in registered_users.items()
        if uname not in submitted
    ]

    if not pending:
        return await ctx.reply("🎉 Everyone submitted!")

    await ctx.reply("❌ Not submitted:\n" + "\n".join(pending))

# ------------------ SUMMARY ------------------
@bot.command()
async def summarize(ctx):
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        return await ctx.reply("Admin only")

    title = f"Summary-{datetime.datetime.now().strftime('%B-%Y')}"
    try:
        return sheet.worksheet(title)
    except:
        sws = sheet.add_worksheet(title, 200, 4)
        sws.append_row(["Real Name", "Days Submitted", "Total Days", "Consistency %"])

    days = [w for w in sheet.worksheets() if len(w.title) == 10]
    total = len(days)

    for uname, real in registered_users.items():
        count = sum(1 for d in days if uname in d.col_values(2))
        percent = (count / total * 100) if total else 0
        sws.append_row([real, count, total, f"{percent:.1f}%"])

    await ctx.reply("📊 Summary created")

# ------------------ REMINDER ------------------
@tasks.loop(time=datetime.time(hour=22, minute=0))
async def daily_reminder():
    for uname in registered_users:
        if uname not in submissions_today:
            user = discord.utils.get(bot.users, name=uname)
            if user:
                try:
                    await user.send("⏲️ Submit today's CP")
                except:
                    pass
    submissions_today.clear()

bot.run(os.getenv("TOKEN"))
