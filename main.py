from flask import Flask
from threading import Thread
import os
import re
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

# =========================
# LOAD ENV
# =========================

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# =========================
# FLASK WEB SERVER
# =========================

web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Bot Running Successfully!"

def run_web():
    port = int(os.environ.get("PORT", 8000))
    web_app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()

# =========================
# TELEGRAM BOT
# =========================

app = Client(
    "downloader-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

DOWNLOAD_DIR = "downloads"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

user_data = {}

# =========================
# FUNCTIONS
# =========================

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

# =========================
# START COMMAND
# =========================

@app.on_message(filters.command("start"))
async def start(_, message: Message):

    text = (
        "🚀 TXT Batch Downloader Bot\n\n"
        "📂 TXT file send karo.\n\n"
        "✅ Supported:\n"
        "• MP4\n"
        "• M3U8\n"
        "• PDF\n\n"
        "📝 TXT Format:\n"
        "Lecture 1:https://example.com/video.m3u8"
    )

    await message.reply_text(text)

# =========================
# TXT FILE HANDLER
# =========================

@app.on_message(filters.document)
async def txt_handler(_, message: Message):

    if not message.document.file_name.endswith(".txt"):
        return await message.reply_text(
            "❌ Please send TXT file only."
        )

    txt_file = await message.download()

    with open(txt_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    items = []

    for line in lines:

        line = line.strip()

        if ":" not in line:
            continue

        try:
            title, url = line.split(":", 1)

            items.append({
                "title": title.strip(),
                "url": url.strip()
            })

        except:
            pass

    if not items:
        return await message.reply_text(
            "❌ No valid URLs found."
        )

    total_videos = 0
    total_pdfs = 0

    for item in items:

        if ".pdf" in item["url"].lower():
            total_pdfs += 1
        else:
            total_videos += 1

    user_data[message.chat.id] = {
        "items": items,
        "quality": "720",
        "by": "Unknown"
    }

    msg = (
        f"✅ TXT Loaded Successfully\n\n"
        f"🎬 Videos: {total_videos}\n"
        f"📄 PDFs: {total_pdfs}\n"
        f"📦 Total: {len(items)}\n\n"
    )

    for i, item in enumerate(items, start=1):
        msg += f"{i}. {item['title']}\n"

    msg += "\n📥 Starting number send karo."

    await message.reply_text(msg)

# =========================
# TEXT HANDLER
# =========================

@app.on_message(filters.text)
async def text_handler(_, message: Message):

    chat_id = message.chat.id

    if chat_id not in user_data:
        return

    data = user_data[chat_id]

    # START NUMBER

    if "start" not in data:

        try:

            start_num = int(message.text)

            data["start"] = start_num - 1

            return await message.reply_text(
                "🎥 Quality send karo:\n\n"
                "360 / 480 / 720 / 1080"
            )

        except:
            return

    # QUALITY

    if "quality_done" not in data:

        data["quality"] = message.text.strip()
        data["quality_done"] = True

        return await message.reply_text(
            "✍️ Downloaded By name send karo."
        )

    # NAME

    if "name_done" not in data:

        data["by"] = message.text.strip()
        data["name_done"] = True

        await message.reply_text(
            "🚀 Download Started..."
        )

        asyncio.create_task(
            process_queue(message, data)
        )

# =========================
# PROCESS QUEUE
# =========================

async def process_queue(message, data):

    items = data["items"][data["start"]:]
    quality = data["quality"]
    by_name = data["by"]

    for count, item in enumerate(
        items,
        start=data["start"] + 1
    ):

        title = sanitize(item["title"])
        url = item["url"]

        try:

            # =========================
            # PDF DOWNLOAD
            # =========================

            if ".pdf" in url.lower():

                status = await message.reply_text(
                    f"📄 Downloading PDF:\n{title}"
                )

                pdf_path = os.path.join(
                    DOWNLOAD_DIR,
                    f"{title}.pdf"
                )

                os.system(
                    f'wget "{url}" -O "{pdf_path}"'
                )

                await status.edit_text(
                    f"⬆️ Uploading PDF:\n{title}"
                )

                await message.reply_document(
                    pdf_path,
                    caption=(
                        f"📄 {title}\n\n"
                        f"Downloaded By: {by_name}"
                    )
                )

                os.remove(pdf_path)

                await status.delete()

                continue

            # =========================
            # VIDEO DOWNLOAD
            # =========================

            status = await message.reply_text(
                f"⬇️ Downloading:\n{title}"
            )

            output = os.path.join(
                DOWNLOAD_DIR,
                f"{title}.mp4"
            )

            ydl_opts = {
                "outtmpl": output,
                "format": f"best[height<={quality}]",
                "quiet": True,
                "merge_output_format": "mp4",
                "nocheckcertificate": True
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            await status.edit_text(
                f"⬆️ Uploading:\n{title}"
            )

            caption = (
                f"🎬 {title}\n\n"
                f"Downloaded By: {by_name}"
            )

            await message.reply_video(
                output,
                caption=caption,
                supports_streaming=True
            )

            os.remove(output)

            await status.delete()

        except Exception as e:

            await message.reply_text(
                f"❌ Failed:\n\n"
                f"📁 {title}\n\n"
                f"⚠️ Error:\n{e}"
            )

    await message.reply_text(
        "✅ All Downloads Completed."
    )

# =========================
# RUN BOT
# =========================

print("🚀 Bot Started Successfully")

app.run()