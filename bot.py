import requests
import random
import os
import json
import textwrap
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFont

# Tokens
HF_TOKEN = os.environ.get("HF_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1003884004969"

BOOKS = [
    "https://www.gutenberg.org/cache/epub/43632/pg43632.txt",
    "https://www.gutenberg.org/cache/epub/24518/pg24518.txt",
    "https://www.gutenberg.org/cache/epub/52562/pg52562.txt",
    "https://www.gutenberg.org/cache/epub/10940/pg10940.txt"
]

def download_arabic_font():
    font_path = "Tajawal-Black.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Black.ttf"
        r = requests.get(url)
        with open(font_path, 'wb') as f:
            f.write(r.content)
    return font_path

def get_random_gutenberg_excerpt():
    url = random.choice(BOOKS)
    headers = {"User-Agent": "HistoricalBot/1.0"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            text = response.text
            start_index = int(len(text) * random.uniform(0.15, 0.80))
            chunk = text[start_index:start_index+4000]
            return chunk
    except Exception as e:
        print(f"Error fetching book: {e}")
    return "In 1800s, a strange event occurred where a whole village started dancing uncontrollably."

def generate_story_and_title(excerpt):
    client = InferenceClient(token=HF_TOKEN)
    prompt = f"""
    أنت راوي قصص تاريخي بشري محترف.
    اقرأ هذا المقتطف من كتاب تاريخي قديم:
    "{excerpt}"
    
    استخرج الحدث التاريخي من هذا النص، واكتبه باللغة العربية بأسلوب بشري طبيعي جداً.
    
    شروط السرد الصارمة:
    1. **يجب** أن تبدأ القصة دائماً بذكر التاريخ (مثلاً: "في عام 1800م، ..." أو "في القرن الخامس عشر، ...").
    2. اكتب القصة كاملة بدون اختصار مخل وبدون تمطيط ممل.
    3. ضع التشكيل (الحركات) فقط على الكلمات الصعبة التي قد يُخطئ القارئ في نطقها، ولا تشكل كل الحروف.
    4. قسم القصة إلى 3 فقرات متصلة (بداية، ذروة، ونهاية).
    
    يجب أن توفر إجابتك بصيغة JSON حصرياً كالتالي:
    {{
      "title": "عنوان جذاب جدا ومثير للقصة (لا يتجاوز 6 كلمات)",
      "image_prompt": "A highly detailed cinematic historical painting representing the core event, dramatic lighting, 8k",
      "story": "القصة كاملة هنا ومقسمة لفقرات مع إيموجي خفيفة وهاشتاقات"
    }}
    
    أعطني الـ JSON فقط بدون أي نص إضافي.
    """
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        data = json.loads(content)
        return data["title"], data["story"], data["image_prompt"]
    except Exception as e:
        print(f"Error generating story: {e}")
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
    try:
        image = client.text_to_image(image_prompt, model="stabilityai/stable-diffusion-xl-base-1.0")
        base_image_path = "base_image.png"
        image.save(base_image_path)
        final_image_path = add_arabic_text_to_image(base_image_path, title, font_path)
        return final_image_path
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

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
    excerpt = get_random_gutenberg_excerpt()
    title, story, image_prompt = generate_story_and_title(excerpt)
    
    if not story:
        print("Failed to generate story. Exiting.")
        return
        
    print(f"Title: {title}")
    image_path = generate_image_with_title(image_prompt, title, font_path)
    send_to_telegram(f"✨ **{title}**\n\n{story}", image_path)
    print("Done!")

if __name__ == "__main__":
    main()
