import telebot
import json
import os
from flask import Flask, request

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OWNER_ID = 8226637107

bot = telebot.TeleBot(BOT_TOKEN)

# =====================
# DATA STORAGE
# =====================
questions = []
scores = {}
js_buffer = {}
user_mode = {}

# =====================
# FLASK APP
# =====================
app = Flask(__name__)

@app.route("/")
def home():
    return "🔥 PRO BOT RUNNING"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK"

# =====================
# START INFO (optional but stable)
# =====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
"""
🔥 PRO WEBHOOK QUIZ BOT

📌 Commands:
/test - Quiz system
/ht - HTML generator
/js - JSON builder
/leaderboard - Scores

⚡ Webhook mode active (stable)
""")

# =====================
# /test → QUIZ MODE
# =====================
@bot.message_handler(commands=['test'])
def test_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    user_mode[message.from_user.id] = "quiz"
    bot.send_message(message.chat.id, "📩 Send Quiz JSON file")

# =====================
# /ht → HTML MODE
# =====================
@bot.message_handler(commands=['ht'])
def ht_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    user_mode[message.from_user.id] = "html"
    bot.send_message(message.chat.id, "📩 Send JSON file for HTML generation")

# =====================
# /js → JSON BUILDER MODE
# =====================
@bot.message_handler(commands=['js'])
def js_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    js_buffer[message.from_user.id] = []
    user_mode[message.from_user.id] = "js"
    bot.send_message(message.chat.id, "📩 Send text lines, then /done")

# =====================
# /done → CREATE JSON
# =====================
@bot.message_handler(commands=['done'])
def done(message):
    if message.from_user.id != OWNER_ID:
        return

    data = js_buffer.get(message.from_user.id, [])

    result = [{"id": i+1, "data": d} for i, d in enumerate(data)]

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    bot.send_document(message.chat.id, open("output.json", "rb"))

# =====================
# TEXT COLLECTOR FOR /js
# =====================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def collect_text(message):

    if message.from_user.id in js_buffer:
        js_buffer[message.from_user.id].append(message.text)

# =====================
# DOCUMENT HANDLER (TEST + HT FIXED)
# =====================
@bot.message_handler(content_types=['document'])
def handle_doc(message):
    global questions

    if message.from_user.id != OWNER_ID:
        return

    mode = user_mode.get(message.from_user.id)

    file = bot.get_file(message.document.file_id)
    data = bot.download_file(file.file_path)

    try:
        parsed = json.loads(data)
    except:
        bot.send_message(message.chat.id, "❌ Invalid JSON")
        return

    # ================= QUIZ =================
    if mode == "quiz":
        questions = parsed
        bot.send_message(message.chat.id, "✅ Quiz Loaded Successfully")

    # ================= HTML =================
    elif mode == "html":
        html = generate_html(parsed)

        with open("quiz.html", "w", encoding="utf-8") as f:
            f.write(html)

        bot.send_document(message.chat.id, open("quiz.html", "rb"))

    user_mode[message.from_user.id] = None

# =====================
# HTML GENERATOR (PRO DESIGN)
# =====================
def generate_html(data):

    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>PRO QUIZ</title>
<style>
body {
    font-family: Arial;
    background: #0f172a;
    color: white;
    padding: 20px;
}

h2 {
    text-align: center;
}

.card {
    background: #1e293b;
    padding: 15px;
    margin: 15px 0;
    border-radius: 12px;
}

.question {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 10px;
}

.option {
    background: #334155;
    padding: 10px;
    margin: 6px 0;
    border-radius: 8px;
    word-wrap: break-word;
}

.option:hover {
    background: #475569;
}
</style>
</head>
<body>

<h2>🔥 PRO QUIZ TEST</h2>
"""

    for q in data:
        html += '<div class="card">'
        html += f'<div class="question">{q.get("question","")}</div>'

        for opt in q.get("options", []):
            html += f'<div class="option">{opt}</div>'

        html += '</div>'

    html += "</body></html>"
    return html

# =====================
# LEADERBOARD
# =====================
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):

    if not scores:
        bot.send_message(message.chat.id, "No scores yet")
        return

    text = "🏆 LEADERBOARD\n\n"

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    for i, (u, s) in enumerate(sorted_scores, 1):
        text += f"{i}. User {u} - {s}\n"

    bot.send_message(message.chat.id, text)

# =====================
# WEBHOOK SETUP
# =====================
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

# =====================
# RUN
# =====================
def run():
    set_webhook()
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run()