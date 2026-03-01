import requests
import random
import os
import re
import json
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# Tokens
HF_TOKEN = os.environ.get("HF_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1003884004969"

# Public domain books URLs (Historical Anecdotes, Oddities, etc.)
BOOKS = [
    "https://www.gutenberg.org/cache/epub/43632/pg43632.txt", # Historic Oddities
    "https://www.gutenberg.org/cache/epub/24518/pg24518.txt", # Extraordinary Popular Delusions
    "https://www.gutenberg.org/cache/epub/52562/pg52562.txt", # Curiosities of History
    "https://www.gutenberg.org/cache/epub/10940/pg10940.txt"  # Ten Thousand Wonderful Things
]

def download_arabic_font():
    font_path = "Cairo-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Bold.ttf"
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
            # Remove Project Gutenberg header/footer roughly
            start_index = int(len(text) * random.uniform(0.15, 0.80))
            # Get a chunk of 4000 characters
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
    الذكاء الاصطناعي عادة يختصر، لكنك لن تفعل ذلك! اكتب القصة بشكل متكامل ومقسم إلى:
    1. مقدمة غامضة ومثيرة.
    2. صلب القصة والتفاصيل (الحبكة).
    3. الخاتمة أو العبرة.
    
    يجب أن توفر إجابتك بصيغة JSON حصرية، كالتالي:
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
        # Clean markdown formatting if present
        if content.startswith("```json"):
            content = content[7:-3].strip()
            
        data = json.loads(content)
        return data["title"], data["story"], data["image_prompt"]
    except Exception as e:
        print(f"Error generating story: {e}")
        return None, None, None

def add_arabic_text_to_image(image_path, text, font_path):
    try:
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        
        # Create a drawing context for overlay
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Draw a dark gradient at the bottom for text readability
        rect_height = int(height * 0.25)
        for i in range(rect_height):
            alpha = int(200 * (i / rect_height))
            draw.line([(0, height - rect_height + i), (width, height - rect_height + i)], fill=(0, 0, 0, alpha))
        
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # Reshape and adjust Arabic text
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        
        # Calculate font size
        font_size = int(height * 0.06)
        font = ImageFont.truetype(font_path, font_size)
        
        # Calculate text bounds
        bbox = draw.textbbox((0, 0), bidi_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position text at the bottom center
        x = (width - text_width) / 2
        y = height - rect_height + (rect_height - text_height) / 2
        
        # Draw text with stroke for better visibility
        stroke_color = (0, 0, 0, 255)
        text_color = (255, 215, 0, 255) # Goldish color
        draw.text((x, y), bidi_text, font=font, fill=text_color, stroke_width=2, stroke_fill=stroke_color)
        
        output_path = "history_image_with_title.png"
        img.convert("RGB").save(output_path)
        return output_path
    except Exception as e:
        print(f"Error drawing text: {e}")
        return image_path

def generate_image_with_title(image_prompt, title, font_path):
    client = InferenceClient(token=HF_TOKEN)
    try:
        # Generate base image
        image = client.text_to_image(image_prompt, model="stabilityai/stable-diffusion-xl-base-1.0")
        base_image_path = "base_image.png"
        image.save(base_image_path)
        
        # Add Arabic title overlay
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
                # Send the rest in chunks
                for i in range(0, len(text), 4096):
                    requests.post(text_url, json={"chat_id": CHANNEL_ID, "text": text[i:i+4096]})
            else:
                requests.post(url, data=payload, files={"photo": photo})
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        for i in range(0, len(text), 4096):
            requests.post(url, json={"chat_id": CHANNEL_ID, "text": text[i:i+4096]})

def main():
    print("Downloading font...")
    font_path = download_arabic_font()
    
    print("Fetching historical excerpt from Gutenberg...")
    excerpt = get_random_gutenberg_excerpt()
    
    print("Generating detailed story and title...")
    title, story, image_prompt = generate_story_and_title(excerpt)
    
    if not story:
        print("Failed to generate story. Exiting.")
        return
        
    print(f"Title: {title}")
    
    print("Generating image and overlaying Arabic title...")
    image_path = generate_image_with_title(image_prompt, title, font_path)
    
    print("Sending to Telegram channel...")
    send_to_telegram(f"✨ **{title}**\n\n{story}", image_path)
    print("Done!")

if __name__ == "__main__":
    main()
