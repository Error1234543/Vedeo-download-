import os
import asyncio
import aiohttp
import subprocess
from flask import Flask, request
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
APP_URL = os.environ.get("APP_URL")  # Render URL

STREAM_API = "https://anonymouspwplayerr-c96de7802811.herokuapp.com/pw"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ================= PYROGRAM =================
app = Client(
    "pw-leech-bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True
)

user_data = {}

# ================= FLASK =================
flask_app = Flask(__name__)

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

def make_stream_url(url, token):
    return f"{STREAM_API}?url={url}&token={token}"

# ================= BOT LOGIC =================
@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    user_data[message.from_user.id] = {}
    await message.reply("📂 Send text file containing PDF / Video links")

@app.on_message(filters.document & filters.private)
async def handle_file(client, message: Message):
    if not message.document.file_name.endswith(".txt"):
        return await message.reply("❌ Only .txt file allowed")

    uid = message.from_user.id
    path = await message.download()

    with open(path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    user_data[uid]["lines"] = lines
    user_data[uid]["index"] = 0

    await message.reply(
        f"✅ File received\n📊 Total links: {len(lines)}\n\n"
        f"➡️ Send start number (example: 1)"
    )

@app.on_message(filters.text & filters.private)
async def text_handler(client, message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid not in user_data:
        return

    data = user_data[uid]

    if "start_index" not in data and text.isdigit():
        data["start_index"] = int(text) - 1
        data["index"] = data["start_index"]
        await message.reply("📝 Send Batch Name")
        return

    if "batch" not in data:
        data["batch"] = text
        await message.reply("🚀 Processing started")
        await process_links(message, uid)
        return

    if data.get("waiting_token"):
        data["token"] = text
        data["waiting_token"] = False
        data["waiting_quality"] = True
        await message.reply("🎞 Send quality (360 / 480 / 720)")
        return

    if data.get("waiting_quality") and text in ["360", "480", "720"]:
        data["quality"] = text
        data["waiting_quality"] = False
        await download_video(message, uid)
        await process_links(message, uid)

# ================= CORE =================
async def process_links(message, uid):
    data = user_data[uid]
    lines = data["lines"]

    if data["index"] >= len(lines):
        await message.reply("✅ All downloads completed")
        user_data.pop(uid)
        return

    title, url = parse_line(lines[data["index"]])
    data["current_title"] = title
    data["current_url"] = url

    if is_pdf(url):
        await download_pdf(message, title, url, data["batch"])
        data["index"] += 1
        await process_links(message, uid)
        return

    if is_video(url):
        data["waiting_token"] = True
        await message.reply("🔐 Send token for video")
        return

    data["index"] += 1
    await process_links(message, uid)

async def download_pdf(message, title, url, batch):
    path = f"{DOWNLOAD_DIR}/{title}.pdf"
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            with open(path, "wb") as f:
                f.write(await r.read())

    await message.reply_document(
        path,
        caption=f"📘 {title}\n📦 Batch: {batch}"
    )
    os.remove(path)

async def download_video(message, uid):
    data = user_data[uid]
    stream = make_stream_url(data["current_url"], data["token"])
    out = f"{DOWNLOAD_DIR}/video.mp4"

    subprocess.run([
        "yt-dlp",
        "-f", f"best[height<={data['quality']}]",
        stream,
        "-o", out
    ])

    await message.reply_video(
        out,
        caption=f"🎥 {data['current_title']}\n📦 Batch: {data['batch']}\n📺 {data['quality']}p"
    )

    os.remove(out)
    data["index"] += 1

# ================= WEBHOOK =================
@flask_app.route("/", methods=["GET"])
def home():
    return "Bot is running"

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    asyncio.get_event_loop().create_task(app.process_update(update))
    return "OK"

# ================= START =================
if __name__ == "__main__":
    app.start()
    app.set_webhook(f"{APP_URL}/webhook")

    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)