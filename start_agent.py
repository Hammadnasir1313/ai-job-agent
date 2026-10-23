# Starts everything for WhatsApp replies:
#   1. Cloudflare tunnel  (gives my computer a public address)
#   2. Tells WasenderAPI the new address (it changes every start)
#   3. whatsapp_server.py  (listens for "YES 3" / "NO 3")
# Run:  double-click start_agent.bat
# auto_agent.py also uses these functions to start everything by itself.

import os
import re
import subprocess
import sys
import threading
import time

import requests
from dotenv import load_dotenv

load_dotenv()
CLOUDFLARED = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
TOKEN = os.getenv("WASENDER_PERSONAL_TOKEN")
API = "https://www.wasenderapi.com/api"
NO_WINDOW = subprocess.CREATE_NO_WINDOW


def start_tunnel():
    # Start the tunnel and wait for its address (like https://abc-def.trycloudflare.com)
    tunnel = subprocess.Popen(
        [CLOUDFLARED, "tunnel", "--no-autoupdate", "--url", "http://localhost:5000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=NO_WINDOW,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        found = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", tunnel.stdout.readline())
        if found:
            # Keep reading the tunnel's messages in the background, so it never gets stuck
            threading.Thread(target=lambda: [None for _ in tunnel.stdout], daemon=True).start()
            print("Tunnel started:", found.group())
            return tunnel, found.group()
    tunnel.kill()
    return None, None


def update_webhook(address):
    # Tell WasenderAPI to send my WhatsApp messages to the new address.
    # Returns the webhook secret (password), or None.
    headers = {"Authorization": f"Bearer {TOKEN}"}
    sessions = requests.get(f"{API}/whatsapp-sessions", headers=headers, timeout=30).json()
    session_id = sessions["data"][0]["id"]

    # A new tunnel address takes a little time to work on the internet, so retry for up to 2 minutes
    print("Telling WasenderAPI the new address (can take a minute)...")
    for attempt in range(1, 13):
        update = requests.put(
            f"{API}/whatsapp-sessions/{session_id}",
            headers=headers,
            json={
                "webhook_url": f"{address}/webhook",
                "webhook_enabled": True,
                "webhook_events": ["messages.upsert"],
            },
            timeout=30,
        )
        if update.ok or update.status_code != 422:
            break
        time.sleep(10)

    if not update.ok:
        print("Could not update WasenderAPI webhook:", update.status_code, update.text)
        return None
    print("WasenderAPI webhook updated ✅")
    return (update.json().get("data") or {}).get("webhook_secret")


def server_env(secret):
    # The webhook secret comes back from WasenderAPI, so I don't need to copy it
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if secret:
        env["WASENDER_WEBHOOK_SECRET"] = secret
        print("Webhook secret received ✅")
    else:
        print("No webhook secret from WasenderAPI. Using WASENDER_WEBHOOK_SECRET from .env")
    return env


if __name__ == "__main__":
    if not TOKEN or "paste" in TOKEN:
        print("Please put your WasenderAPI Personal Access Token in .env (WASENDER_PERSONAL_TOKEN=...)")
        input("Press Enter to close...")
        sys.exit()

    tunnel, address = start_tunnel()
    if not tunnel:
        print("Could not start the tunnel. Check your internet and try again.")
        input("Press Enter to close...")
        sys.exit()

    env = server_env(update_webhook(address))

    # Start the server in this window (Ctrl+C or close the window to stop)
    try:
        subprocess.run([sys.executable, "whatsapp_server.py"], env=env)
    finally:
        tunnel.kill()
