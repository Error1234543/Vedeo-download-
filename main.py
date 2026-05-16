import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

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

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

@app.on_message(filters.command("start"))
async def start(_, message: Message):

    await message.reply_text(
        "📂 TXT file send karo.\n\n"
        "Supported:\n"
        "• MP4\n"
        "• M3U8\n"
        "• PDF"
    )

@app.on_message(filters.document)
async def txt_handler(_, message: Message):

    if not message.document.file_name.endswith(".txt"):
        return await message.reply_text(
            "❌ TXT file send karo."
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

    user_data[message.chat.id] = {
        "items": items,
        "quality": "720",
        "by": "Unknown"
    }

    msg = f"✅ Total Files: {len(items)}\n\n"

    for i, item in enumerate(items, start=1):
        msg += f"{i}. {item['title']}\n"

    msg += "\n📥 Starting number send karo."

    await message.reply_text(msg)

@app.on_message(filters.text)
async def text_handler(_, message: Message):

    chat_id = message.chat.id

    if chat_id not in user_data:
        return

    data = user_data[chat_id]

    if "start" not in data:

        try:
            start_num = int(message.text)

            data["start"] = start_num - 1

            return await message.reply_text(
                "🎥 Quality send karo:\n\n360 / 480 / 720 / 1080"
            )

        except:
            return

    if "quality_done" not in data:

        data["quality"] = message.text.strip()
        data["quality_done"] = True

        return await message.reply_text(
            "✍️ Downloaded By name send karo."
        )

    if "name_done" not in data:

        data["by"] = message.text.strip()
        data["name_done"] = True

        await message.reply_text(
            "🚀 Download Started..."
        )

        asyncio.create_task(
            process_queue(message, data)
        )

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

            if ".pdf" in url.lower():

                pdf_path = os.path.join(
                    DOWNLOAD_DIR,
                    f"{title}.pdf"
                )

                os.system(
                    f'wget "{url}" -O "{pdf_path}"'
                )

                await message.reply_document(
                    pdf_path,
                    caption=(
                        f"📄 {title}\n\n"
                        f"Downloaded By: {by_name}"
                    )
                )

                os.remove(pdf_path)

                continue

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
                f"❌ Failed:\n{title}\n\n{e}"
            )

app.run()