import telebot
import json
import os
import time
from flask import Flask, request

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OWNER_ID = 8226637107

bot = telebot.TeleBot(BOT_TOKEN)

# =====================
# DATA
# =====================
exams = {}
active_exam = None
active_group = None
scores = {}
timer_data = {}

# =====================
# FLASK
# =====================
app = Flask(__name__)

@app.route("/")
def home():
    return "BOT RUNNING 🚀"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK"

# =====================
# START
# =====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
"""
🔥 ULTRA PRO EXAM BOT

/startquiz → Start exam
/stop → Stop exam
/reset → Reset leaderboard
/status → Bot status

/test → Load quiz JSON
/ht → HTML generator
/js → JSON builder
/leaderboard → Scores

⚡ Advanced Exam System Active
""")

# =====================
# STATUS
# =====================
@bot.message_handler(commands=['status'])
def status(message):
    bot.send_message(message.chat.id,
f"""
📊 BOT STATUS

Active Exam: {active_exam}
Active Group: {active_group}
Users: {len(scores)}
""")

# =====================
# RESET SCORES
# =====================
@bot.message_handler(commands=['reset'])
def reset(message):
    if message.from_user.id != OWNER_ID:
        return

    scores.clear()
    bot.send_message(message.chat.id, "♻ Leaderboard Reset Done")

# =====================
# START QUIZ IN GROUP
# =====================
@bot.message_handler(commands=['startquiz'])
def startquiz(message):
    global active_group, active_exam

    if message.from_user.id != OWNER_ID:
        return

    active_group = message.chat.id
    active_exam = "default"

    bot.send_message(message.chat.id, "🚀 Quiz Started in Group")
    send_question(0)

# =====================
# STOP QUIZ
# =====================
@bot.message_handler(commands=['stop'])
def stop(message):
    global active_exam, active_group

    if message.from_user.id != OWNER_ID:
        return

    active_exam = None
    active_group = None

    bot.send_message(message.chat.id, "⛔ Quiz Stopped")

# =====================
# TEST LOAD
# =====================
@bot.message_handler(commands=['test'])
def test_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    bot.send_message(message.chat.id, "📩 Send JSON file")

# =====================
# HT
# =====================
@bot.message_handler(commands=['ht'])
def ht_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    bot.send_message(message.chat.id, "📩 Send JSON for HTML")

# =====================
# JS
# =====================
js_buffer = {}

@bot.message_handler(commands=['js'])
def js_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    js_buffer[message.from_user.id] = []
    bot.send_message(message.chat.id, "📩 Send text then /done")

# =====================
# DONE
# =====================
@bot.message_handler(commands=['done'])
def done(message):
    if message.from_user.id != OWNER_ID:
        return

    data = js_buffer.get(message.from_user.id, [])

    out = [{"id": i+1, "data": d} for i, d in enumerate(data)]

    with open("output.json", "w") as f:
        json.dump(out, f, indent=4)

    bot.send_document(message.chat.id, open("output.json", "rb"))

# =====================
# SCORES RESET + INIT
# =====================
def add_score(user, mark):
    if user not in scores:
        scores[user] = 0
    scores[user] += mark

# =====================
# LOAD JSON
# =====================
questions = []

@bot.message_handler(content_types=['document'])
def load_file(message):
    global questions

    if message.from_user.id != OWNER_ID:
        return

    file = bot.get_file(message.document.file_id)
    data = bot.download_file(file.file_path)

    parsed = json.loads(data)

    if isinstance(parsed, list) and "question" in parsed[0]:
        questions = parsed
        bot.send_message(message.chat.id, "✅ Quiz Loaded")

# =====================
# SEND QUESTION (TIMER + NEGATIVE MARK)
# =====================
def send_question(index):
    global questions, active_group

    if not active_group:
        return

    if index >= len(questions):
        bot.send_message(active_group, "🏁 Exam Finished")
        return

    q = questions[index]

    text = f"⏳ Q{index+1}\n{q['question']}\n\n⚡ Timer: 30 sec"

    markup = telebot.types.InlineKeyboardMarkup()

    for opt in q['options']:
        markup.add(
            telebot.types.InlineKeyboardButton(opt[:30], callback_data=f"{index}|{opt}")
        )

    bot.send_message(active_group, text, reply_markup=markup)

    timer_data[index] = time.time()

# =====================
# ANSWER CHECK (NEGATIVE MARKING)
# =====================
@bot.callback_query_handler(func=lambda call: True)
def check_answer(call):
    try:
        index, selected = call.data.split("|")
        index = int(index)

        correct = questions[index]['answer']

        user = call.from_user.id

        if selected == correct:
            add_score(user, 1)
            bot.answer_callback_query(call.id, "✔ Correct +1")
        else:
            add_score(user, -0.25)
            bot.answer_callback_query(call.id, f"❌ Wrong | Ans: {correct}")

        send_question(index + 1)

    except:
        bot.answer_callback_query(call.id, "Error")

# =====================
# LEADERBOARD
# =====================
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):

    text = "🏆 LEADERBOARD\n\n"

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    for i, (u, s) in enumerate(sorted_scores, 1):
        text += f"{i}. {u} → {s}\n"

    bot.send_message(message.chat.id, text)

# =====================
# WEBHOOK
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