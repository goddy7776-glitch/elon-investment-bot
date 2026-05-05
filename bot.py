import telebot
from telebot import types
import pycountry
import json
import os
import flag  # Make sure to run: pip install emoji-country-flag
from datetime import datetime
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv() 
API_TOKEN = os.getenv('API_TOKEN')

# IMPORTANT: Get your ID from @userinfobot and put it here
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
    user_input = text.strip()
    # Check if it's a flag emoji first
    try:
        code = flag.dflagize(user_input).replace(":", "")
        if len(code) == 2: return True
    except: pass

    # Check by name or code
    user_input_lower = user_input.lower()
    for c in pycountry.countries:
        if user_input_lower == c.name.lower(): return True
        if hasattr(c, 'common_name') and user_input_lower == c.common_name.lower(): return True
        if user_input_lower == c.alpha_2.lower(): return True
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
        show_menu(m.chat.id, u["name"])
    else:
        u["step"] = "awaiting_country"
        save_data(db)
        bot.send_message(m.chat.id, "Welcome! 👋\nPlease send your **Country Name** or **Flag** to verify.")

@bot.message_handler(commands=['admin'])
def admin_panel(m):
    if m.from_user.id != ADMIN_ID:
        bot.reply_to(m, "❌ Access Denied.")
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
            # Resolve flag to name if needed
            try:
                code = flag.dflagize(m.text).replace(":", "")
                if len(code) == 2:
                    c_obj = pycountry.countries.get(alpha_2=code.upper())
                    u["country_name"] = c_obj.name
                else:
                    u["country_name"] = m.text
            except:
                u["country_name"] = m.text
            
            u["step"] = "awaiting_name"
            bot.reply_to(m, f"✅ {u['country_name']} verified! Now enter your **Full Name** (2+ words):")
        else:
            bot.reply_to(m, "❌ Invalid country or flag. Try again.")
    
    elif u["step"] == "awaiting_name":
        if len(m.text.split()) >= 2:
            u["name"] = m.text
            u["step"] = "completed"
            show_menu(m.chat.id, m.text)
        else:
            bot.reply_to(m, "⚠️ Please enter a full name (minimum 2 words).")
    
    # ... (Keep other step handlers like reports/pin here)
    save_data(db)

# --- CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(c):
    uid = str(c.from_user.id)
    u = get_user(uid)

    if c.data == "back_main":
        show_menu(c.message.chat.id, u["name"], edit=True, message_id=c.message.message_id)

    elif c.data == "main_dash":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("$2,000 to get $20,000", callback_data="inv_2000"),
            types.InlineKeyboardButton("⬅️ Back", callback_data="back_main")
        )
        bot.edit_message_text("📈 **Investment Plans**", c.message.chat.id, c.message.message_id, reply_markup=markup)

    elif c.data.startswith("inv_"):
        amt = c.data.split("_")[1]
        msg = (f"📥 **Plan Selected: ${amt}**\n\n"
               f"To begin, fund the **TON Coin** address below.\n\n"
               f"TON Address:\n`{MY_TON_COIN}`\n\n"
               f"Exchange Link:\n{CHANGELY}")
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Back", callback_data="main_dash"))
        bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

    save_data(db)

print("Bot is running...")
bot.infinity_polling()
