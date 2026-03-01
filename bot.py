import requests
import json
import random
import os
import re
from huggingface_hub import InferenceClient

# Tokens
HF_TOKEN = os.environ.get("HF_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1003884004969"

def get_random_historical_event():
    # Fetch random historical events from Wikipedia API
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    
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
    
    # Fallback event
    return "Year 1912: The RMS Titanic sinks in the North Atlantic Ocean after hitting an iceberg during her maiden voyage."

def generate_story(event_text):
    client = InferenceClient(api_key=HF_TOKEN)
    prompt = f"""
    أنت راوي قصص تاريخي محترف وكاتب مبدع. 
    اقرأ هذه الحقيقة التاريخية التالية باللغة الإنجليزية: 
    "{event_text}"
    
    أعد صياغتها باللغة العربية على شكل قصة مشوقة جداً ومثيرة للانتباه، كأنك تروي رواية. 
    اجعل الأسلوب جذاباً، استخدم فقرات قصيرة، وأضف بعض الإيموجي المناسبة. 
    في النهاية، ضع هاشتاقات مناسبة.
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500 # Increased to allow room for DeepSeek's thinking process
        )
        content = response.choices[0].message.content
        # Remove <think> blocks
        clean_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return clean_content
    except Exception as e:
        print(f"Error generating story: {e}")
        return None

def generate_image(event_text):
    client = InferenceClient(api_key=HF_TOKEN)
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
    print("Fetching historical event...")
    event = get_random_historical_event()
    print(f"Event: {event}")
    
    print("Generating story...")
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
