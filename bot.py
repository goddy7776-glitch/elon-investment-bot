import os
import asyncio
from telebot import TeleBot, types
from pytonconnect import TonConnect
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
API_TOKEN = os.getenv('API_TOKEN')
# COMMENT: Replace the value below in your Render Environment Variables with your actual TON wallet address
MY_WALLET_ADDRESS = os.getenv('UQBFgzpjyEIMpZj1wsXEgHmqfeAS_R48SoVbv-J_WjcmkujE') 

bot = TeleBot(API_TOKEN)

# Manifest link (tells the wallet your bot's name/icon)
MANIFEST_URL = "https://raw.githubusercontent.com/ton-connect/demo-dapp-with-react-ui/master/public/tonconnect-manifest.json"

@bot.message_handler(commands=['start', 'invest'])
def start_investing(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Define investment amounts
    btn1 = types.InlineKeyboardButton("Invest 5 TON", callback_data="deposit_5")
    btn2 = types.InlineKeyboardButton("Invest 10 TON", callback_data="deposit_10")
    btn3 = types.InlineKeyboardButton("Invest 50 TON", callback_data="deposit_50")
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(message.chat.id, "Select an amount to invest via TON Connect:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('deposit_'))
def handle_deposit(call):
    amount_ton = int(call.data.split('_')[1])
    # Convert TON to Nanotons (1 TON = 1,000,000,000 Nanotons)
    amount_nanotons = amount_ton * 10**9

    connector = TonConnect(MANIFEST_URL)
    
    # 1. Generate connection link if user isn't connected
    wallets_list = connector.get_wallets()
    generated_url = connector.connect(wallets_list[0]) # Defaults to Tonkeeper

    # 2. Prepare the transaction details
    transaction = {
        'valid_until': 1000, # Time in seconds
        'messages': [
            {
                'address': MY_WALLET_ADDRESS, # This is your linked wallet
                'amount': str(amount_nanotons), # The investment amount
            }
        ]
    }

    # 3. Send response to user
    markup = types.InlineKeyboardMarkup()
    connect_btn = types.InlineKeyboardButton("Open Tonkeeper to Pay", url=generated_url)
    markup.add(connect_btn)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Requesting deposit of {amount_ton} TON.\n\nTap below to open your wallet and confirm the transaction.",
        reply_markup=markup
    )

# Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(none_stop=True)
