# Step 5b: listen for my WhatsApp replies.
#   "YES 3" -> apply to job #3
#   "NO 3"  -> skip job #3
# Run:  python whatsapp_server.py   (or double-click start_agent.bat)

import os
import re
import threading

import requests
from dotenv import load_dotenv
from flask import Flask, request

from apply import apply_to_job, skip_job
from send_whatsapp import send_whatsapp

load_dotenv()
WEBHOOK_SECRET = os.getenv("WASENDER_WEBHOOK_SECRET")
MY_NUMBER = re.sub(r"\D", "", os.getenv("MY_WHATSAPP", ""))  # digits only
# WhatsApp sometimes names my own chat with a code like "123456@lid" instead of my number.
# If the server prints "Ignored ... from chat 123456@lid", put that code here in .env.
MY_CHAT_IDS = [c.strip() for c in os.getenv("MY_CHAT_IDS", "").split(",") if c.strip()]

COMMAND = re.compile(r"^\s*(yes|no)\s*#?(\d+)\s*$", re.I)

app = Flask(__name__)
lock = threading.Lock()  # handle one reply at a time
done_messages = set()  # WhatsApp can send the same message twice; do it once


def is_my_chat(chat):
    # A chat is mine if it has my number, e.g. "923001234567@s.whatsapp.net".
    if MY_NUMBER in chat or chat in MY_CHAT_IDS:
        return True
    # WhatsApp sometimes uses a code instead, e.g. "123456789012345@lid".
    # Ask WasenderAPI which phone number the code belongs to.
    if chat.endswith("@lid"):
        response = requests.get(
            f"https://www.wasenderapi.com/api/pn-from-lid/{chat}",
            headers={"Authorization": f"Bearer {os.getenv('WASENDER_API_KEY')}"},
            timeout=30,
        )
        number = (response.json().get("data") or {}).get("pn", "") if response.ok else ""
        if MY_NUMBER in number:
            MY_CHAT_IDS.append(chat)  # remember it, no need to ask again
            return True
    return False


def handle(answer, job_id):
    with lock:
        if answer == "yes":
            send_whatsapp(f"⏳ Applying to job #{job_id}...")
            result = apply_to_job(job_id, ask_me=False)
        else:
            result = skip_job(job_id)
        print(result)
        send_whatsapp(result)


@app.route("/", methods=["GET"])
def home():
    return "Job agent is running."


@app.route("/webhook", methods=["POST"])
def webhook():
    # 1. Make sure the message really comes from WasenderAPI
    if not WEBHOOK_SECRET or request.headers.get("X-Webhook-Signature") != WEBHOOK_SECRET:
        return "unauthorized", 401

    data = (request.get_json(silent=True) or {}).get("data", {})
    messages = data.get("messages") or []
    if isinstance(messages, dict):
        messages = [messages]

    for msg in messages:
        key = msg.get("key", {})
        text = msg.get("messageBody") or ""
        sender = re.sub(r"\D", "", key.get("cleanedSenderPn") or "")

        # 2. Only "YES 3" or "NO 3"
        match = COMMAND.match(text)
        if not match or key.get("id") in done_messages:
            continue

        # 3. Only listen to ME, in my "Message yourself" chat.
        #    (My number is linked, so messages I send to friends also arrive here.)
        chat = key.get("remoteJid") or ""
        if not ((key.get("fromMe") or sender == MY_NUMBER) and is_my_chat(chat)):
            print(f"Ignored '{text}' from chat {chat} (not my own chat)")
            continue
        done_messages.add(key.get("id"))

        answer, job_id = match.group(1).lower(), int(match.group(2))
        print(f"Got '{text}' from WhatsApp")
        # Do the work in the background so WasenderAPI gets a fast answer
        threading.Thread(target=handle, args=(answer, job_id)).start()

    return "ok", 200


if __name__ == "__main__":
    if not WEBHOOK_SECRET:
        print("WARNING: WASENDER_WEBHOOK_SECRET is missing in .env, all messages will be refused.")
    print("Listening for WhatsApp replies on http://localhost:5000/webhook")
    app.run(port=5000)
