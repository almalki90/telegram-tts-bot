import requests
import json
import random
import os
import datetime
from huggingface_hub import InferenceClient

# Tokens
HF_TOKEN = os.environ.get("HF_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1003884004969"

def get_on_this_day_event():
    today = datetime.datetime.now()
    month = today.month
    day = today.day
    
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month:02d}/{day:02d}"
    headers = {"User-Agent": "HistoricalBot/1.0"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            events = response.json().get("events", [])
            if events:
                event = random.choice(events)
                year = event.get("year", "Unknown")
                text = event.get("text", "")
                pages = event.get("pages", [])
                details = pages[0].get("extract", "") if pages else ""
                return f"Year {year}: {text}. {details}"
    except Exception as e:
        print(f"Error fetching from Wikipedia: {e}")
    
    return "Year 1912: The RMS Titanic sinks in the North Atlantic Ocean after hitting an iceberg during her maiden voyage."

def generate_story(event_text):
    client = InferenceClient(token=HF_TOKEN)
    prompt = f"""
    أنت راوي قصص تاريخي محترف وكاتب مبدع. 
    اقرأ هذه الحقيقة التاريخية التي حدثت في "مثل هذا اليوم" باللغة الإنجليزية: 
    "{event_text}"
    
    أعد صياغتها باللغة العربية على شكل قصة مشوقة جداً ومثيرة للانتباه، كأنك تروي رواية تاريخية. 
    اجعل الأسلوب جذاباً، استخدم فقرات قصيرة، وأضف بعض الإيموجي المناسبة. 
    في النهاية، ضع هاشتاقات مناسبة مثل #حدث_في_مثل_هذا_اليوم #قصص_تاريخية.
    """
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating story: {e}")
        return None

def generate_image(event_text):
    client = InferenceClient(token=HF_TOKEN)
    prompt = f"A highly detailed cinematic historical painting or photograph representing: {event_text[:100]}"
    try:
        image = client.text_to_image(prompt, model="stabilityai/stable-diffusion-xl-base-1.0")
        image_path = "history_image.png"
        image.save(image_path)
        return image_path
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

def send_to_telegram(text, image_path=None):
    if image_path and os.path.exists(image_path):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(image_path, "rb") as photo:
            payload = {"chat_id": CHANNEL_ID, "caption": text[:1024]}
            if len(text) > 1024:
                payload["caption"] = "قصة تاريخية جديدة 👇 (حدث في مثل هذا اليوم)"
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
    print("Fetching historical event for TODAY...")
    event = get_on_this_day_event()
    print(f"Event: {event}")
    
    print("Generating story with Qwen...")
    story = generate_story(event)
    if not story:
        print("Failed to generate story. Exiting.")
        return
    
    print("Generating image...")
    image_path = generate_image(event)
    
    print("Sending to Telegram channel...")
    send_to_telegram(story, image_path)
    print("Done!")

if __name__ == "__main__":
    main()
