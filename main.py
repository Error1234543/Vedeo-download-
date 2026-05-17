import telebot
import json
import os

# =====================
# CONFIG
# =====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
OWNER_ID = 7447651332

bot = telebot.TeleBot(BOT_TOKEN)

questions = []
active_group_id = None
user_scores = {}

# =====================
# START MESSAGE (PRO UI)
# =====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"""
🔥 Welcome to Smart Quiz Bot

📌 Features:
• /test → Group Quiz System (JSON)
• /ht → HTML Test Generator
• Instant Answer Checking
• Leaderboard System

👑 Owner System Enabled

🚀 Send /test or /ht to begin
""")

# =====================
# TEST COMMAND
# =====================
@bot.message_handler(commands=['test'])
def test_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    bot.send_message(message.chat.id, "📩 Send JSON file for quiz system")

# =====================
# HT COMMAND
# =====================
@bot.message_handler(commands=['ht'])
def ht_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    bot.send_message(message.chat.id, "📩 Send JSON file for HTML test generation")

# =====================
# JSON HANDLER
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

    bot.send_message(message.chat.id, "📌 JSON loaded successfully!\n👉 Now send Group ID like -100xxxx")

# =====================
# GROUP ID SET + START QUIZ
# =====================
@bot.message_handler(func=lambda m: m.text and m.text.startswith("-100"))
def set_group(message):
    global active_group_id

    active_group_id = message.text

    bot.send_message(message.chat.id, "🚀 Starting quiz in group...")
    send_question(0)

# =====================
# SEND QUESTION
# =====================
def send_question(index):
    if index >= len(questions):
        bot.send_message(active_group_id, "🏁 Quiz Finished!")
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

    bot.send_message(active_group_id, text, reply_markup=markup)

# =====================
# ANSWER CHECK
# =====================
@bot.callback_query_handler(func=lambda call: True)
def check_answer(call):
    global questions

    index, selected = call.data.split("|")
    index = int(index)

    correct = questions[index]['answer']

    user_id = call.from_user.id

    if user_id not in user_scores:
        user_scores[user_id] = 0

    if selected == correct:
        user_scores[user_id] += 1
        bot.answer_callback_query(call.id, "✔ Correct")
    else:
        bot.answer_callback_query(call.id, f"❌ Wrong | Ans: {correct}")

    # next question
    send_question(index + 1)

# =====================
# LEADERBOARD
# =====================
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    if not user_scores:
        bot.send_message(message.chat.id, "No scores yet")
        return

    text = "🏆 LEADERBOARD\n\n"

    sorted_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)

    rank = 1
    for uid, score in sorted_users:
        text += f"{rank}. User {uid} - {score}\n"
        rank += 1

    bot.send_message(message.chat.id, text)

# =====================
# HTML GENERATOR
# =====================
def generate_html(data):
    import json

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Quiz Test</title>
<style>
body {{ font-family: Arial; padding: 20px; }}
.card {{ border:1px solid #ddd; padding:15px; margin:10px; }}
button {{ padding:10px; margin:5px; }}
</style>
</head>
<body>

<h2>📘 Online Test</h2>
<div id="quiz"></div>

<script>
const questions = {json.dumps(data)};

let index = 0;
let score = 0;

function loadQ(){{
    if(index >= questions.length){{
        document.getElementById("quiz").innerHTML =
        "<h2>Result: " + score + "/" + questions.length + "</h2>";
        return;
    }}

    let q = questions[index];
    let html = `<div class='card'>
    <h3>Q${{q.question_number}}</h3>
    <p>${{q.question}}</p>`;

    q.options.forEach(opt => {{
        html += `<button onclick="check('${{opt}}','${{q.answer}}')">${{opt}}</button><br>`;
    }});

    html += "</div>";

    document.getElementById("quiz").innerHTML = html;
}}

function check(sel, ans){{
    if(sel === ans) score++;
    index++;
    loadQ();
}}

loadQ();
</script>

</body>
</html>
"""

# =====================
# HT JSON HANDLER
# =====================
@bot.message_handler(content_types=['document'])
def html_json(message):
    if message.from_user.id != OWNER_ID:
        return

    file = bot.get_file(message.document.file_id)
    data = json.loads(bot.download_file(file.file_path))

    html = generate_html(data)

    with open("test.html", "w", encoding="utf-8") as f:
        f.write(html)

    bot.send_document(message.chat.id, open("test.html", "rb"))

# =====================
# RUN BOT
# =====================
print("Bot is running...")
bot.infinity_polling()