import os
import time
import threading
import subprocess
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message
from yt_dlp import YoutubeDL

# ================= CONFIG =================
API_ID = 20619533
API_HASH = "5893568858a096b7373c1970ba05e296"
BOT_TOKEN = "YOUR_BOT_TOKEN"

ALLOWED_GROUP = -1002432150473
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ================= KEEP ALIVE =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Alive 🔥"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask, daemon=True).start()

# ================= BOT =================
bot = Client(
    "render-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

active_users = set()

# ================= SPEED FORMAT =================
def human(size):
    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024:
            return f"{size:.2f}{unit}"
        size /= 1024

# ================= DOWNLOAD =================
def download_video(url, status_msg: Message):
    last_edit = time.time()

    def progress(d):
        nonlocal last_edit
        if d['status'] == 'downloading':
            if time.time() - last_edit > 3:
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate')

                text = (
                    "⬇️ Downloading...\n"
                    f"⚡ Speed: {human(speed)}/s\n"
                    f"📦 Downloaded: {human(downloaded)}\n"
                    f"⏳ ETA: {eta}s"
                )
                if total:
                    text += f"\n📁 Total: {human(total)}"

                try:
                    status_msg.edit(text)
                except:
                    pass

                last_edit = time.time()

    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "progress_hooks": [progress],
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 1,
        "noplaylist": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(e)
        return False

# ================= UPLOAD =================
def upload_video(file_path, message: Message):
    start = time.time()

    def progress(current, total):
        elapsed = time.time() - start
        speed = current / elapsed if elapsed > 0 else 0

        text = (
            "⬆️ Uploading...\n"
            f"⚡ Speed: {human(speed)}/s\n"
            f"📤 Uploaded: {human(current)} / {human(total)}"
        )
        try:
            message.edit(text)
        except:
            pass

    bot.send_video(
        chat_id=message.chat.id,
        video=file_path,
        caption="✅ Upload complete",
        progress=progress
    )

# ================= SINGLE LINK =================
@bot.on_message(filters.text & filters.group)
def single_link(_, message: Message):
    if message.from_user.id in active_users:
        return message.reply("⏳ Ek download pehle se chal raha hai")

    url = message.text.strip()
    if not url.startswith("http"):
        return

    active_users.add(message.from_user.id)
    status = message.reply("⬇️ Starting download...")

    ok = download_video(url, status)

    if ok:
        status.edit("📤 Upload shuru...")
        for f in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, f)
            upload_video(path, status)
            os.remove(path)
    else:
        status.edit("❌ Download failed")

    active_users.remove(message.from_user.id)

# ================= /dl COMMAND =================
@bot.on_message(filters.command("dl") & filters.group)
def ask_txt(_, message: Message):
    message.reply("📄 TXT file bhejo jisme links ho")

# ================= TXT FILE =================
@bot.on_message(filters.document & filters.group)
def txt_handler(_, message: Message):
    if not message.document.file_name.endswith(".txt"):
        return

    if message.from_user.id in active_users:
        return message.reply("⏳ Download chal raha hai")

    active_users.add(message.from_user.id)

    file_path = message.download()
    status = message.reply("📂 TXT file read kar raha hoon...")

    with open(file_path, "r") as f:
        links = [x.strip() for x in f if x.strip().startswith("http")]

    total = len(links)

    for i, link in enumerate(links, start=1):
        status.edit(f"⬇️ ({i}/{total}) Download start")
        download_video(link, status)

        for f in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, f)
            upload_video(path, status)
            os.remove(path)

        time.sleep(5)  # Render safe gap

    status.edit("✅ Sab downloads complete")
    active_users.remove(message.from_user.id)

# ================= START =================
print("Bot Started 🔥")
bot.run()