import os
import time
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

bot = Client(
    "render-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

active_users = set()

# ================= UTILS =================
def human(size):
    for u in ['B','KB','MB','GB']:
        if size < 1024:
            return f"{size:.2f}{u}"
        size /= 1024

# ================= DOWNLOAD =================
def download_video(url, msg):
    last = time.time()

    def hook(d):
        nonlocal last
        if d['status'] == 'downloading' and time.time() - last > 3:
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            downloaded = d.get('downloaded_bytes', 0)

            text = (
                "⬇️ Downloading...\n"
                f"⚡ Speed: {human(speed)}/s\n"
                f"📦 Downloaded: {human(downloaded)}\n"
                f"⏳ ETA: {eta}s"
            )
            try:
                msg.edit(text)
            except:
                pass
            last = time.time()

    opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "progress_hooks": [hook],
        "noplaylist": True,
        "retries": 5,
        "fragment_retries": 5
    }

    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
        return True
    except:
        return False

# ================= UPLOAD =================
def upload(file, msg):
    start = time.time()

    def progress(cur, total):
        speed = cur / (time.time() - start)
        try:
            msg.edit(
                "⬆️ Uploading...\n"
                f"⚡ Speed: {human(speed)}/s\n"
                f"📤 {human(cur)} / {human(total)}"
            )
        except:
            pass

    bot.send_video(msg.chat.id, file, progress=progress)

# ================= SINGLE LINK =================
@bot.on_message(filters.text & filters.group)
def single(_, m: Message):
    if m.from_user.id in active_users:
        return

    url = m.text.strip()
    if not url.startswith("http"):
        return

    active_users.add(m.from_user.id)
    msg = m.reply("⬇️ Starting...")

    if download_video(url, msg):
        for f in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, f)
            upload(path, msg)
            os.remove(path)
    else:
        msg.edit("❌ Failed")

    active_users.remove(m.from_user.id)

# ================= /dl =================
@bot.on_message(filters.command("dl") & filters.group)
def ask_txt(_, m):
    m.reply("📄 TXT file bhejo")

# ================= TXT FILE =================
@bot.on_message(filters.document & filters.group)
def txt(_, m: Message):
    if m.from_user.id in active_users:
        return

    if not m.document.file_name.endswith(".txt"):
        return

    active_users.add(m.from_user.id)
    path = m.download()
    msg = m.reply("📂 Reading file...")

    with open(path) as f:
        links = [x.strip() for x in f if x.startswith("http")]

    for link in links:
        msg.edit("⬇️ Downloading next...")
        download_video(link, msg)

        for f in os.listdir(DOWNLOAD_DIR):
            p = os.path.join(DOWNLOAD_DIR, f)
            upload(p, msg)
            os.remove(p)

        time.sleep(5)

    msg.edit("✅ All done")
    active_users.remove(m.from_user.id)

print("Bot Running 🔥")
bot.run()