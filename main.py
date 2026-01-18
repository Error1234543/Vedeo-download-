import os
import asyncio
import threading
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from yt_dlp import YoutubeDL
from flask import Flask

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ================= PYROGRAM =================
bot = Client(
    "stream-downloader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= FLASK (KOYEB HEALTH) =================
app = Flask(__name__)

@app.route("/")
def home():
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=8000)

threading.Thread(target=run_flask, daemon=True).start()

# ================= HELPERS =================
def parse_message(text):
    if "-n" in text:
        url, name = text.split("-n", 1)
        return url.strip(), name.strip()
    return text.strip(), "Video"

# ================= BOT =================
@bot.on_message(filters.private & filters.text)
async def handler(_, m: Message):
    url, title = parse_message(m.text)

    if not ("mpd" in url or "m3u8" in url):
        return await m.reply("❌ Invalid stream URL")

    out = f"{DOWNLOAD_DIR}/{title}.mp4"

    status = await m.reply(
        f"⬇️ Starting download\n"
        f"🎬 {title}\n"
        f"⚙️ Engine: yt-dlp"
    )

    last_update = 0

    def hook(d):
        nonlocal last_update
        if d["status"] != "downloading":
            return

        now = time.time()
        if now - last_update < 1.5:
            return
        last_update = now

        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes", 0)

        if not total:
            return

        percent = downloaded * 100 / total
        speed = d.get("speed", 0)
        eta = d.get("eta", 0)

        text = (
            f"⬇️ Downloading\n"
            f"🎬 {title}\n"
            f"📦 {downloaded/1024/1024:.2f} / {total/1024/1024:.2f} MB\n"
            f"📊 {percent:.1f}%\n"
            f"🚀 Speed: {speed/1024/1024:.2f} MB/s\n"
            f"⏳ ETA: {eta}s"
        )

        asyncio.run_coroutine_threadsafe(
            status.edit(text),
            bot.loop
        )

    ydl_opts = {
        "outtmpl": out,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "concurrent_fragment_downloads": 8,
        "http_headers": {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://physicswallah.live"
        }
    }

    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: YoutubeDL(ydl_opts).download([url])
        )
    except Exception as e:
        return await status.edit(f"❌ Download failed\n{e}")

    await status.edit("⬆️ Uploading to Telegram...")

    start = time.time()

    async def upload_progress(cur, total):
        elapsed = time.time() - start
        speed = (cur / 1024 / 1024) / elapsed if elapsed > 0 else 0
        percent = cur * 100 / total

        await status.edit(
            f"⬆️ Uploading\n"
            f"🎬 {title}\n"
            f"📊 {percent:.1f}%\n"
            f"🚀 Speed: {speed:.2f} MB/s"
        )

    await m.reply_video(
        out,
        caption=title,
        progress=upload_progress
    )

    await status.delete()
    os.remove(out)

# ================= RUN =================
bot.run()