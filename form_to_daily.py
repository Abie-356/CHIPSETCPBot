import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json", SCOPE
)
client = gspread.authorize(creds)

# 🟢 GOOGLE FORM RESPONSE SHEET
FORM_SHEET_ID = "1u7BWSXLXzDMaUCjuglw1MxPCHNoAGsDtlBG99k9_Plg"
form_sheet = client.open_by_key(FORM_SHEET_ID)
form_ws = form_sheet.worksheet("Form Responses 1")

# 🔵 DISCORD BOT MASTER SHEET
BOT_SHEET_ID = "1qPoJ0uBdVCQZMZYWRS6Bt60YjJnYUkD4OePSTRMiSrI"
bot_sheet = client.open_by_key(BOT_SHEET_ID)

rows = form_ws.get_all_records()

print("📥 Total form rows found:", len(rows))  # DEBUG (keep it)

# 🔒 DATE NORMALIZATION (FINAL + SAFE)
from datetime import datetime, date

def normalize_date(raw_date):
def normalize_date(raw_date):
    """
    Convert Google Form date into YYYY-MM-DD
    """
    # Case 1: Google Sheets gives datetime.date
    if isinstance(raw_date, date):
        return raw_date.strftime("%Y-%m-%d")

    # Case 2: Google Form gives string
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    raise ValueError(f"Unsupported date format: {raw_date}")


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
        date_str = normalize_date(raw_date)
    except Exception as e:
        print("⚠️ Skipping row due to date error:", raw_date)
        continue

    day_ws = get_day_sheet(date_str)

    existing = day_ws.get_all_values()
    if any(r[1] == name and r[3] == problem for r in existing[1:]):
        continue

    day_ws.append_row([
        date_str,
        name,
        screenshot,
        problem
    ])

print("✅ Google Form → Discord Bot sheet sync DONE")


