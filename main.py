import os
import asyncio
import aiohttp
import threading
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
def parse_message(text: str):
    """
    URL -n Title
    """
    if "-n" in text:
        url, name = text.split("-n", 1)
        return url.strip(), name.strip()
    return text.strip(), "Video"

# ================= BOT =================
@bot.on_message(filters.private & filters.text)
async def stream_handler(_, m: Message):
    url, title = parse_message(m.text)

    if not ("mpd" in url or "m3u8" in url):
        return await m.reply("❌ Invalid stream URL")

    out = f"{DOWNLOAD_DIR}/{title}.mp4"

    status = await m.reply(
        f"⬇️ Starting download...\n"
        f"🎬 {title}\n"
        f"⚙️ Engine: yt-dlp"
    )

    last_edit = 0

    # -------- DOWNLOAD PROGRESS --------
    def hook(d):
        nonlocal last_edit
        if d["status"] == "downloading":
            now = asyncio.get_event_loop().time()
            if now - last_edit < 1.2:
                return
            last_edit = now

            percent = d.get("_percent_str", "0%")
            speed = d.get("_speed_str", "0 MB/s")
            eta = d.get("_eta_str", "--")

            text = (
                f"⬇️ Downloading (yt-dlp)\n"
                f"🎬 {title}\n"
                f"📊 Progress : {percent}\n"
                f"🚀 Speed : {speed}\n"
                f"⏳ ETA : {eta}"
            )

            asyncio.run_coroutine_threadsafe(
                status.edit(text),
                bot.loop
            )

    ydl_opts = {
        "outtmpl": out,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
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

    # -------- UPLOAD --------
    upload_start = asyncio.get_event_loop().time()

    async def upload_progress(current, total):
        elapsed = asyncio.get_event_loop().time() - upload_start
        speed = (current / 1024 / 1024) / elapsed if elapsed > 0 else 0
        percent = current * 100 / total

        await status.edit(
            f"⬆️ Uploading to Telegram\n"
            f"🎬 {title}\n"
            f"📊 Progress : {percent:.1f}%\n"
            f"🚀 Speed : {speed:.2f} MB/s"
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