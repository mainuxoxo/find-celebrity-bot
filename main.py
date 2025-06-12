import os
from flask import Flask, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
BOT_TOKEN = '8087028352:AAF1RhB7YeX9KRrMW066Pgy-5TbV5BDycz4'

def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    requests.post(url, data={'chat_id': chat_id, 'text': text})

def search_duckduckgo(name):
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
    return list(set(links))

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

@app.route('/web')
def show_web():
    name = request.args.get('name', '')
    links = search_duckduckgo(name)
    html = f"<h2>Social Profiles for {name}</h2><ul>"
    for i, link in enumerate(links):
        html += f"<li><a href='{link}' target='_blank' onclick='track({i})'>{link}</a></li>"
    html += "</ul><script>function track(i){{fetch('/click?i='+i);}}</script>"
    return html

click_log = {}

@app.route('/click')
def track_click():
    i = request.args.get('i', 'unknown')
    click_log[i] = click_log.get(i, 0) + 1
    return '', 204

@app.route('/')
def home():
    return '✅ DuckDuckGo Telegram bot is running!'


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render sets PORT automatically
    app.run(host="0.0.0.0", port=port)