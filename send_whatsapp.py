# Step 4: send a WhatsApp message to myself using WasenderAPI.
# Run:  python send_whatsapp.py "Hello from my job agent!"

import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("WASENDER_API_KEY")
MY_NUMBER = os.getenv("MY_WHATSAPP")


def send_whatsapp(text):
    # Returns True if the message was sent.
    # The free trial allows 1 message per minute, so if we are too fast, wait and retry.
    for attempt in range(1, 4):
        response = requests.post(
            "https://www.wasenderapi.com/api/send-message",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"to": MY_NUMBER, "text": text},
            timeout=30,
        )
        if response.ok:
            print("WhatsApp sent!")
            return True
        if response.status_code == 429:
            wait = int(response.json().get("retry_after", 60)) + 2
            print(f"WhatsApp limit reached. Waiting {wait} seconds ({attempt}/3)...")
            time.sleep(wait)
            continue
        print("Could not send WhatsApp:", response.status_code, response.text)
        return False

    print("Could not send WhatsApp after 3 tries.")
    return False


if __name__ == "__main__":
    send_whatsapp(sys.argv[1])
