import asyncio
import os
import edge_tts
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiohttp import web

TOKEN = os.environ.get("BOT_TOKEN", "8233159789:AAH4xxt55Ei3W-EkjD7enVQPo_caBQWapEA")
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_voices = {}

VOICES = {
    "ar-SA-HamedNeural": "🇸🇦 حامد (ذكر)",
    "ar-SA-ZariyahNeural": "🇸🇦 زارية (أنثى)",
    "ar-EG-ShakirNeural": "🇪🇬 شاكر (ذكر)",
    "ar-EG-SalmaNeural": "🇪🇬 سلمى (أنثى)",
    "ar-AE-HamdanNeural": "🇦🇪 حمدان (ذكر)",
    "ar-AE-FatimaNeural": "🇦🇪 فاطمة (أنثى)"
}

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    text = "أهلاً بك في بوت تحويل النص إلى صوت 🎙️\n\n- أرسل لي أي نص وسأحوله لصوت احترافي.\n- لتغيير الصوت (ذكر/أنثى) اضغط على /voice"
    await message.reply(text)

@dp.message(Command("voice"))
async def choose_voice(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for voice_id, voice_name in VOICES.items():
        markup.inline_keyboard.append([InlineKeyboardButton(text=voice_name, callback_data=f"voice_{voice_id}")])
    await message.reply("اختر الصوت المناسب لك:", reply_markup=markup)

@dp.callback_query(lambda c: c.data.startswith('voice_'))
async def process_voice(callback_query: types.CallbackQuery):
    voice_id = callback_query.data.replace('voice_', '')
    user_voices[callback_query.from_user.id] = voice_id
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f"✅ تم تغيير الصوت إلى: {VOICES[voice_id]}\nأرسل لي النص الآن!")

@dp.message()
async def handle_text(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    voice = user_voices.get(user_id, "ar-SA-HamedNeural")

    processing_msg = await message.reply("⏳ جاري تحويل النص إلى صوت، يرجى الانتظار...")
    audio_file = f"audio_{user_id}.mp3"
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(audio_file)
        audio = FSInputFile(audio_file)
        await bot.send_audio(chat_id=message.chat.id, audio=audio)
        os.remove(audio_file)
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
    except Exception as e:
        await bot.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.", chat_id=message.chat.id, message_id=processing_msg.message_id)

async def handle_web(request):
    return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
