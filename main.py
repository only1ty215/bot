import os
import threading
import requests
from flask import Flask
import telebot

TOKEN = '9092673646:AAFyrSSdYznnUAOlC1jR_rZT2-3hsbYkvNI'
ADMIN_ID = 8172701890

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- HARDCODED BIN DATABASE (No API needed) ---
BIN_DB = {
    "449497": {"bank": "HAPO COMMUNITY CREDIT UNION", "processor": "DCS", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "415823": {"bank": "POLICE FCU", "processor": "DCS", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "514616": {"bank": "WOODFOREST NATIONAL BANK", "processor": "Valet", "vbv": "Non-VBV", "type": "MASTERCARD", "country": "UNITED STATES"},
    "406632": {"bank": "LGE COMMUNITY CREDIT UNION", "processor": "DCS", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "463092": {"bank": "TOWN & COUNTRY FEDERAL CREDIT UNION", "processor": "Valet", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "439348": {"bank": "CNB BANK", "processor": "DX", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "437795": {"bank": "VOYAGE FEDERAL CREDIT UNION", "processor": "DCS", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "470541": {"bank": "CREDIT UNION OF COLORADO", "processor": "DCS", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "429123": {"bank": "SIU CREDIT UNION", "processor": "DCS", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "478820": {"bank": "NUMERICA CREDIT UNION", "processor": "DCS", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "476546": {"bank": "BANKPLUS", "processor": "Valet", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "415384": {"bank": "GESA CREDIT UNION", "processor": "DCS", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "424653": {"bank": "ALABAMA STATE EMPLOYEES CU", "processor": "DCS", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"},
    "430409": {"bank": "AFFINITY FEDERAL CREDIT UNION", "processor": "Valet", "vbv": "Non-VBV", "type": "VISA", "country": "UNITED STATES"}
}

# Dummy route so Render knows it's a web service
@app.route('/')
def health_check():
    return "Bot is alive", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.id != ADMIN_ID: return
    bot.reply_to(message, "Send a BIN to check instantly. Example:\n`/bin 449497`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_bin(message):
    if message.chat.id != ADMIN_ID: return
    
    text = message.text.strip()
    
    # Extract BIN (allows "/bin 449497" or just "449497")
    if text.startswith('/bin '):
        bin_num = text.replace('/bin ', '').strip()
    elif text.isdigit() and 6 <= len(text) <= 8:
        bin_num = text
    else:
        return

    bank = "Unknown"
    processor = "Unknown"
    vbv = "Requires Live Auth Test"
    brand = "Unknown"
    country = "Unknown"

    # 1. Check Local Database
    for known_bin, data in BIN_DB.items():
        if bin_num.startswith(known_bin):
            bank = data['bank']
            processor = data['processor']
            vbv = data['vbv']
            brand = data['type']
            country = data['country']
            break

    # 2. Fallback to API for new BINs
    if bank == "Unknown":
        try:
            r = requests.get(f"https://lookup.binlist.net/{bin_num}", headers={'Accept-Version': '3'}, timeout=5)
            if r.status_code == 200:
                api_data = r.json()
                bank = api_data.get('bank', {}).get('name', 'Unknown')
                brand = api_data.get('scheme', 'Unknown').upper()
                country = api_data.get('country', {}).get('name', 'Unknown')
        except:
            pass

    reply = f"💳 <b>BIN:</b> <code>{bin_num}</code>\n"
    reply += f"🏦 <b>Bank:</b> {bank}\n"
    reply += f"💠 <b>Brand:</b> {brand}\n"
    reply += f"🌍 <b>Country:</b> {country}\n"
    reply += f"⚙️ <b>Processor:</b> {processor}\n"
    reply += f"🛡️ <b>VBV:</b> <code>{vbv}</code>"
    
    bot.reply_to(message, reply, parse_mode='HTML')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False), daemon=True).start()
    
    print("Bot is running...")
    bot.infinity_polling()
