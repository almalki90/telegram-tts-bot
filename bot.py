import requests
import random
import os
from huggingface_hub import InferenceClient

# Tokens
HF_TOKEN = os.environ.get("HF_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1003884004969"

BOOKS = [
    "https://www.gutenberg.org/cache/epub/43632/pg43632.txt", # Historic Oddities
    "https://www.gutenberg.org/cache/epub/24518/pg24518.txt", # Extraordinary Popular Delusions
    "https://www.gutenberg.org/cache/epub/52562/pg52562.txt", # Curiosities of History
    "https://www.gutenberg.org/cache/epub/44123/pg44123.txt", # Historic incidents
    "https://www.gutenberg.org/cache/epub/10940/pg10940.txt", # Curious myths of the middle ages
    "https://www.gutenberg.org/cache/epub/64010/pg64010.txt"  # Historical Romances
]

def get_random_book_excerpt():
    url = random.choice(BOOKS)
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            text = res.text
            # Skip the first 10% and last 10% to avoid Gutenberg headers/footers/indexes
            start_bound = int(len(text) * 0.15)
            end_bound = int(len(text) * 0.85)
            text = text[start_bound:end_bound]
            
            # Get a random chunk of ~5000 characters (enough context for a story)
            chunk_start = random.randint(0, len(text) - 5000)
            chunk = text[chunk_start:chunk_start+5000]
            return chunk
    except Exception as e:
        print(f"Error fetching book: {e}")
    
    return "In 1518, a strange mania struck Strasbourg where people danced for days without rest..."

def generate_story(excerpt):
    client = InferenceClient(token=HF_TOKEN)
    prompt = f"""
أنت راوي قصص تاريخي محترف وكاتب مبدع جداً. مهمتك هي قراءة هذا المقتطف العشوائي من كتاب تاريخي إنجليزي واستخراج الحدث أو الشخصية التي يتحدث عنها:
"{excerpt}"

التعليمات الصارمة لكتابة القصة:
1. افهم السياق واكتب القصة التاريخية بالكامل باللغة العربية. (حتى لو كان المقتطف مجرد جزء من الحدث، قم بسرد القصة التاريخية المعروفة لهذا الحدث من البداية للنهاية).
2. **إياك والاختصار!** لا تكن كسولاً. قم بسرد الأحداث بتفصيل عميق ومشوق كأنها رواية تاريخية يقرؤها الناس بنهم.
3. قسّم القصة إلى أجزاء لتكون مريحة للقراءة (مثلاً: 🔹 الجزء الأول: البداية الخفية، 🔹 الجزء الثاني: ذروة الأحداث، 🔹 الجزء الثالث: النهاية المفاجئة).
4. استخدم لغة فصحى قوية، إيموجي معبرة في الأماكن المناسبة، وحوارات خيالية قصيرة إن لزم الأمر لزيادة التشويق.
5. في بداية الرد ضع عنواناً نارياً وجذاباً جداً للقصة.
    """
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating story: {e}")
        return None

def generate_cover_image(story):
    client = InferenceClient(token=HF_TOKEN)
    # 1. Summarize story into a prompt
    prompt_maker = f"Based on this story, write a single English sentence describing a cinematic, highly detailed cover image for it. Only output the English sentence. Story: {story[:400]}"
    try:
        res = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[{"role": "user", "content": prompt_maker}],
            max_tokens=100
        )
        img_prompt = res.choices[0].message.content.strip()
        print("Image Prompt:", img_prompt)
        
        # 2. Generate Image
        final_prompt = f"Cinematic historical book cover, masterpiece, highly detailed, dramatic lighting. {img_prompt}"
        image = client.text_to_image(final_prompt, model="stabilityai/stable-diffusion-xl-base-1.0")
        image_path = "cover.png"
        image.save(image_path)
        return image_path
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

def send_to_telegram(story, image_path=None):
    # Split the story into parts (Telegram max is 4096 per message, 1024 per caption)
    # We will send the image with the title/Part 1 as caption. 
    # Then send the remaining parts as separate messages.
    
    parts = story.split("🔹")
    if len(parts) == 1:
        # Fallback split if the AI didn't use the exact emoji
        parts = [story[i:i+4000] for i in range(0, len(story), 4000)]
    else:
        # Re-add the emoji to the parts (except the first one if it's empty or just the title)
        formatted_parts = []
        for i, p in enumerate(parts):
            p = p.strip()
            if p:
                if i > 0:
                    formatted_parts.append("🔹 " + p)
                else:
                    formatted_parts.append(p)
        parts = formatted_parts

    # Send Image + Title/First Part
    first_part = parts[0]
    remaining_parts = parts[1:]

    url_photo = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    url_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as photo:
            # If first part is too long for caption, split it
            if len(first_part) <= 1024:
                requests.post(url_photo, data={"chat_id": CHANNEL_ID, "caption": first_part}, files={"photo": photo})
            else:
                title = first_part[:first_part.find('\n')] if '\n' in first_part else "قصة تاريخية مشوقة 📜"
                requests.post(url_photo, data={"chat_id": CHANNEL_ID, "caption": title + "\n\n(القصة في الأسفل 👇)"}, files={"photo": photo})
                requests.post(url_msg, json={"chat_id": CHANNEL_ID, "text": first_part})
    else:
        requests.post(url_msg, json={"chat_id": CHANNEL_ID, "text": first_part})

    # Send remaining parts
    for part in remaining_parts:
        if len(part) > 4096:
            # Safe split if a single part is still too long
            for i in range(0, len(part), 4000):
                requests.post(url_msg, json={"chat_id": CHANNEL_ID, "text": part[i:i+4000]})
        else:
            requests.post(url_msg, json={"chat_id": CHANNEL_ID, "text": part})

def main():
    print("Fetching random excerpt from historical books...")
    excerpt = get_random_book_excerpt()
    print("Excerpt fetched (length):", len(excerpt))
    
    print("Generating comprehensive story...")
    story = generate_story(excerpt)
    if not story:
        print("Failed to generate story. Exiting.")
        return
    
    print("Generating cinematic cover image...")
    image_path = generate_cover_image(story)
    
    print("Sending story in batches to Telegram...")
    send_to_telegram(story, image_path)
    print("Done!")

if __name__ == "__main__":
    main()
