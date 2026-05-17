
import telebot
import json
import os
from flask import Flask, request

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 7447651332

# IMPORTANT: replace with your koyeb url
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(BOT_TOKEN)

# =====================
# DATA
# =====================
questions = []
active_group = None
scores = {}
js_buffer = {}

# =====================
# FLASK APP
# =====================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running 🚀"

@app.route("/health")
def health():
    return {"status": "ok"}

# =====================
# TELEGRAM WEBHOOK ROUTE
# =====================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# =====================
# START
# =====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, """
🔥 PRO WEBHOOK QUIZ BOT

📌 Commands:
/test - Quiz system
/ht - HTML generator
/js - JSON builder
/leaderboard - Scores

⚡ Webhook mode active (no crashes)
""")

# =====================
# TEST SYSTEM
# =====================
@bot.message_handler(commands=['test'])
def test_cmd(message):
    if message.from_user.id != OWNER_ID:
        return
    bot.send_message(message.chat.id, "📩 Send JSON file")

@bot.message_handler(content_types=['document'])
def load_json(message):
    global questions

    if message.from_user.id != OWNER_ID:
        return

    file = bot.get_file(message.document.file_id)
    data = bot.download_file(file.file_path)

    try:
        questions = json.loads(data)
    except:
        bot.send_message(message.chat.id, "❌ Invalid JSON")
        return

    bot.send_message(message.chat.id, "✅ JSON loaded\n👉 Send Group ID")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("-100"))
def set_group(message):
    global active_group

    active_group = message.text
    bot.send_message(message.chat.id, "🚀 Starting quiz...")
    send_question(0)

# =====================
# SEND QUESTION
# =====================
def send_question(index):
    global questions, active_group

    if not active_group:
        return

    if index >= len(questions):
        bot.send_message(active_group, "🏁 Quiz Finished!")
        return

    q = questions[index]

    text = f"❓ Q{q.get('question_number', index+1)}\n\n{q['question']}"

    markup = telebot.types.InlineKeyboardMarkup()

    for opt in q['options']:
        safe = str(opt)[:30]

        markup.add(
            telebot.types.InlineKeyboardButton(
                safe,
                callback_data=f"{index}|{safe}"
            )
        )

    bot.send_message(active_group, text, reply_markup=markup)

# =====================
# ANSWER CHECK
# =====================
@bot.callback_query_handler(func=lambda call: True)
def answer(call):
    global questions

    try:
        index, selected = call.data.split("|")
        index = int(index)

        if index >= len(questions):
            bot.answer_callback_query(call.id, "Finished")
            return

        correct = str(questions[index]['answer'])[:30]

        user = call.from_user.id

        if user not in scores:
            scores[user] = 0

        if selected == correct:
            scores[user] += 1
            bot.answer_callback_query(call.id, "✔ Correct")
        else:
            bot.answer_callback_query(call.id, f"❌ Wrong | Ans: {correct}")

        send_question(index + 1)

    except:
        bot.answer_callback_query(call.id, "Error")

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
# JS + HT (simple safe)
# =====================
@bot.message_handler(commands=['js'])
def js_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    js_buffer[message.from_user.id] = []
    bot.send_message(message.chat.id, "📩 Send lines then /done")

@bot.message_handler(commands=['done'])
def js_done(message):
    if message.from_user.id != OWNER_ID:
        return

    data = js_buffer.get(message.from_user.id, [])

    result = [{"id": i+1, "data": d} for i, d in enumerate(data)]

    with open("output.json", "w") as f:
        json.dump(result, f, indent=4)

    bot.send_document(message.chat.id, open("output.json", "rb"))

# =====================
# WEBHOOK SETUP AUTO
# =====================
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

# =====================
# RUN FLASK
# =====================
def run():
    set_webhook()
    app.run(host="0.0.0.0", port=8000)

# =====================
# START
# =====================
if __name__ == "__main__":
    run()