# Step 6: runs everything by itself, Monday to Friday, when I log in to my laptop.
# Windows Task Scheduler starts this file (hidden, no window).
#   - listens for my WhatsApp replies (YES 3 / NO 3) all day
#   - checks the company websites once per day (from 9 AM)
#   - tells me everything on WhatsApp
# All messages are written to agent.log (open it if something goes wrong).

import datetime
import os
import subprocess
import sys
import time

# Work from this folder, even when Windows starts us from somewhere else
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# No window, so write everything to agent.log
LOG = open("agent.log", "a", encoding="utf-8", buffering=1)
sys.stdout = sys.stderr = LOG

import requests  # noqa: E402

from jobs import load_pending  # noqa: E402
from send_whatsapp import send_whatsapp  # noqa: E402
from start_agent import NO_WINDOW, server_env, start_tunnel, update_webhook  # noqa: E402

PYTHON = sys.executable.replace("pythonw.exe", "python.exe")  # runs other scripts without a window
CHECK_FROM_HOUR = 9  # check jobs once a day, from 9 AM
LAST_CHECK_FILE = "last_check.txt"


def log(text):
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] {text}")


def is_workday():
    return datetime.date.today().weekday() < 5  # Monday=0 ... Friday=4


def checked_today():
    if not os.path.exists(LAST_CHECK_FILE):
        return False
    with open(LAST_CHECK_FILE) as f:
        return f.read().strip() == str(datetime.date.today())


def daily_check():
    log("Daily job check started")
    send_whatsapp("🤖 Good morning! Checking company websites for new jobs...")
    before = len(load_pending())
    subprocess.run(
        [PYTHON, "check_companies.py"],
        stdout=LOG, stderr=LOG, creationflags=NO_WINDOW,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
    )
    new_jobs = len(load_pending()) - before
    with open(LAST_CHECK_FILE, "w") as f:
        f.write(str(datetime.date.today()))
    if new_jobs:
        send_whatsapp(f"📋 Daily check done: {new_jobs} new job(s) sent above.")
    else:
        send_whatsapp("📋 Daily check done: no new matching jobs today.")
    log(f"Daily job check done: {new_jobs} new jobs")


def connect():
    # Start the tunnel + WhatsApp listener. Returns (tunnel, server, address).
    tunnel, address = start_tunnel()
    if not tunnel:
        return None, None, None
    env = server_env(update_webhook(address))
    server = subprocess.Popen(
        [PYTHON, "whatsapp_server.py"], env=env,
        stdout=LOG, stderr=LOG, creationflags=NO_WINDOW,
    )
    return tunnel, server, address


def is_working(address):
    # Can WhatsApp still reach me? (After sleep or Wi-Fi changes, the tunnel can break.)
    try:
        return requests.get(address + "/", timeout=20).ok
    except Exception:
        return False


if not is_workday():
    log("Weekend, not starting.")
    sys.exit()

log("Agent starting")
tunnel = server = address = None

while True:
    # 1. Make sure WhatsApp replies can reach me (start, or restart if broken)
    if not address or not is_working(address):
        for process in (tunnel, server):
            if process:
                process.kill()
        tunnel, server, address = connect()
        if address:
            log("Listening for WhatsApp replies")
        else:
            log("Could not connect, will try again in 15 minutes")

    # 2. Once a day on workdays, from 9 AM: check the companies
    if is_workday() and not checked_today() and datetime.datetime.now().hour >= CHECK_FROM_HOUR:
        daily_check()

    time.sleep(15 * 60)  # look again in 15 minutes
