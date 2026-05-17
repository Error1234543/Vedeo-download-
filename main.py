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
# STORAGE
# =====================
questions = []
scores = {}
js_buffer = {}
user_state = {}
active_group = None

# =====================
# FLASK
# =====================
app = Flask(__name__)

@app.route("/")
def home():
    return "🔥 BOT RUNNING"

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
🔥 PRO EXAM BOT

/test → Telegram Quiz
/ht → HTML Exam
/js → JSON Builder
/leaderboard → Scores
""")

# =====================
# /test FLOW FIXED
# =====================
@bot.message_handler(commands=['test'])
def test_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    user_state[message.from_user.id] = "quiz"
    bot.send_message(message.chat.id, "📩 Send Quiz JSON file")

# =====================
# /ht HTML MODE
# =====================
@bot.message_handler(commands=['ht'])
def ht_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    user_state[message.from_user.id] = "html"
    bot.send_message(message.chat.id, "📩 Send JSON for HTML exam")

# =====================
# /js MODE
# =====================
@bot.message_handler(commands=['js'])
def js_cmd(message):
    if message.from_user.id != OWNER_ID:
        return

    js_buffer[message.from_user.id] = []
    user_state[message.from_user.id] = "js"
    bot.send_message(message.chat.id, "📩 Send text lines then /done")

# =====================
# /done JSON EXPORT
# =====================
@bot.message_handler(commands=['done'])
def done(message):
    if message.from_user.id != OWNER_ID:
        return

    data = js_buffer.get(message.from_user.id, [])

    out = [{"id": i+1, "data": d} for i, d in enumerate(data)]

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4, ensure_ascii=False)

    bot.send_document(message.chat.id, open("output.json", "rb"))

# =====================
# TEXT COLLECTOR (JS MODE)
# =====================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def collect(message):
    if message.from_user.id in js_buffer:
        js_buffer[message.from_user.id].append(message.text)

    # GROUP ID for quiz
    global active_group

    if message.text.startswith("-100") and user_state.get(message.from_user.id) == "quiz":
        active_group = message.text
        bot.send_message(message.chat.id, "🚀 Starting Quiz in Group...")
        send_quiz(0)

# =====================
# DOCUMENT HANDLER (FIXED FLOW)
# =====================
@bot.message_handler(content_types=['document'])
def handle_doc(message):
    global questions

    if message.from_user.id != OWNER_ID:
        return

    file = bot.get_file(message.document.file_id)
    data = bot.download_file(file.file_path)

    try:
        parsed = json.loads(data)
    except:
        bot.send_message(message.chat.id, "❌ Invalid JSON")
        return

    mode = user_state.get(message.from_user.id)

    # ================= QUIZ =================
    if mode == "quiz":
        questions = parsed
        bot.send_message(message.chat.id, "✅ Quiz Loaded. Now send GROUP ID (-100...)")

    # ================= HTML =================
    elif mode == "html":
        html = generate_html(parsed)

        with open("exam.html", "w", encoding="utf-8") as f:
            f.write(html)

        bot.send_document(message.chat.id, open("exam.html", "rb"))

    user_state[message.from_user.id] = None

# =====================
# QUIZ SENDER (FIXED)
# =====================
def send_quiz(index):
    global questions, active_group

    if index >= len(questions):
        bot.send_message(active_group, "🏁 Quiz Finished")
        return

    q = questions[index]

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    for opt in q["options"]:
        markup.add(opt)

    bot.send_message(
        active_group,
        f"❓ Q{index+1}\n{q['question']}",
        reply_markup=markup
    )

# =====================
# PRO HTML (FIXED + CLEAN UI)
# =====================
def generate_html(data):

    import json

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>PRO EXAM</title>

<style>
body {{
    font-family: Arial;
    background: #0f172a;
    color: white;
    padding: 20px;
}}

.card {{
    background: #1e293b;
    padding: 15px;
    margin: 15px 0;
    border-radius: 12px;
}}

.option {{
    background: #334155;
    padding: 10px;
    margin: 5px 0;
    border-radius: 8px;
    cursor: pointer;
}}

.option:hover {{
    background: #475569;
}}

#timer {{
    position: fixed;
    top: 10px;
    right: 10px;
    background: red;
    padding: 10px;
    border-radius: 8px;
}}
</style>
</head>

<body>

<div id="timer">⏳ 30</div>
<h2>🔥 ONLINE EXAM</h2>

<div id="quiz"></div>

<script>
let questions = {json.dumps(data)};
let index = 0;
let score = 0;
let wrong = [];
let time = 30;

function load() {{
    let q = questions[index];

    let html = `<div class="card">
        <h3>${{q.question}}</h3>`;

    q.options.forEach(opt => {{
        html += `<div class="option" onclick="check('${{opt}}')">${{opt}}</div>`;
    }});

    html += "</div>";

    document.getElementById("quiz").innerHTML = html;
}}

function check(ans) {{
    let correct = questions[index].answer;

    if(ans === correct) {{
        score++;
    }} else {{
        wrong.push({{q: questions[index].question, your: ans, correct}});
    }}

    index++;

    if(index < questions.length) {{
        load();
        time = 30;
    }} else {{
        result();
    }}
}}

function result() {{
    let html = `<h2>🏁 RESULT</h2>
    <h3>Score: ${{score}} / ${{questions.length}}</h3>
    <h3>Wrong: ${{wrong.length}}</h3>`;

    wrong.forEach(w => {{
        html += `<div class="card">
        <b>Q:</b> ${{w.q}}<br>
        <b>Your:</b> ${{w.your}}<br>
        <b>Correct:</b> ${{w.correct}}
        </div>`;
    }});

    document.getElementById("quiz").innerHTML = html;
}}

setInterval(() => {{
    time--;
    document.getElementById("timer").innerText = "⏳ " + time;

    if(time <= 0) {{
        index++;
        time = 30;
        if(index < questions.length) load();
        else result();
    }}
}},1000);

load();
</script>

</body>
</html>
"""

# =====================
# LEADERBOARD
# =====================
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):

    if not scores:
        bot.send_message(message.chat.id, "No scores yet")
        return

    text = "🏆 LEADERBOARD\n\n"

    for i,(u,s) in enumerate(sorted(scores.items(), key=lambda x: x[1], reverse=True),1):
        text += f"{i}. {u} → {s}\n"

    bot.send_message(message.chat.id, text)

# =====================
# RUN
# =====================
def run():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run()