import os
import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
import threading
from yt_dlp import YoutubeDL

# ================= CONFIG =================
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Client(
    "pw-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_data = {}

# ================= FLASK =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running", 200

def run_flask():
    app.run(host="0.0.0.0", port=8000)

threading.Thread(target=run_flask, daemon=True).start()

# ================= HELPERS =================
def parse_line(line):
    if ":" in line:
        t, u = line.split(":", 1)
        return t.strip(), u.strip()
    return None, None

def is_pdf(url):
    return ".pdf" in url.lower()

def is_video(url):
    return "mpd" in url or "m3u8" in url

# ================= BOT =================
@bot.on_message(filters.command("start") & filters.private)
async def start(_, m: Message):
    user_data[m.from_user.id] = {}
    await m.reply("📂 Send .txt file with PDF / Video links")

@bot.on_message(filters.document & filters.private)
async def file_handler(_, m: Message):
    if not m.document.file_name.endswith(".txt"):
        return await m.reply("❌ Only .txt allowed")

    uid = m.from_user.id
    path = await m.download()

    with open(path, "r", encoding="utf-8") as f:
        lines = [i.strip() for i in f if i.strip()]

    user_data[uid] = {
        "lines": lines,
        "index": 0
    }

    await m.reply(
        f"✅ File loaded\n"
        f"🔗 Total links: {len(lines)}\n\n"
        f"➡️ Send starting number (1-based)"
    )

@bot.on_message(filters.text & filters.private)
async def text_handler(_, m: Message):
    uid = m.from_user.id
    if uid not in user_data:
        return

    d = user_data[uid]
    txt = m.text.strip()

    # Start index
    if "start" not in d and txt.isdigit():
        d["start"] = int(txt) - 1
        d["index"] = d["start"]
        await m.reply("📝 Send batch name")
        return

    # Batch
    if "batch" not in d:
        d["batch"] = txt
        await m.reply("🔐 Send token (only once)")
        d["need_token"] = True
        return

    # Token
    if d.get("need_token"):
        d["token"] = txt
        d["need_token"] = False
        await m.reply("🎞 Send quality (360 / 480 / 720)")
        d["need_quality"] = True
        return

    # Quality
    if d.get("need_quality"):
        if txt not in ["360", "480", "720"]:
            return await m.reply("❌ Send 360 / 480 / 720 only")

        d["quality"] = txt
        d["need_quality"] = False
        await m.reply(f"✅ Quality fixed: {txt}p\n🚀 Starting downloads...")
        await process_next(uid, m)
        return

# ================= CORE =================
async def process_next(uid, m):
    d = user_data[uid]

    if d["index"] >= len(d["lines"]):
        await m.reply("✅ All downloads completed")
        user_data.pop(uid)
        return

    title, url = parse_line(d["lines"][d["index"]])
    d["title"] = title
    d["url"] = url

    if is_pdf(url):
        await download_pdf(m, title, url, d["batch"])
        d["index"] += 1
        await process_next(uid, m)
        return

    if is_video(url):
        await download_video(uid, m)
        return

    d["index"] += 1
    await process_next(uid, m)

# ================= PDF =================
async def download_pdf(m, title, url, batch):
    path = f"{DOWNLOAD_DIR}/{title}.pdf"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            with open(path, "wb") as f:
                async for chunk in r.content.iter_chunked(1024 * 1024):
                    f.write(chunk)

    await m.reply_document(path, caption=f"📘 {title}\n📦 {batch}")
    os.remove(path)

# ================= VIDEO =================
async def download_video(uid, m):
    d = user_data[uid]
    out = f"{DOWNLOAD_DIR}/{d['title']}.mp4"

    status = await m.reply("⬇️ Downloading video...")

    last = {"t": 0}

    def hook(h):
        if h["status"] == "downloading":
            if h.get("elapsed", 0) - last["t"] < 3:
                return
            last["t"] = h.get("elapsed", 0)

            p = h.get("_percent_str", "0%")
            s = h.get("_speed_str", "0 KB/s")
            e = h.get("_eta_str", "?")

            asyncio.run_coroutine_threadsafe(
                status.edit(f"⬇️ {p} | {s} | ETA {e}"),
                bot.loop
            )

    ydl_opts = {
        "format": f"bv*[height<={d['quality']}]+ba/b",
        "outtmpl": out,
        "merge_output_format": "mp4",
        "quiet": True,

        # IMPORTANT HEADERS
        "http_headers": {
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {d['token']}",
            "Referer": "https://physicswallah.live/",
            "Origin": "https://physicswallah.live",
        },

        "progress_hooks": [hook],
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 1,
    }

    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: YoutubeDL(ydl_opts).download([d["url"]])
        )
    except Exception:
        await status.edit(
            "❌ Video failed\n"
            "⚠️ DRM / Token expired\n"
            "➡️ Send fresh token"
        )
        d["need_token"] = True
        return

    await status.edit("⬆️ Uploading...")

    await m.reply_video(
        out,
        caption=f"🎥 {d['title']}\n📦 {d['batch']}\n📺 {d['quality']}p"
    )

    os.remove(out)
    d["index"] += 1
    await process_next(uid, m)

# ================= RUN =================
bot.run()