import os
import sqlite3
from flask import Flask, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
BOT_TOKEN = '8087028352:AAF1RhB7YeX9KRrMW066Pgy-5TbV5BDycz4'

click_log = {}
search_log = {}

# === SQLite cache setup ===
def init_db():
    conn = sqlite3.connect('cache.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cache (name TEXT PRIMARY KEY, result TEXT)''')
    conn.commit()
    conn.close()

def cache_get(name):
    conn = sqlite3.connect('cache.db')
    c = conn.cursor()
    c.execute('SELECT result FROM cache WHERE name=?', (name,))
    row = c.fetchone()
    conn.close()
    return row[0].split('||') if row else None

def cache_set(name, links):
    conn = sqlite3.connect('cache.db')
    c = conn.cursor()
    c.execute('REPLACE INTO cache (name, result) VALUES (?, ?)', (name, '||'.join(links)))
    conn.commit()
    conn.close()

# === Search Function ===
def search_duckduckgo(name):
    cached = cache_get(name)
    if cached:
        return cached
    query = f"{name} site:instagram.com OR site:twitter.com OR site:facebook.com"
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    links = []
    for a in soup.select('.result__a'):
        href = a['href']
        if any(site in href for site in ["instagram.com", "twitter.com", "facebook.com"]):
            links.append(href)
    links = list(set(links))
    cache_set(name, links)
    return links

# === Telegram Webhook ===
def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    requests.post(url, data={'chat_id': chat_id, 'text': text})

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if 'message' in data and 'text' in data['message']:
        chat_id = data['message']['chat']['id']
        name = data['message']['text']
        links = search_duckduckgo(name)
        if links:
            msg = "\n".join(links)
            send_message(chat_id, f"🔍 Found profiles for *{name}*:\n\n{msg}")
        else:
            send_message(chat_id, f"❌ No social profiles found for *{name}*.")
    return '', 200

# === Web Interface ===
@app.route('/web')
def show_web():
    name = request.args.get('name', '')
    links = search_duckduckgo(name)
    html = f"<h2>Social Profiles for {name}</h2><ul>"
    for i, link in enumerate(links):
        html += f"<li><a href='{link}' target='_blank' onclick='track({i})'>{link}</a></li>"
    html += "</ul><script>function track(i){{fetch('/click?i='+i);}}</script>"
    return html

# === Click Analytics ===
@app.route('/click')
def track_click():
    i = request.args.get('i', 'unknown')
    click_log[i] = click_log.get(i, 0) + 1
    return '', 204

# === Home Page ===
@app.route('/')
def home():
    return '✅ DuckDuckGo Telegram bot is running!'

# === Search UI ===
@app.route('/search', methods=['GET', 'POST'])
def search_page():
    if request.method == 'POST':
        name = request.form.get('name', '')
        search_log[name] = search_log.get(name, 0) + 1
        links = search_duckduckgo(name)
        results_html = "".join([f"<li><a href='{link}' target='_blank'>{link}</a></li>" for link in links])
        return f"""
            <h2>Results for {name}</h2>
            <ul>{results_html}</ul>
            <br><a href='/search'>🔙 Back</a>
        """
    return '''
        <form method="post" onsubmit="document.getElementById('spinner').style.display='block';">
            <h2 style="font-family:sans-serif;">⭐ Find Social Media Profiles</h2>
            <input name="name" placeholder="e.g. Elon Musk" required>
            <button type="submit">🔍 Search</button>
        </form>
        <div id="spinner" style="display:none;"><br>⏳ Searching...</div>
    '''

# === Run App ===
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))  # Render auto-assigns PORT
    app.run(host="0.0.0.0", port=port)
