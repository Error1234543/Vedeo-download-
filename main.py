import os
import re
import asyncio
import aiohttp
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message

# ========== CONFIG ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")

STREAM_API = "https://anonymouspwplayerr-c96de7802811.herokuapp.com/pw"

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Client(
    "pw-leech-bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

user_data = {}

# ========== HELPERS ==========

def parse_line(line):
    if ":" in line:
        title, url = line.split(":", 1)
        return title.strip(), url.strip()
    return None, None

def is_pdf(url):
    return ".pdf" in url.lower()

def is_video(url):
    return "mpd" in url or "m3u8" in url

def make_stream_url(url, token):
    return f"{STREAM_API}?url={url}&token={token}"

# ========== COMMANDS ==========

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text(
        "📂 **Send text file containing PDF / Video links**"
    )
    user_data[message.from_user.id] = {}

@app.on_message(filters.document & filters.private)
async def handle_text_file(client, message: Message):
    if not message.document.file_name.endswith(".txt"):
        return await message.reply("❌ Please send only .txt file")

    uid = message.from_user.id
    path = await message.download()

    with open(path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    user_data[uid]["lines"] = lines
    user_data[uid]["index"] = 0

    await message.reply(
        f"✅ File received\n📊 **Total links found:** {len(lines)}\n\n"
        f"➡️ **Send start number (example: 1)**"
    )

@app.on_message(filters.text & filters.private)
async def text_handler(client, message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid not in user_data:
        return

    data = user_data[uid]

    # Start number
    if "start_index" not in data and text.isdigit():
        data["start_index"] = int(text) - 1
        data["index"] = data["start_index"]
        await message.reply("📝 **Send Batch Name**")
        return

    # Batch name
    if "batch" not in data:
        data["batch"] = text
        await message.reply("🚀 **Processing started...**")
        await process_links(message, uid)
        return

    # Token
    if data.get("waiting_token"):
        data["token"] = text
        data["waiting_token"] = False
        await message.reply("🎞 **Send quality (360 / 480 / 720)**")
        return

    # Quality
    if text in ["360", "480", "720"] and data.get("waiting_quality"):
        data["quality"] = text
        data["waiting_quality"] = False
        await download_video(message, uid)
        await process_links(message, uid)
        return

# ========== CORE PROCESS ==========

async def process_links(message, uid):
    data = user_data[uid]
    lines = data["lines"]

    if data["index"] >= len(lines):
        await message.reply("✅ **All downloads completed**")
        user_data.pop(uid)
        return

    line = lines[data["index"]]
    title, url = parse_line(line)

    data["current_title"] = title
    data["current_url"] = url

    # PDF
    if is_pdf(url):
        await download_pdf(message, title, url, data["batch"])
        data["index"] += 1
        await process_links(message, uid)
        return

    # Video
    if is_video(url):
        data["waiting_token"] = True
        await message.reply("🔐 **Send token for video**")
        return

    data["index"] += 1
    await process_links(message, uid)

async def download_pdf(message, title, url, batch):
    file_path = f"{DOWNLOAD_DIR}/{title}.pdf"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            with open(file_path, "wb") as f:
                f.write(await r.read())

    await message.reply_document(
        file_path,
        caption=f"📘 {title}\n📦 Batch: {batch}"
    )

    os.remove(file_path)

async def download_video(message, uid):
    data = user_data[uid]
    stream_url = make_stream_url(data["current_url"], data["token"])
    quality = data["quality"]

    out_file = f"{DOWNLOAD_DIR}/video.mp4"

    cmd = [
        "yt-dlp",
        "-f", f"best[height<={quality}]",
        stream_url,
        "-o", out_file
    ]

    subprocess.run(cmd)

    await message.reply_video(
        out_file,
        caption=(
            f"🎥 {data['current_title']}\n"
            f"📦 Batch: {data['batch']}\n"
            f"📺 Quality: {quality}p"
        )
    )

    os.remove(out_file)
    data["index"] += 1

# ========== RUN ==========
print("🤖 Bot Started...")
app.run()
