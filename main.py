import telebot
import json
import os
from flask import Flask
import threading

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 8226637107

bot = telebot.TeleBot(BOT_TOKEN)

# =====================
# STORAGE
# =====================
questions = []
active_group = None
scores = {}

# JS SYSTEM STORAGE
js_buffer = {}

# HT SYSTEM STORAGE
ht_questions = []

# =====================
# FLASK (KOYEB HEALTH)
# =====================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running 🚀"

@app.route("/health")
def health():
    return {"status": "ok"}

def run_flask():
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)
# =====================
# START
# =====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, """
🔥 PRO QUIZ BOT

📌 Commands:
/test - Group Quiz (JSON → Poll)
/ht - JSON → HTML File
/js - JSON Builder Tool
/leaderboard - Scores

🚀 All Systems Active
""")

# =========================================================
# ===================== 🔥 /TEST SYSTEM ====================
# =========================================================

@bot.message_handler(commands=['test'])
def test_cmd(message):
    if message.from_user.id != OWNER_ID:
        return
    bot.send_message(message.chat.id, "📩 Send JSON file for Quiz")

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

    bot.send_message(message.chat.id, "✅ JSON Loaded\n👉 Now send Group ID")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("-100"))
def set_group(message):
    global active_group

    active_group = message.text
    bot.send_message(message.chat.id, "🚀 Sending Quiz to Group...")
    send_question(0)

def send_question(index):
    global questions, active_group

    if not active_group:
        return

    if index >= len(questions):
        bot.send_message(active_group, "🏁 Quiz Finished!")
        return

    q = questions[index]

    text = f"❓ Q{q['question_number']}\n\n{q['question']}"

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

# =========================================================
# ===================== 🔥 /HT SYSTEM ======================
# =========================================================

@bot.message_handler(commands=['ht'])
def ht_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    bot.send_message(message.chat.id, "📩 Send JSON for HTML conversion")

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

def generate_html(data):
    import json

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Test</title>
</head>
<body>

<h2>Online Test</h2>
<div id="q"></div>

<script>
const q = {json.dumps(data)};
let i=0, score=0;

function load(){{
if(i>=q.length){{
document.getElementById('q').innerHTML="Result: "+score;
return;
}}

let x=q[i];
let h=`<h3>${{x.question}}</h3>`;

x.options.forEach(o=>{
h+=`<button onclick="check('${{o}}','${{x.answer}}')">${{o}}</button><br>`;
});

document.getElementById('q').innerHTML=h;
}}

function check(s,a){{
if(s==a) score++;
i++;
load();
}}

load();
</script>

</body>
</html>
"""

# =========================================================
# ===================== 🔥 /JS SYSTEM =====================
# =========================================================

@bot.message_handler(commands=['js'])
def js_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    js_buffer[message.from_user.id] = []
    bot.send_message(message.chat.id, "📩 Send lines then /done")

@bot.message_handler(func=lambda m: True)
def collect_js(message):
    if message.from_user.id != OWNER_ID:
        return

    if message.from_user.id in js_buffer:
        if message.text.startswith("/"):
            return
        js_buffer[message.from_user.id].append(message.text)

@bot.message_handler(commands=['done'])
def js_done(message):
    if message.from_user.id != OWNER_ID:
        return

    data = js_buffer.get(message.from_user.id, [])

    result = [{"id": i+1, "data": d} for i,d in enumerate(data)]

    with open("output.json","w") as f:
        json.dump(result,f,indent=4)

    bot.send_document(message.chat.id, open("output.json","rb"))

    js_buffer[message.from_user.id] = []

# =========================================================
# ===================== LEADERBOARD =======================
# =========================================================

@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):

    if not scores:
        bot.send_message(message.chat.id, "No scores yet")
        return

    text="🏆 LEADERBOARD\n\n"

    for i,(u,s) in enumerate(sorted(scores.items(),key=lambda x:x[1],reverse=True),1):
        text+=f"{i}. User {u} - {s}\n"

    bot.send_message(message.chat.id,text)

# =========================================================
# ===================== RUN BOT ===========================
# =========================================================

def run_bot():
    print("Bot Running...")
    bot.infinity_polling(skip_pending=True)

if __name__=="__main__":

    threading.Thread(target=run_flask).start()
    run_bot()