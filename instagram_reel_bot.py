import asyncio, math, logging, os
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from yt_dlp import YoutubeDL

TOKEN = "8055592444:AAFkwGx83sD7uYHJ-a3r3V2Lj5rLyoK81zI"
BOT_USERNAME = "Instareeldownloderpro_bot"  # بدون @

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# هندلر /start در چت خصوصی
@dp.message(Command("start"), F.chat.type == "private")
async def start_private(message: Message):
    await message.answer(
        "👋 خوش اومدی!\nفقط لینک ریلز اینستاگرام رو برام بفرست تا برات دانلودش کنم 🎥"
    )

# هندلر لینک مستقیم در چت خصوصی
@dp.message(F.chat.type == "private")
async def handle_private_reel(message: Message):
    text = message.text.strip()
    if text.startswith("https://www.instagram.com/reel/"):
        await process_reel(message, text)

# هندلر منشن و لینک در گروه
@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_reel(message: Message):
    text = message.text.strip()
    parts = text.split()
    if len(parts) != 2:
        return

    mention, link = parts
    if mention != f"@{BOT_USERNAME}":
        return
    if not link.startswith("https://www.instagram.com/reel/"):
        return

    await process_reel(message, link)

# گرفتن حجم فایل قبل از دانلود
def get_video_info(url: str):
    try:
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            best = next((f for f in formats if f.get("ext") == "mp4" and f.get("filesize")), None)
            return best.get("filesize") if best else None
    except Exception:
        return None

# تابع دانلود و ارسال ریلز
async def process_reel(message: Message, reel_url: str):
    status_msg = await message.reply("📥 در حال یافتن ریلز ...")

    total_size = get_video_info(reel_url)
    if total_size:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=f"📦 حجم فایل: {total_size / 1024 / 1024:.2f}MB\n📥 در حال آماده‌سازی دانلود..."
        )
    else:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text="📥 در حال آماده‌سازی دانلود..."
        )

    progress_data = {"done": False}
    filename = "reel.mp4"

    def progress_hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = total_size or d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            percent = min(downloaded / total * 100, 100)
            progress_data.update({
                "downloaded": downloaded,
                "total": total,
                "speed": speed,
                "eta": eta,
                "percent": percent,
                "done": False
            })
        elif d['status'] == 'finished':
            progress_data["done"] = True

    ydl_opts = {
        'format': 'mp4',
        'quiet': True,
        'noplaylist': True,
        'progress_hooks': [progress_hook],
        'outtmpl': filename,
    }

    def download_video():
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([reel_url])
        except Exception:
            progress_data["error"] = True

    thread = Thread(target=download_video)
    thread.start()

    last_msg = ""
    while not progress_data.get("done") and not progress_data.get("error"):
        downloaded = progress_data.get("downloaded", 0)
        total = max(progress_data.get("total", 1), 1)
        percent = progress_data.get("percent", 0)
        speed = progress_data.get("speed", 0)
        eta = progress_data.get("eta", 0)

        msg = (
            f"📥 دانلود در حال انجام...\n"
            f"درصد: {percent:.2f}%\n"
            f"حجم: {downloaded / 1024 / 1024:.2f}MB از {total / 1024 / 1024:.2f}MB\n"
            f"سرعت: {speed / 1024 / 1024:.2f}MB/s\n"
            f"⏳ زمان باقی‌مانده: {math.ceil(eta)} ثانیه"
        )

        if msg != last_msg:
            last_msg = msg
            try:
                await bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=msg)
            except:
                pass

        await asyncio.sleep(1)

    if progress_data.get("error"):
        await bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id,
                                    text="❌ خطا در دانلود ویدیو.")
        return

    try:
        with open(filename, "rb") as f:
            await bot.send_video(chat_id=message.chat.id,
                                 video=types.BufferedInputFile(f.read(), filename="reel.mp4"))
        if os.path.exists(filename):
            os.remove(filename)
        await bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
    except Exception:
        await message.reply("")

# اجرای بات
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dp.run_polling(bot)