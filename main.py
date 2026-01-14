import os
import asyncio
import subprocess
import aiohttp
from flask import Flask, request
from pyrogram import Client, filters
from pyrogram.types import Message

# ========== CONFIG ==========
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
APP_URL = os.environ["APP_URL"]   # https://xxx.koyeb.app

STREAM_API = "https://anonymouspwplayerr-c96de7802811.herokuapp.com/pw"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ========== PYROGRAM ==========
bot = Client(
    "pw-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

user_data = {}

# ========== FLASK ==========
web = Flask(__name__)

# ========== HELPERS ==========
def parse_line(line):
    if ":" in line:
        t, u = line.split(":", 1)
        return t.strip(), u.strip()
    return None, None

def is_pdf(url):
    return ".pdf" in url.lower()

def is_video(url):
    return "mpd" in url or "m3u8" in url

def make_stream(url, token):
    return f"{STREAM_API}?url={url}&token={token}"

# ========== BOT ==========
@bot.on_message(filters.command("start"))
async def start(_, m: Message):
    user_data[m.from_user.id] = {}
    await m.reply("📂 Send text file (.txt)")

@bot.on_message(filters.document & filters.private)
async def file_handler(_, m: Message):
    if not m.document.file_name.endswith(".txt"):
        return await m.reply("❌ Only .txt allowed")

    uid = m.from_user.id
    path = await m.download()

    with open(path, "r", encoding="utf-8") as f:
        lines = [i.strip() for i in f if i.strip()]

    user_data[uid]["lines"] = lines
    user_data[uid]["index"] = 0

    await m.reply(
        f"✅ File loaded\n📊 Total links: {len(lines)}\n\n➡️ Send start number"
    )

@bot.on_message(filters.text & filters.private)
async def text_handler(_, m: Message):
    uid = m.from_user.id
    if uid not in user_data:
        return

    d = user_data[uid]
    txt = m.text.strip()

    if "start" not in d and txt.isdigit():
        d["start"] = int(txt) - 1
        d["index"] = d["start"]
        await m.reply("📝 Send Batch Name")
        return

    if "batch" not in d:
        d["batch"] = txt
        await m.reply("🚀 Processing started")
        await process(uid, m)
        return

    if d.get("need_token"):
        d["token"] = txt
        d["need_token"] = False
        d["need_quality"] = True
        await m.reply("🎞 Send quality (360 / 480 / 720)")
        return

    if d.get("need_quality") and txt in ["360", "480", "720"]:
        d["quality"] = txt
        d["need_quality"] = False
        await download_video(uid, m)
        await process(uid, m)

# ========== CORE ==========
async def process(uid, m):
    d = user_data[uid]
    if d["index"] >= len(d["lines"]):
        await m.reply("✅ All done")
        user_data.pop(uid)
        return

    title, url = parse_line(d["lines"][d["index"]])
    d["title"] = title
    d["url"] = url

    if is_pdf(url):
        await download_pdf(m, title, url, d["batch"])
        d["index"] += 1
        await process(uid, m)
        return

    if is_video(url):
        d["need_token"] = True
        await m.reply("🔐 Send token")
        return

    d["index"] += 1
    await process(uid, m)

async def download_pdf(m, title, url, batch):
    path = f"{DOWNLOAD_DIR}/{title}.pdf"
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            with open(path, "wb") as f:
                f.write(await r.read())

    await m.reply_document(path, caption=f"📘 {title}\n📦 {batch}")
    os.remove(path)

async def download_video(uid, m):
    d = user_data[uid]
    stream = make_stream(d["url"], d["token"])
    out = f"{DOWNLOAD_DIR}/video.mp4"

    subprocess.run([
        "yt-dlp",
        "-f", f"best[height<={d['quality']}]",
        stream,
        "-o", out
    ])

    await m.reply_video(
        out,
        caption=f"🎥 {d['title']}\n📦 {d['batch']}\n📺 {d['quality']}p"
    )
    os.remove(out)
    d["index"] += 1

# ========== WEBHOOK ==========
@web.route("/", methods=["GET"])
def home():
    return "Bot is running"

@web.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    asyncio.get_event_loop().create_task(bot.process_update(update))
    return "ok"

# ========== START ==========
if __name__ == "__main__":
    bot.start()
    bot.set_webhook(f"{APP_URL}/webhook")

    port = int(os.environ.get("PORT", 8000))
    web.run(host="0.0.0.0", port=port)