import telebot
import json
from flask import Flask
import threading

# =====================
# CONFIG
# =====================
BOT_TOKEN = "8527135566:AAGdKxmmK_-a4t-CCQ0t69jdOJu_Kv178sM"
OWNER_ID = 8226637107

bot = telebot.TeleBot(BOT_TOKEN)

questions = []
active_group = None
scores = {}

# =====================
# FLASK HEALTH CHECK
# =====================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Alive 🚀"

@app.route("/health")
def health():
    return {"status": "ok"}

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# =====================
# GLOBAL JS STORAGE
# =====================
js_buffer = {}

# =====================
# START
# =====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, """
🔥 Smart Quiz Bot

📌 Commands:
/test - Group Quiz
/ht - HTML Test
/js - JSON Generator
/leaderboard - Scores

🚀 Ready!
""")

# =====================
# TEST COMMAND
# =====================
@bot.message_handler(commands=['test'])
def test_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    bot.send_message(message.chat.id, "📩 Send JSON file")

# =====================
# HT COMMAND
# =====================
@bot.message_handler(commands=['ht'])
def ht_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    bot.send_message(message.chat.id, "📩 Send JSON for HTML")

# =====================
# JSON LOAD FOR QUIZ
# =====================
@bot.message_handler(content_types=['document'])
def handle_json(message):
    global questions

    if message.from_user.id != OWNER_ID:
        return

    file = bot.get_file(message.document.file_id)
    data = bot.download_file(file.file_path)

    try:
        questions = json.loads(data)
    except:
        bot.reply_to(message, "❌ Invalid JSON")
        return

    bot.send_message(message.chat.id, "✅ JSON Loaded!\nNow send Group ID")

# =====================
# GROUP SET
# =====================
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
    if index >= len(questions):
        bot.send_message(active_group, "🏁 Quiz Finished!")
        return

    q = questions[index]

    text = f"❓ Q{q['question_number']}\n\n{q['question']}"

    markup = telebot.types.InlineKeyboardMarkup()

    for opt in q['options']:
        markup.add(
            telebot.types.InlineKeyboardButton(
                opt,
                callback_data=f"{index}|{opt}"
            )
        )

    bot.send_message(active_group, text, reply_markup=markup)

# =====================
# ANSWER CHECK
# =====================
@bot.callback_query_handler(func=lambda call: True)
def answer(call):
    global questions

    index, selected = call.data.split("|")
    index = int(index)

    correct = questions[index]['answer']

    user = call.from_user.id

    if user not in scores:
        scores[user] = 0

    if selected == correct:
        scores[user] += 1
        bot.answer_callback_query(call.id, "✔ Correct")
    else:
        bot.answer_callback_query(call.id, f"❌ Wrong | Ans: {correct}")

    send_question(index + 1)

# =====================
# LEADERBOARD
# =====================
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):

    if not scores:
        bot.send_message(message.chat.id, "No scores yet")
        return

    text = "🏆 LEADERBOARD\n\n"

    for i, (u, s) in enumerate(sorted(scores.items(), key=lambda x: x[1], reverse=True), 1):
        text += f"{i}. User {u} - {s}\n"

    bot.send_message(message.chat.id, text)

# =====================
# /JS COMMAND START
# =====================
@bot.message_handler(commands=['js'])
def js_start(message):
    if message.from_user.id != OWNER_ID:
        return

    js_buffer[message.from_user.id] = []

    bot.send_message(message.chat.id,
        "📩 Send your data line by line.\nThen type /done to get JSON file.")

# =====================
# COLLECT TEXT
# =====================
@bot.message_handler(func=lambda m: True)
def collect_js(message):
    if message.from_user.id != OWNER_ID:
        return

    if message.from_user.id in js_buffer:

        if message.text.startswith("/"):
            return

        js_buffer[message.from_user.id].append(message.text)

# =====================
# /DONE → CREATE JSON FILE
# =====================
@bot.message_handler(commands=['done'])
def done(message):
    if message.from_user.id != OWNER_ID:
        return

    data_list = js_buffer.get(message.from_user.id, [])

    if not data_list:
        bot.send_message(message.chat.id, "❌ No data found")
        return

    result = []

    for i, line in enumerate(data_list, 1):
        result.append({
            "id": i,
            "data": line
        })

    filename = "output.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    bot.send_document(message.chat.id, open(filename, "rb"))

    js_buffer[message.from_user.id] = []

# =====================
# RUN BOT
# =====================
def run_bot():
    print("Bot Running...")
    bot.infinity_polling(skip_pending=True)

# =====================
# START BOTH
# =====================
if __name__ == "__main__":

    t1 = threading.Thread(target=run_flask)
    t1.start()

    run_bot()