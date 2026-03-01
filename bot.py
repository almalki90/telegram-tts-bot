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
    font_path = "Amiri-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf"
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
    أنت راوي قصص تاريخي محترف تستهدف جمهوراً يعشق الغموض والإثارة.
    اقرأ هذا المقتطف من كتاب تاريخي قديم:
    "{excerpt}"
    
    مهمتك هي استخراج قصة تاريخية أو حدث غريب من هذا النص، وكتابته باللغة العربية بتفصيل ممتع.
    اكتب القصة بشكل متكامل ومقسم إلى:
    1. مقدمة غامضة ومثيرة.
    2. صلب القصة والتفاصيل.
    3. الخاتمة أو العبرة.
    
    يجب أن توفر إجابتك بصيغة JSON حصرياً كالتالي:
    {{
      "title": "عنوان جذاب جدا ومثير للقصة (لا يتجاوز 6 كلمات)",
      "image_prompt": "A highly detailed cinematic historical painting representing the core event, dramatic lighting, 8k",
      "story": "القصة كاملة هنا ومقسمة لفقرات مع إيموجي وهاشتاقات"
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

def add_arabic_text_to_image(image_path, text, font_path):
    try:
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Bottom gradient for title
        rect_height = int(height * 0.25)
        for i in range(rect_height):
            alpha = int(200 * (i / rect_height))
            draw.line([(0, height - rect_height + i), (width, height - rect_height + i)], fill=(0, 0, 0, alpha))
            
        # Top gradient for channel name
        top_rect_height = int(height * 0.15)
        for i in range(top_rect_height):
            alpha = int(180 * (1 - (i / top_rect_height)))
            draw.line([(0, i), (width, i)], fill=(0, 0, 0, alpha))
        
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # 1. Draw Title natively using Pillow 10+ with direction="rtl" and textwrap
        font_size = int(height * 0.055)
        font = ImageFont.truetype(font_path, font_size)
        
        # Wrap the text so it doesn't overflow
        lines = textwrap.wrap(text, width=28)
        
        # Center coordinates
        x = width / 2
        y_start = height - rect_height + (rect_height / 2) - ((len(lines) * font_size) / 2)
        
        stroke_color = (0, 0, 0, 255)
        text_color = (255, 215, 0, 255) # Gold
        
        for line in lines:
            draw.text(
                (x, y_start),
                line,
                font=font,
                fill=text_color,
                stroke_width=2,
                stroke_fill=stroke_color,
                direction="rtl",
                align="center",
                anchor="mm"
            )
            y_start += font_size + 10 # spacing between lines
        
        # 2. Draw Channel Name
        channel_text = "قناتنا على التليجرام @qsshistory"
        channel_font_size = int(height * 0.035)
        channel_font = ImageFont.truetype(font_path, channel_font_size)
        
        c_y = int(height * 0.05)
        
        draw.text(
            (x, c_y), 
            channel_text, 
            font=channel_font, 
            fill=(255, 255, 255, 200), 
            stroke_width=1, 
            stroke_fill=(0,0,0,255),
            direction="rtl",
            align="center",
            anchor="mm"
        )
        
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
