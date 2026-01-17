import os
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from yt_dlp import YoutubeDL
import uuid

# ================= CONFIG =================
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

PORT = int(os.environ.get("PORT", 8000))
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ================= FLASK (HEALTH CHECK) =================
app = Flask(__name__)

@app.route("/")
def health():
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT, threaded=True)

threading.Thread(target=run_flask, daemon=True).start()

# ================= BOT =================
bot = Client(
    "stream-downloader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=100
)

# ================= DOWNLOAD =================
@bot.on_message(filters.private & filters.text)
async def download(_, m):
    text = m.text.strip()

    if not text.startswith("http"):
        return await m.reply("❌ Stream URL bhejo")

    # caption format: URL -n NAME
    name = "video"
    if " -n " in text:
        url, name = text.split(" -n ", 1)
    else:
        url = text

    filename = f"{DOWNLOAD_DIR}/{uuid.uuid4().hex}.mp4"

    status = await m.reply("⬇️ Downloading...")

    def hook(d):
        if d["status"] == "downloading":
            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")
            percent = d.get("_percent_str", "")
            asyncio.run_coroutine_threadsafe(
                status.edit(
                    f"⬇️ {percent}\n⚡ {speed}\n⏳ {eta}"
                ),
                bot.loop
            )

    ydl_opts = {
        "format": "best",
        "outtmpl": filename,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "http_headers": {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://physicswallah.live"
        }
    }

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: YoutubeDL(ydl_opts).download([url])
        )
    except Exception as e:
        return await status.edit(f"❌ Failed\n{e}")

    await status.edit("⬆️ Uploading...")

    await m.reply_video(
        filename,
        caption=name
    )

    os.remove(filename)
    await status.delete()

# ================= START =================
bot.run()