import os, asyncio, requests
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

STREAM_API = "https://anonymouspwplayerr-c96de7802811.herokuapp.com/pw"

app = Client(
    "txt-leech-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_data = {}
user_tasks = {}

# ---------------- UTIL ----------------
def parse_txt(text):
    data = []
    for line in text.splitlines():
        if ":" in line:
            t, u = line.split(":", 1)
            data.append((t.strip(), u.strip()))
    return data

def is_video(url):
    return "cloudfront" in url or ".mpd" in url or ".m3u8" in url

# ---------------- COMMANDS ----------------
@app.on_message(filters.command("dl") & filters.private)
async def start_dl(_, m):
    user_data[m.from_user.id] = {}
    await m.reply("📄 TXT file bhejo")

@app.on_message(filters.document & filters.private)
async def txt_handler(_, m: Message):
    if not m.document.file_name.endswith(".txt"):
        return await m.reply("❌ Sirf .txt file")

    uid = m.from_user.id
    path = await m.download()

    with open(path, "r", encoding="utf-8") as f:
        links = parse_txt(f.read())

    user_data[uid]["links"] = links

    await m.reply(
        f"✅ File loaded\n"
        f"🔗 Total links: {len(links)}\n\n"
        f"➡️ Batao kis number se start kare (1-based)"
    )

@app.on_message(filters.text & filters.private)
async def flow(_, m):
    uid = m.from_user.id
    if uid not in user_data:
        return

    d = user_data[uid]

    if "start" not in d and m.text.isdigit():
        d["start"] = int(m.text) - 1
        await m.reply("🔑 Token bhejo (sirf 1 baar)")
        return

    if "token" not in d:
        d["token"] = m.text.strip()
        await m.reply("🚀 Download start ho raha hai...")
        user_tasks[uid] = asyncio.create_task(queue(uid, m))
        return

# ---------------- QUEUE ----------------
async def queue(uid, m):
    d = user_data[uid]
    links = d["links"]
    token = d["token"]

    for i in range(d["start"], len(links)):
        if uid not in user_tasks:
            break

        title, url = links[i]

        if is_video(url):
            stream = f"{STREAM_API}?url={url}&token={token}"
            await download_video(m, title, stream)
        else:
            await download_pdf(m, title, url)

    await m.reply("✅ All downloads completed")
    user_tasks.pop(uid, None)
    user_data.pop(uid, None)

# ---------------- PDF ----------------
async def download_pdf(m, title, url):
    file = f"{DOWNLOAD_DIR}/{title}.pdf"
    r = requests.get(url, stream=True)

    with open(file, "wb") as f:
        for c in r.iter_content(1024 * 1024):
            f.write(c)

    await m.reply_document(file, caption=title)
    os.remove(file)

# ---------------- VIDEO ----------------
async def download_video(m, title, url):
    status = await m.reply(f"⬇️ Downloading\n🎬 {title}")

    def hook(d):
        if d["status"] == "downloading":
            p = d.get("_percent_str", "")
            s = d.get("_speed_str", "")
            e = d.get("_eta_str", "")
            asyncio.run_coroutine_threadsafe(
                status.edit(
                    f"⬇️ Downloading\n"
                    f"🎬 {title}\n"
                    f"📊 {p}\n"
                    f"🚀 {s}\n"
                    f"⏳ ETA {e}"
                ),
                app.loop
            )

    out = f"{DOWNLOAD_DIR}/{title}.mp4"

    ydl_opts = {
        "outtmpl": out,
        "progress_hooks": [hook],
        "quiet": True,
        "retries": 5,
        "fragment_retries": 5
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    await m.reply_video(out, caption=title)
    os.remove(out)

# ---------------- CANCEL ----------------
@app.on_message(filters.command("cancel") & filters.private)
async def cancel(_, m):
    uid = m.from_user.id
    if uid in user_tasks:
        user_tasks.pop(uid)
        await m.reply("❌ Download cancelled")

app.run()