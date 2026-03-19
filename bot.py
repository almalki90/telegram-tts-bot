import requests
import random
import os
import json
import textwrap
import time
import math
from google import genai
from google.genai import types
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFont

# Tokens
HF_TOKEN = os.environ.get("HF_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1003884004969"

BOOKS = [
    # أمهات الكتب والمصادر العربية الضخمة
    ("البداية والنهاية لابن كثير", 9000),
    ("تاريخ الطبري (رسل وملوك)", 6000),
    ("الكامل في التاريخ لابن الأثير", 8000),
    ("مروج الذهب ومعادن الجوهر للمسعودي", 2000),
    ("عجائب الآثار في التراجم والأخبار للجبرتي", 2500),
    ("تاريخ ابن خلدون", 3000),
    
    # مراجع تاريخ الشرق الأوسط والإسلام (إنجليزية ضخمة)
    ("A History of the Arab Peoples by Albert Hourani", 600),
    ("The Middle East: A Brief History of the Last 2,000 Years by Bernard Lewis", 500),
    ("The Crusades Through Arab Eyes by Amin Maalouf", 350),
    ("The Great Arab Conquests by Hugh Kennedy", 450),
    ("Destiny Disrupted: A History of the World Through Islamic Eyes", 450),
    ("Osman's Dream: The History of the Ottoman Empire", 700),
    ("A Peace to End All Peace: The Fall of the Ottoman Empire", 650),
    
    # موسوعات تاريخية عالمية ضخمة (World History Encyclopedias)
    ("The Story of Civilization by Will Durant", 10000),
    ("The History of the Decline and Fall of the Roman Empire by Edward Gibbon", 3500),
    ("The Cambridge Ancient History", 9000),
    ("The Cambridge Medieval History", 8000),
    ("The Outline of History by H. G. Wells", 1200),
    
    # الموسوعات الأجنبية من المشروع السابق (غرائب، جرائم تاريخية، وألغاز)
    ("The Mammoth Book of Bizarre Crimes", 500),
    ("The Encyclopedia of Unsolved Crimes", 450),
    ("The Mammoth Book of Historical Whodunnits", 600),
    ("The Mammoth Book of Unexplained Phenomena", 600),
    ("The Book of Extraordinary Historical Mysteries", 400),
    ("Mysteries of History by Robert Stewart", 450),
    ("Historical Enigmas of the Middle Ages", 350),
    ("Secret Societies and Subversive Movements in History", 450),
    ("The Vatican Secret Archives: Mysteries Revealed", 350)
]

def get_seeded_book_and_page():
    # الحصول على رقم الساعة الحالي (منذ عام 1970)
    current_hour = int(time.time() / 3600)
    
    # استخدام رقم الساعة كبذرة (Seed) لا تتكرر أبداً
    random.seed(current_hour)
    
    # اختيار كتاب بناءً على البذرة
    book_title, max_pages = random.choice(BOOKS)
    
    # اختيار رقم صفحة بناءً على البذرة (تجنب الصفحات الأولى لأنها غالباً فهارس)
    page_number = random.randint(20, max_pages)
    
    # إعادة تصفير البذرة حتى لا يؤثر على باقي أجزاء الكود التي تحتاج عشوائية حقيقية
    random.seed(time.time())
    
    return book_title, page_number

def download_arabic_font():
    font_path = "Tajawal-Black.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Black.ttf"
        r = requests.get(url)
        with open(font_path, 'wb') as f:
            f.write(r.content)
    return font_path

def generate_story_and_title(book_title, page_number):
    prompt = f"""
    أنت باحث تاريخي خبير ومحقق متخصص في تاريخ الشرق الأوسط (بجميع دوله وعصوره القديمة والحديثة). أنت تبحث دائماً عن الأحداث النادرة والقصص غير المشهورة التي لا يعرفها الكثيرون.
    
    مهمتك الانطلاق فوراً والبحث في الكتاب/الموسوعة التالية:
    "{book_title}"
    وتحديداً ابحث في أحداث وأروقة هذا الكتاب بالقرب من الصفحة رقم {page_number}.
    
    استخرج حدثاً تاريخياً واحداً غامضاً، أو قصة حقيقية، أو لغزاً مسجلاً في هذا الجزء من الكتاب. **(إذا كان الكتاب عالمياً، ابحث عن تقاطع أو قصة تخص الشرق الأوسط أو العرب أو المسلمين في تلك الحقبة، وإذا لم تجد، اسرد أندر قصة موجودة في تلك الصفحة).**
    
    شروط السرد الصارمة جداً:
    1. **مدة القراءة:** اختصر الحدث التاريخي بذكاء شديد وبدون إخلال بالمعنى، ليكون مناسباً للقراءة الصوتية بحيث **لا يتجاوز دقيقتين (يجب أن يكون النص بين 200 إلى 250 كلمة كحد أقصى)**.
    2. **يجب** أن تبدأ القصة بذكر الزمان والمكان مباشرة (مثلاً: "في عام كذا في مدينة كذا...").
    3. قسّم السرد إلى **مقاطع قصيرة جداً (فقرات تشبه التغريدات)**، بحيث يفصل بين كل مقطع وآخر سطر فارغ لتسهيل القراءة.
    4. **لا تكتب أي عناوين فرعية على الإطلاق** (لا تستخدم كلمات مثل: بداية القصة، تصاعد الأحداث، النهاية، العبرة).
    5. **تجنب ذكر أي عبرة أو دروس مستفادة**. فقط اسرد الحدث التاريخي وتوقف بمجرد انتهاء الحدث.
    6. ضع التشكيل على الكلمات التي قد يُخطئ القارئ في نطقها.
    7. اكتب بأسلوب بشري جذاب، درامي، ومثير للاهتمام يشد المستمع.
    
    يجب أن توفر إجابتك بصيغة JSON حصرياً كالتالي (بدون أي نص إضافي خارجه):
    {{
      "title": "عنوان جذاب للقصة (لا يتجاوز 6 كلمات)",
      "image_prompt": "A highly detailed semi-realistic anime style illustration representing the core event, lifelike anime characters, 2.5D anime, cinematic lighting, 8k, masterpiece",
      "story": "القصة المسرودة هنا (250 كلمة كحد أقصى) بشكل متصل بدون أي عناوين فرعية وبدون عبرة"
    }}
    """
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        content = response.text.strip()
        
        data = json.loads(content)
        
        story = data.get("story", "")
        unwanted_phrases = ["بداية القصة:", "تصاعد الأحداث:", "ذروة الحدث:", "النهاية:", "الخاتمة:", "العبرة:", "الدروس المستفادة:", "بداية القصة", "تصاعد الأحداث", "ذروة الحدث", "النهاية", "الخاتمة", "العبرة", "الدروس المستفادة"]
        for phrase in unwanted_phrases:
            story = story.replace(phrase, "")
            
        return data.get("title", "قصة تاريخية مثيرة"), story, data.get("image_prompt", "cinematic historical painting 8k")
    except Exception as e:
        print(f"Error generating story with Gemini: {e}")
        return None, None, None

def resize_to_tiktok_format(img):
    target_width = 1080
    target_height = 1920
    img_ratio = img.width / img.height
    target_ratio = target_width / target_height

    if img_ratio > target_ratio:
        new_height = target_height
        new_width = int(new_height * img_ratio)
    else:
        new_width = target_width
        new_height = int(new_width / img_ratio)

    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = (new_width - target_width) / 2
    top = (new_height - target_height) / 2
    right = (new_width + target_width) / 2
    bottom = (new_height + target_height) / 2
    
    return img.crop((left, top, right, bottom))

def add_arabic_text_to_image(image_path, text, font_path):
    try:
        img = Image.open(image_path).convert("RGBA")
        img = resize_to_tiktok_format(img)
        width, height = img.size
        
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        font_size = int(height * 0.06) 
        font = ImageFont.truetype(font_path, font_size)
        
        channel_text = "قناتنا على التليجرام @qsshistory"
        channel_font_size = int(height * 0.025)
        channel_font = ImageFont.truetype(font_path, channel_font_size)
        
        lines = textwrap.wrap(text, width=16)
        
        line_heights = []
        line_widths = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append(bbox[3] - bbox[1])
            
        c_bbox = draw.textbbox((0, 0), channel_text, font=channel_font)
        c_width = c_bbox[2] - c_bbox[0]
        c_height = c_bbox[3] - c_bbox[1]
            
        total_title_height = sum(line_heights) + (len(lines) - 1) * 20
        total_text_height = total_title_height + 40 + c_height 
        max_line_width = max(max(line_widths) if line_widths else 0, c_width)
        
        box_padding_x = 80
        box_padding_y = 60
        box_width = max_line_width + box_padding_x * 2
        box_height = total_text_height + box_padding_y * 2
        
        box_x1 = (width - box_width) / 2
        box_y1 = height * 0.65 - (box_height / 2) 
        box_x2 = box_x1 + box_width
        box_y2 = box_y1 + box_height
        
        draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=40, fill=(0, 0, 0, 180))
        
        y_start = box_y1 + box_padding_y
        for i, line in enumerate(lines):
            draw.text(
                (width / 2, y_start),
                line,
                font=font,
                fill=(255, 215, 0, 255), 
                direction="rtl",
                align="center",
                anchor="ma" 
            )
            y_start += line_heights[i] + 20
            
        y_start += 20 
        draw.text(
            (width / 2, y_start),
            channel_text,
            font=channel_font,
            fill=(220, 220, 220, 255),
            direction="rtl",
            align="center",
            anchor="ma"
        )
        
        img = Image.alpha_composite(img, overlay)
        output_path = "history_image_with_title.png"
        img.convert("RGB").save(output_path)
        return output_path
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error drawing text: {e}")
        return image_path

def generate_image_with_title(image_prompt, title, font_path):
    client = InferenceClient(token=HF_TOKEN)
    base_image_path = "base_image.png"
    image_success = False
    
    # محاولة توليد الصورة مع نموذج بديل في حال فشل النموذج الأول
    models_to_try = [
        "stabilityai/stable-diffusion-xl-base-1.0",
        "prompthero/openjourney" 
    ]
    
    for model in models_to_try:
        try:
            print(f"Attempting image generation with {model}...")
            image = client.text_to_image(image_prompt, model=model)
            image.save(base_image_path)
            image_success = True
            break
        except Exception as e:
            print(f"Error generating image with {model}: {e}")
            
    # في حال فشل التوليد تماماً، إنشاء خلفية افتراضية أنيقة
    if not image_success:
        print("Falling back to a solid background image.")
        fallback_img = Image.new('RGB', (1080, 1920), color=(25, 30, 40))
        fallback_img.save(base_image_path)
        
    final_image_path = add_arabic_text_to_image(base_image_path, title, font_path)
    return final_image_path

def send_to_telegram(text, image_path=None):
    if image_path and os.path.exists(image_path):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(image_path, "rb") as photo:
            payload = {"chat_id": CHANNEL_ID, "caption": text[:1024]}
            if len(text) > 1024:
                payload["caption"] = "قصة تاريخية جديدة 👇"
                requests.post(url, data=payload, files={"photo": photo})
                text_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                for i in range(0, len(text), 4096):
                    requests.post(text_url, json={"chat_id": CHANNEL_ID, "text": text[i:i+4096]})
            else:
                requests.post(url, data=payload, files={"photo": photo})
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        for i in range(0, len(text), 4096):
            requests.post(url, json={"chat_id": CHANNEL_ID, "text": text[i:i+4096]})

def main():
    font_path = download_arabic_font()
    
    book_title, page_number = get_seeded_book_and_page()
    print(f"Targeting book: {book_title}, near page {page_number}")
    
    title, story, image_prompt = generate_story_and_title(book_title, page_number)
    
    if not story:
        print("Failed to generate story. Exiting.")
        import sys
        sys.exit(1)
        
    print(f"Title: {title}")
    image_path = generate_image_with_title(image_prompt, title, font_path)
    
    final_text = f"✨ **{title}**\n\n{story}\n\n📚 **المصدر:** من أروقة كتاب ({book_title})"
    
    send_to_telegram(final_text, image_path)
    print("Done!")

if __name__ == "__main__":
    main()
