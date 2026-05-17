import telebot
import json
import os
from flask import Flask
import threading

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 7447651332

bot = telebot.TeleBot(BOT_TOKEN)

questions = []
active_group = None
scores = {}

# =====================
# FLASK (KOYEB HEALTH)
# =====================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Alive 🚀"

@app.route("/health")
def health():
    return {"status": "ok"}

def run_flask():
    app.run(host="0.0.0.0", port=8000)

# =====================
# START
# =====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, """
🔥 PRO QUIZ BOT

📌 Commands:
/test - Group Quiz
/ht - HTML Test
/js - JSON Tool
/leaderboard - Scores

🚀 Stable Version Active
""")

# =====================
# TEST
# =====================
@bot.message_handler(commands=['test'])
def test(message):
    if message.from_user.id != OWNER_ID:
        return

    bot.send_message(message.chat.id, "📩 Send JSON file")

# =====================
# JSON LOAD
# =====================
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

    bot.send_message(message.chat.id, "✅ Loaded!\nNow send Group ID")

# =====================
# GROUP SET
# =====================
@bot.message_handler(func=lambda m: m.text and m.text.startswith("-100"))
def set_group(message):
    global active_group

    active_group = message.text
    bot.send_message(message.chat.id, "🚀 Starting Quiz...")
    send_question(0)

# =====================
# SEND QUESTION (SAFE)
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
        safe_opt = str(opt)[:30]  # SAFE LIMIT 🔥

        markup.add(
            telebot.types.InlineKeyboardButton(
                safe_opt,
                callback_data=f"{index}|{safe_opt}"
            )
        )

    bot.send_message(active_group, text, reply_markup=markup)

# =====================
# ANSWER HANDLER (FULL SAFE)
# =====================
@bot.callback_query_handler(func=lambda call: True)
def answer(call):
    global questions

    try:
        data = call.data.split("|")

        if len(data) != 2:
            bot.answer_callback_query(call.id, "Invalid data")
            return

        index = int(data[0])
        selected = data[1]

        if index >= len(questions):
            bot.answer_callback_query(call.id, "Test Finished")
            return

        correct = str(questions[index]['answer'])[:30]

        user = call.from_user.id

        if user not in scores:
            scores[user] = 0

        if selected == correct:
            scores[user] += 1
            bot.answer_callback_query(call.id, "✔ Correct")
        else:
            bot.answer_callback_query(call.id, f"❌ Wrong\nAns: {correct}")

        send_question(index + 1)

    except Exception as e:
        print("Callback Error:", e)
        bot.answer_callback_query(call.id, "Error occurred")

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
# BOT RUN
# =====================
def run_bot():
    print("Bot Running...")
    bot.infinity_polling(skip_pending=True)

# =====================
# START BOTH (FLASK + BOT)
# =====================
if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask)
    t1.start()

    run_bot()