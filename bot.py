import telebot
import subprocess
import os

# نجلب التوكن بأمان من جيت هاب سيكرتس
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: BOT_TOKEN is missing!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 أهلاً بك! \nأرسل لي أي نص عربي وسأقوم بتحويله إلى مقطع صوتي بصوت المذيع حامد فوراً.")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text
    chat_id = message.chat.id
    
    # رسالة انتظار
    msg = bot.reply_to(message, "⏳ جاري تجهيز المقطع الصوتي، لحظات...")
    
    text_file = f"text_{chat_id}.txt"
    audio_file = f"audio_{chat_id}.mp3"
    
    try:
        # 1. حفظ النص في ملف لتجنب أخطاء النصوص الطويلة
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(text)
        
        # 2. توليد الصوت باستخدام مكتبة مايكروسوفت
        subprocess.run(["edge-tts", "--voice", "ar-SA-HamedNeural", "-f", text_file, "--write-media", audio_file], check=True)
        
        # 3. إرسال المقطع الصوتي للمستخدم
        with open(audio_file, 'rb') as audio:
            bot.send_audio(
                chat_id, 
                audio, 
                title="تسجيل صوتي", 
                performer="المعلق حامد (AI)"
            )
            
        # 4. حذف رسالة الانتظار وتنظيف الملفات المؤقتة
        bot.delete_message(chat_id, msg.message_id)
        if os.path.exists(text_file):
            os.remove(text_file)
        if os.path.exists(audio_file):
            os.remove(audio_file)
            
    except Exception as e:
        print(f"Error: {e}")
        bot.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.", chat_id, msg.message_id)

print("البوت يعمل الآن ومستعد لاستقبال الرسائل...")
bot.infinity_polling()
