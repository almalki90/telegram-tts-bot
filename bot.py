import asyncio
import os
import traceback
import gTTS
from gtts import gTTS as gtts_module
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiohttp import web

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    print("Error: BOT_TOKEN is missing!")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# استخدام مكتبة gTTS كبديل قوي لأن edge-tts محظورة من مايكروسوفت على سيرفرات Render
# ملاحظة: gTTS لا تدعم اختيار صوت (ذكر/أنثى)، تدعم صوت واحد فقط لكل لغة، لذلك سنبسط الخيارات للهجات
user_accents = {}

VOICES = {
    "ar": "🇸🇦 لغة عربية فصحى",
    "en": "🇺🇸 لغة إنجليزية",
    "fr": "🇫🇷 لغة فرنسية",
    "es": "🇪🇸 لغة إسبانية"
}

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    text = "أهلاً بك في بوت تحويل النص إلى صوت 🎙️\n\n- أرسل لي أي نص وسأحوله لصوت واضح.\n- لتغيير لغة التحدث اضغط على /lang"
    await message.reply(text)

@dp.message(Command("lang"))
async def choose_voice(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for voice_id, voice_name in VOICES.items():
        markup.inline_keyboard.append([InlineKeyboardButton(text=voice_name, callback_data=f"voice_{voice_id}")])
    await message.reply("اختر اللغة التي تريدها:", reply_markup=markup)

@dp.callback_query(lambda c: c.data.startswith('voice_'))
async def process_voice(callback_query: types.CallbackQuery):
    voice_id = callback_query.data.replace('voice_', '')
    user_accents[callback_query.from_user.id] = voice_id
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f"✅ تم تغيير اللغة إلى: {VOICES[voice_id]}\nأرسل لي النص الآن!")

@dp.message()
async def handle_text(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    lang = user_accents.get(user_id, "ar") # العربي هو الافتراضي

    processing_msg = await message.reply("⏳ جاري تحويل النص إلى صوت، يرجى الانتظار...")
    audio_file = f"audio_{user_id}.mp3"
    
    try:
        # استخدام gTTS لتوليد الصوت (يعمل بشكل ممتاز ومستقر جداً ولا يتعرض للحظر)
        tts = gtts_module(text=text, lang=lang, slow=False)
        tts.save(audio_file)
        
        audio = FSInputFile(audio_file)
        await bot.send_audio(chat_id=message.chat.id, audio=audio)
        
        if os.path.exists(audio_file):
            os.remove(audio_file)
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error generating audio: {error_details}")
        await bot.edit_message_text(f"❌ حدث خطأ:\n{str(e)}", chat_id=message.chat.id, message_id=processing_msg.message_id)

async def handle_web(request):
    return web.Response(text="Bot is running smoothly with gTTS! 🚀")

async def main():
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")
    
    print("Bot is starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
