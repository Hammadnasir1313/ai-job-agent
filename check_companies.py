# Visit each software company's careers page, find matching jobs, send to WhatsApp.
# Run:  python check_companies.py

import json
import re
import time

from jobs import check_page, load_seen, read_page, send_new_good_jobs

# Only ask Gemini about a page if it mentions one of these (saves the free limit)
RELEVANT = re.compile(r"php|laravel|wordpress|full[- ]?stack|web developer|software engineer|software developer", re.I)

with open("companies.json", encoding="utf-8") as f:
    companies = json.load(f)

seen = load_seen()
sent = 0
no_careers_page = []

for company in companies:
    name = company["name"]
    url = company["careers"]
    if not url:
        no_careers_page.append(name)
        continue

    print("Checking:", name)
    try:
        page_text = read_page(url)
    except Exception as e:
        print("   could not open page:", e)
        continue
    if not page_text:
        print("   page blocked or empty, skipping")
        continue
    if not RELEVANT.search(page_text):
        print("   no developer jobs mentioned, skipping")
        continue

    jobs = check_page(url, page_text)
    for job in jobs:
        job["company"] = job.get("company") or name
        # If the page has no apply email, use the company's known HR email
        if company["email"] and job.get("apply") in (None, "", "not found"):
            job["apply"] = company["email"]
    print(f"   {len(jobs)} matching jobs")
    sent += send_new_good_jobs(jobs, seen)
    time.sleep(5)  # small pause so the free Gemini plan doesn't block us

print(f"\nDone. Sent {sent} new jobs to WhatsApp.")
if no_careers_page:
    print("No careers page (check by hand or send an open application):", ", ".join(no_careers_page))
