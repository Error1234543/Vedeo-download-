import os, re, asyncio, signal, sys, time, math
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
import requests

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

user_tasks = {}
user_data = {}

app = Client(
    "leechbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ---------- UTIL ----------
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
@app.on_message(filters.command("dl"))
async def dl_cmd(_, msg):
    user_data[msg.from_user.id] = {}
    await msg.reply("📄 **Text file bhejo (.txt)**")

@app.on_message(filters.document & filters.private)
async def txt_handler(_, msg: Message):
    if not msg.document.file_name.endswith(".txt"):
        return

    path = await msg.download()
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    links = parse_txt(content)
    uid = msg.from_user.id

    user_data[uid]["links"] = links

    await msg.reply(
        f"✅ **File Loaded**\n\n"
        f"🔗 Total Links: `{len(links)}`\n\n"
        f"👉 Batao kis number se start kare?"
    )

@app.on_message(filters.text & filters.private)
async def text_flow(_, msg):
    uid = msg.from_user.id
    if uid not in user_data:
        return

    if "start" not in user_data[uid]:
        if msg.text.isdigit():
            user_data[uid]["start"] = int(msg.text) - 1
            await msg.reply("🔑 **Token bhejo (sirf 1 baar)**")
        return

    if "token" not in user_data[uid]:
        user_data[uid]["token"] = msg.text.strip()
        await msg.reply("🚀 **Download start ho raha hai...**")
        user_tasks[uid] = asyncio.create_task(start_queue(msg, uid))
        return

# ---------- DOWNLOAD QUEUE ----------
async def start_queue(msg, uid):
    links = user_data[uid]["links"]
    start = user_data[uid]["start"]
    token = user_data[uid]["token"]

    for i in range(start, len(links)):
        title, url = links[i]
        if uid not in user_tasks:
            break

        if is_video(url):
            api_url = f"https://anonymouspwplayerr-c96de7802811.herokuapp.com/pw?url={url}&token={token}"
            await download_video(msg, title, api_url)
        else:
            await download_pdf(msg, title, url)

    await msg.reply("✅ **All Done!**")
    user_tasks.pop(uid, None)

# ---------- PDF ----------
async def download_pdf(msg, title, url):
    r = requests.get(url, stream=True)
    file = f"{DOWNLOAD_DIR}/{title}.pdf"
    with open(file, "wb") as f:
        for c in r.iter_content(1024):
            f.write(c)

    await msg.reply_document(file, caption=title)
    os.remove(file)

# ---------- VIDEO ----------
async def download_video(msg, title, url):
    status = await msg.reply(f"⬇️ Downloading...\n🎬 {title}")

    def hook(d):
        if d["status"] == "downloading":
            speed = d.get("_speed_str", "N/A")
            eta = d.get("_eta_str", "N/A")
            percent = d.get("_percent_str", "0%")
            asyncio.run_coroutine_threadsafe(
                status.edit(
                    f"⬇️ **Downloading**\n"
                    f"🎬 {title}\n"
                    f"📊 {percent}\n"
                    f"🚀 Speed: {speed}\n"
                    f"⏳ ETA: {eta}"
                ),
                app.loop
            )

    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/{title}.mp4",
        "progress_hooks": [hook],
        "quiet": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    file = f"{DOWNLOAD_DIR}/{title}.mp4"
    await msg.reply_video(file, caption=title)
    os.remove(file)

# ---------- CANCEL ----------
@app.on_message(filters.command("cancel"))
async def cancel(_, msg):
    uid = msg.from_user.id
    if uid in user_tasks:
        user_tasks.pop(uid)
        await msg.reply("❌ **Download Cancelled**")

app.run()