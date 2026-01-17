import os
import re
import time
import math
import subprocess
import telebot

# ================= CONFIG =================
BOT_TOKEN = "8585007953:AAEqP3K3_5y43YRoYc4h99Lzlg9uE-1rAHo"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ================= UTILS =================
def human_size(size):
    if size is None:
        return "0 MB"
    power = 1024
    n = 0
    Dic_powerN = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {Dic_powerN[n]}"

def extract_name(text):
    m = re.search(r"-n\s+(.+)$", text)
    return m.group(1).strip() if m else "Video"

def extract_url(text):
    return text.split("-n")[0].strip()

# ================= HANDLER =================
@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def stream_download(message):
    url = extract_url(message.text)
    title = extract_name(message.text)

    output = os.path.join(DOWNLOAD_DIR, f"{title}.mp4")

    msg = bot.reply_to(message, "⏳ Initializing download...")

    last_update = 0

    def progress_hook(d):
        nonlocal last_update
        if d["status"] == "downloading":
            now = time.time()
            if now - last_update < 2:
                return
            last_update = now

            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            speed = d.get("speed", 0)
            eta = d.get("eta", 0)

            text = (
                f"⬇️ <b>Downloading</b>\n\n"
                f"📁 <b>{title}.mp4</b>\n"
                f"📦 {human_size(downloaded)} / {human_size(total)}\n"
                f"⚡ Speed: {human_size(speed)}/s\n"
                f"⏳ ETA: {eta}s"
            )

            try:
                bot.edit_message_text(text, message.chat.id, msg.message_id)
            except:
                pass

    ytdlp_cmd = [
        "yt-dlp",
        "--no-playlist",
        "--merge-output-format", "mp4",
        "--add-header", "User-Agent:Mozilla/5.0",
        "--add-header", "Referer:https://physicswallah.live/",
        "--add-header", "Origin:https://physicswallah.live",
        "--no-check-certificates",
        "-o", output,
        url,
        "--progress"
    ]

    try:
        subprocess.Popen(
            ytdlp_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        subprocess.run(ytdlp_cmd, check=True)

    except:
        bot.edit_message_text(
            "❌ Video failed\n⚠️ DRM / Token expired",
            message.chat.id,
            msg.message_id
        )
        return

    # ================= UPLOAD =================
    bot.edit_message_text(
        f"⬆️ <b>Uploading</b>\n\n📁 <b>{title}.mp4</b>",
        message.chat.id,
        msg.message_id
    )

    start = time.time()
    sent = 0
    file_size = os.path.getsize(output)

    def upload_progress(current, total):
        nonlocal sent
        sent = current
        speed = current / (time.time() - start + 1)
        text = (
            f"⬆️ <b>Uploading</b>\n\n"
            f"📁 <b>{title}.mp4</b>\n"
            f"📦 {human_size(current)} / {human_size(total)}\n"
            f"⚡ Speed: {human_size(speed)}/s"
        )
        try:
            bot.edit_message_text(text, message.chat.id, msg.message_id)
        except:
            pass

    with open(output, "rb") as f:
        bot.send_video(
            message.chat.id,
            f,
            caption=title,
            supports_streaming=True,
            progress=upload_progress
        )

    bot.delete_message(message.chat.id, msg.message_id)
    os.remove(output)

# ================= START =================
print("Bot Started")
bot.infinity_polling()