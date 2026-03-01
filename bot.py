import telebot
import os
from gtts import gTTS
import traceback

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: BOT_TOKEN is missing!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 أهلاً بك! \nأرسل لي أي نص عربي وسأقوم بتحويله إلى مقطع صوتي واضح ومستقر فوراً.")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text
    chat_id = message.chat.id
    
    # رسالة انتظار
    msg = bot.reply_to(message, "⏳ جاري تجهيز المقطع الصوتي، لحظات...")
    
    audio_file = f"audio_{chat_id}.mp3"
    
    try:
        # استخدام مكتبة جوجل المستقرة والتي لا تتعرض للحظر أبداً
        tts = gTTS(text=text, lang='ar', slow=False)
        tts.save(audio_file)
        
        # إرسال المقطع الصوتي للمستخدم
        with open(audio_file, 'rb') as audio:
            bot.send_audio(
                chat_id, 
                audio, 
                title="تسجيل صوتي", 
                performer="المعلق (AI)"
            )
            
        # حذف رسالة الانتظار وتنظيف الملفات المؤقتة
        bot.delete_message(chat_id, msg.message_id)
        if os.path.exists(audio_file):
            os.remove(audio_file)
            
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error: {error_details}")
        bot.edit_message_text(f"❌ حدث خطأ:\n{str(e)}", chat_id, msg.message_id)

print("البوت يعمل الآن ومستعد لاستقبال الرسائل...")
bot.infinity_polling()
