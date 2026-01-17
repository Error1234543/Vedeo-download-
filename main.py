import os, re, asyncio, threading, requests
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
from flask import Flask

# ---------------- CONFIG ----------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ---------------- FLASK (Health check) ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running ✅", 200

def run_flask():
    app.run(host="0.0.0.0", port=8000)

threading.Thread(target=run_flask, daemon=True).start()

# ---------------- BOT ----------------
bot = Client("leechbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_data = {}  # Stores user text file & settings
user_tasks = {}  # Stores asyncio tasks per user

# ---------- HELPERS ----------
def parse_txt(text):
    links = []
    for line in text.splitlines():
        if ":" in line:
            title, url = line.split(":", 1)
            links.append((title.strip(), url.strip()))
    return links

def is_video(url):
    return "cloudfront" in url or ".m3u8" in url or ".mpd" in url

# ---------- COMMANDS ----------
@bot.on_message(filters.command("dl") & filters.private)
async def dl_cmd(_, msg):
    user_data[msg.from_user.id] = {}
    await msg.reply("📄 **Text file bhejo (.txt)**")

@bot.on_message(filters.document & filters.private)
async def txt_handler(_, msg: Message):
    if not msg.document.file_name.endswith(".txt"):
        return await msg.reply("❌ Only `.txt` files allowed.")

    path = await msg.download()
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    links = parse_txt(content)
    uid = msg.from_user.id
    user_data[uid]["links"] = links

    await msg.reply(
        f"✅ **File Loaded**\n"
        f"🔗 Total Links: `{len(links)}`\n"
        f"👉 Batao kis number se start kare?"
    )

@bot.on_message(filters.text & filters.private)
async def text_flow(_, msg: Message):
    uid = msg.from_user.id
    if uid not in user_data:
        return

    data = user_data[uid]

    # Step 1: start number
    if "start" not in data:
        if msg.text.isdigit():
            data["start"] = int(msg.text) - 1
            await msg.reply("🔑 **Token bhejo (sirf 1 baar)**")
        return

    # Step 2: token
    if "token" not in data:
        data["token"] = msg.text.strip()
        await msg.reply("🚀 **Download start ho raha hai...**")
        task = asyncio.create_task(start_queue(msg, uid))
        user_tasks[uid] = task
        return

# ---------- QUEUE ----------
async def start_queue(msg: Message, uid: int):
    data = user_data[uid]
    links = data["links"]
    start = data["start"]
    token = data["token"]

    for i in range(start, len(links)):
        title, url = links[i]

        if uid not in user_tasks:  # Cancelled
            break

        if is_video(url):
            api_url = f"https://anonymouspwplayerr-c96de7802811.herokuapp.com/pw?url={url}&token={token}"
            await download_video(msg, title, api_url)
        else:
            await download_pdf(msg, title, url)

    if uid in user_tasks:
        await msg.reply("✅ **All downloads completed!**")
        user_tasks.pop(uid, None)

# ---------- PDF ----------
async def download_pdf(msg: Message, title: str, url: str):
    status = await msg.reply(f"⬇️ Downloading PDF...\n📄 {title}")
    file_path = f"{DOWNLOAD_DIR}/{title}.pdf"

    with requests.get(url, stream=True) as r:
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = downloaded / total * 100 if total else 0
                    await status.edit(f"⬇️ Downloading PDF...\n📄 {title}\n📊 {percent:.1f}%")

    await msg.reply_document(file_path, caption=title)
    os.remove(file_path)

# ---------- VIDEO ----------
async def download_video(msg: Message, title: str, url: str):
    status = await msg.reply(f"⬇️ Downloading Video...\n🎬 {title}\n⚙️ Engine: yt-dlp")

    def hook(d):
        if d["status"] == "downloading":
            speed = d.get("_speed_str", "N/A")
            eta = d.get("_eta_str", "N/A")
            percent = d.get("_percent_str", "0%")
            asyncio.run_coroutine_threadsafe(
                status.edit(
                    f"⬇️ Downloading Video...\n"
                    f"🎬 {title}\n"
                    f"📊 {percent}\n"
                    f"🚀 Speed: {speed}\n"
                    f"⏳ ETA: {eta}\n"
                    f"⚙️ Engine: yt-dlp"
                ),
                bot.loop
            )

    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/{title}.mp4",
        "progress_hooks": [hook],
        "quiet": True,
        "concurrent_fragment_downloads": 4
    }

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))

    file_path = f"{DOWNLOAD_DIR}/{title}.mp4"
    await msg.reply_video(file_path, caption=title)
    os.remove(file_path)

# ---------- CANCEL ----------
@bot.on_message(filters.command("cancel") & filters.private)
async def cancel(_, msg: Message):
    uid = msg.from_user.id
    if uid in user_tasks:
        user_tasks.pop(uid)
        await msg.reply("❌ **Download Cancelled**")

# ---------- RUN ----------
bot.run()