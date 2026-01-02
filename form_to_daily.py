import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json", SCOPE
)
client = gspread.authorize(creds)

# 🟢 FORM RESPONSE SHEET
FORM_SHEET_ID = "1u7BWSXLXzDMaUCjuglw1MxPCHNoAGsDtlBG99k9_Plg"
form_sheet = client.open_by_key(FORM_SHEET_ID)
form_ws = form_sheet.worksheet("Form Responses 1")

# 🔵 DISCORD BOT MASTER SHEET
BOT_SHEET_ID = "1qPoJ0uBdVCQZMZYWRS6Bt60YjJnYUkD4OePSTRMiSrI"
bot_sheet = client.open_by_key(BOT_SHEET_ID)

rows = form_ws.get_all_records()

# 🔒 EXACT conversion: YYYY-MM-DD → DD-MM-YYYY
def normalize_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")

def get_day_sheet(date_str):
    try:
        return bot_sheet.worksheet(date_str)
    except:
        ws = bot_sheet.add_worksheet(date_str, rows=300, cols=4)
        ws.append_row(["Date", "Username", "Screenshot", "Problem"])
        return ws

for row in rows:
    name = row.get("NAME")
    problem = row.get("PROBLEM NAME")
    raw_date = row.get("DATE OF SUBMISSION")
    screenshot = row.get("SCREENSHOT")

    if not raw_date or not name:
        continue

    try:
        date = normalize_date(raw_date)
    except ValueError:
        continue  # skip bad rows safely

    day_ws = get_day_sheet(date)

    existing = day_ws.get_all_values()
    if any(r[1] == name and r[3] == problem for r in existing[1:]):
        continue

    day_ws.append_row([
        date,
        name,
        screenshot,
        problem
    ])

print("✅ Google Form → Discord Bot sheet sync DONE")
