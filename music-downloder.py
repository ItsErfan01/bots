import os, io, time, asyncio, httpx
from bs4 import BeautifulSoup
from mutagen import File as AudioFile
from telegram import Update, MessageEntity
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

GOOGLE_API_KEY = "AIzaSyDQ8INyTvtD1BJFCpXZjx7064oCAQz3SYI"
CX = "f0788345097924c69"
BOT_TOKEN = "8372568166:AAHezfuJ1s9oRlV-Q-Z667EruNJmbUzWmEs"
AUDIO_FORMATS = [".mp3", ".m4a", ".ogg", ".wav", ".flac", ".aac"]
BOT_USERNAME = "EstivenMotherfucker_bot"

def is_bot_mentioned(update: Update) -> bool:
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == MessageEntity.MENTION:
                mention = update.message.text[entity.offset:entity.offset + entity.length]
                if mention.lower() == f"@{BOT_USERNAME.lower()}":
                    return True
    return False

def extract_song_name(update: Update) -> str:
    text = update.message.text
    for entity in update.message.entities:
        if entity.type == MessageEntity.MENTION:
            end = entity.offset + entity.length
            return text[end:].strip()
    return text.strip()

async def get_best_link(song_name: str, retries=3):
    query = f"دانلود آهنگ {song_name}"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_API_KEY, "cx": CX, "q": query, "num": 1}
    for _ in range(retries):
        try:
            response = httpx.get(url, params=params, timeout=8)
            items = response.json().get("items", [])
            if items:
                return items[0].get("link"), items[0].get("title", "")
        except:
            await asyncio.sleep(2)
    return None, None

async def extract_audio_link(page_url: str, retries=3):
    headers = {"User-Agent": "Mozilla/5.0"}
    for _ in range(retries):
        try:
            response = httpx.get(page_url, headers=headers, timeout=8)
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup.find_all(["audio", "source"]):
                src = tag.get("src")
                if src and any(src.endswith(ext) for ext in AUDIO_FORMATS):
                    return src if src.startswith("http") else page_url + src
            for a in soup.find_all("a", href=True):
                href = a['href']
                if any(href.endswith(ext) for ext in AUDIO_FORMATS) and href.startswith("http"):
                    return href
        except:
            await asyncio.sleep(2)
    return None

async def download_audio_with_progress(audio_url: str, msg, max_retries: int = 3):
    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                head = await client.head(audio_url, headers=headers, timeout=10)
                total_size = int(head.headers.get("Content-Length", 0))
                filename = os.path.basename(audio_url)
                ext = os.path.splitext(filename)[1]
                file_bytes = io.BytesIO()
                file_bytes.name = filename

                start_time = time.time()
                downloaded = 0
                last_reported_percent = -10
                last_progress_time = time.time()

                async with client.stream("GET", audio_url, headers=headers, timeout=30) as response:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        file_bytes.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if downloaded > 0 and now - last_progress_time > 15:
                            raise Exception("دانلود متوقف شده")
                        if downloaded > 0:
                            last_progress_time = now

                        if total_size:
                            percent = int((downloaded / total_size) * 100)
                            elapsed = time.time() - start_time
                            speed = downloaded / elapsed
                            speed_mb = round(speed / (1024 * 1024), 2)
                            remaining = (total_size - downloaded) / speed if speed > 0 else 0
                            minutes, seconds = divmod(int(remaining), 60)
                            size_mb = round(total_size / (1024 * 1024), 2)

                            if percent >= last_reported_percent + 10:
                                try:
                                    await msg.edit_text(
                                        f"🎶 در حال دانلود آهنگ...\n"
                                        f"📥 پیشرفت: {percent}%\n"
                                        f"📦 حجم: {size_mb} مگابایت\n"
                                        f"⚡ سرعت: {speed_mb} MB/s\n"
                                        f"⏳ باقی‌مانده: {minutes} دقیقه و {seconds} ثانیه"
                                    )
                                    last_reported_percent = percent
                                except:
                                    pass

                await msg.edit_text("✅ دانلود کامل شد. 🎵 در حال ارسال فایل...")
                file_bytes.seek(0)

                audio = AudioFile(file_bytes)
                duration = int(audio.info.length) if audio and audio.info else None
                title = str(audio.tags.get("TIT2")) if audio and audio.tags and "TIT2" in audio.tags else None
                performer = str(audio.tags.get("TPE1")) if audio and audio.tags and "TPE1" in audio.tags else None

                return file_bytes, filename, duration, title, performer

        except Exception as e:
            print(f"❌ تلاش {attempt+1} با خطا مواجه شد: {e}")
            await asyncio.sleep(2)

    await msg.edit_text("❌ دانلود انجام نشد. لطفاً دوباره امتحان کن 🎧")
    return None, None, None, None, None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.message.chat.type

    if chat_type in ["group", "supergroup"]:
        text = update.message.text.lower()
        if "هاوکینگ" in text or "هافکینگ" in text:
            await update.message.reply_text("کیرکله بچه‌های کامپیوتر تو کص مامانم", reply_to_message_id=update.message.message_id)
            return

    if chat_type in ["group", "supergroup"]:
        if not is_bot_mentioned(update):
            return
        song_name = extract_song_name(update)
    else:
        song_name = update.message.text.strip()

    msg = await update.message.reply_text(f"🔍 در حال جستجوی آهنگ \"{song_name}\" هستم...")

    page_url, _ = await get_best_link(song_name)
    if not page_url:
        await msg.edit_text("❌ هیچ صفحه‌ای برای دانلود پیدا نشد.")
        return

    audio_url = await extract_audio_link(page_url)
    if not audio_url:
        await msg.edit_text("❌ لینک صوتی قابل دانلود پیدا نشد.")
        return

    file_bytes, filename, duration, title, performer = await download_audio_with_progress(audio_url, msg)
    if not file_bytes:
        return

    try:
        file_bytes.seek(0)  # 🔁 تنظیم مجدد موقعیت فایل
        await context.bot.send_audio(
            chat_id=update.effective_chat.id,  # ✅ استفاده از effective_chat
            audio=file_bytes,
            filename=filename,
            title=title or filename,
            performer=performer or "🎧",
            duration=duration or 0
        )
    except Exception as e:
        print(f"❌ خطا در ارسال فایل: {e}")
        await msg.edit_text("❌ ارسال فایل با مشکل مواجه شد.")
        return

    await msg.delete()

# 🚀 اجرای بات
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()