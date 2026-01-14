import os
import asyncio
import subprocess
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
import threading

# ---------------- CONFIG ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

STREAM_API = "https://anonymouspwplayerr-c96de7802811.herokuapp.com/pw"

bot = Client("pw-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_data = {}

# ---------------- FLASK (Health Check) ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running", 200

def run_flask():
    app.run(host="0.0.0.0", port=8000)

threading.Thread(target=run_flask, daemon=True).start()

# ---------------- HELPERS ----------------
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

# ---------------- BOT HANDLERS ----------------
@bot.on_message(filters.command("start") & filters.private)
async def start(_, m: Message):
    user_data[m.from_user.id] = {}
    await m.reply("📂 Send your text file containing PDF/video links.")

@bot.on_message(filters.document & filters.private)
async def file_handler(_, m: Message):
    if not m.document.file_name.endswith(".txt"):
        return await m.reply("❌ Only .txt files are allowed.")
    
    uid = m.from_user.id
    path = await m.download()
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    user_data[uid]["lines"] = lines
    user_data[uid]["index"] = 0
    await m.reply(f"✅ File loaded. Total links: {len(lines)}\n\n➡️ Send the starting link number (1-based)")

@bot.on_message(filters.text & filters.private)
async def text_handler(_, m: Message):
    uid = m.from_user.id
    if uid not in user_data:
        return
    
    d = user_data[uid]
    txt = m.text.strip()

    # STEP 1: Start index
    if "start" not in d and txt.isdigit():
        d["start"] = int(txt) - 1
        d["index"] = d["start"]
        await m.reply("📝 Send batch name (will appear in description).")
        return
    
    # STEP 2: Batch name
    if "batch" not in d:
        d["batch"] = txt
        await m.reply("🚀 Processing started...")
        await process_next(uid, m)
        return
    
    # STEP 3: Token for video
    if d.get("need_token"):
        d["token"] = txt
        d["need_token"] = False
        # Ask quality only once if not already set
        if "quality" not in d:
            d["need_quality"] = True
            await m.reply("🎞 Send quality for all videos (360 / 480 / 720).")
        else:
            # Already quality set, proceed to download video
            await download_video(uid, m)
            await process_next(uid, m)
        return
    
    # STEP 4: Quality (single choice)
    if d.get("need_quality"):
        if txt in ["360", "480", "720"]:
            d["quality"] = txt
            d["need_quality"] = False
            await m.reply(f"✅ Quality set to {txt}p for all videos. Downloading next video...")
            await download_video(uid, m)
            await process_next(uid, m)
        else:
            await m.reply("❌ Invalid quality. Send 360, 480, or 720.")
        return

# ---------------- CORE LOGIC ----------------
async def process_next(uid, m):
    d = user_data[uid]
    if d["index"] >= len(d["lines"]):
        await m.reply("✅ All links processed.")
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
        d["need_token"] = True
        await m.reply(f"🔐 Send token for video: {title}")
        return
    
    d["index"] += 1
    await process_next(uid, m)

async def download_pdf(m, title, url, batch):
    path = f"{DOWNLOAD_DIR}/{title}.pdf"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            with open(path, "wb") as f:
                f.write(await r.read())
    await m.reply_document(path, caption=f"📘 {title}\n📦 {batch}")
    os.remove(path)

async def download_video(uid, m):
    d = user_data[uid]
    stream_url = make_stream(d["url"], d["token"])
    out = f"{DOWNLOAD_DIR}/{d['title']}.mp4"
    
    subprocess.run([
        "yt-dlp",
        "-f", f"best[height<={d['quality']}]",
        stream_url,
        "-o", out
    ])
    
    await m.reply_video(
        out,
        caption=f"🎥 {d['title']}\n📦 {d['batch']}\n📺 {d['quality']}p"
    )
    os.remove(out)
    d["index"] += 1

# ---------------- START BOT ----------------
bot.run()