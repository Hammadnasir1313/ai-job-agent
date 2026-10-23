# Shared helpers: read a web page, let Gemini find + score jobs, remember sent jobs.
# Used by find_jobs.py and check_companies.py.

import json
import os
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ai import ask_gemini
from match_job import profile, resume
from send_whatsapp import send_whatsapp

SEEN_FILE = "seen_jobs.json"  # remembers jobs already sent, so no repeats
PENDING_FILE = "pending_jobs.json"  # good jobs waiting for my YES (used by apply.py)

BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36"}


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def load_pending():
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_pending(pending):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending, f, indent=2, ensure_ascii=False)


def read_page(url):
    # Download a page and turn it into plain text (keeping job links)
    response = requests.get(url, headers=BROWSER, timeout=20)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if len(text) > 10:
            a.replace_with(f"{text} [{urljoin(url, a['href'])}]")
    return soup.get_text(" ", strip=True)[:20000]


def check_page(url, page_text):
    # Ask Gemini to find the jobs on this page and score each one
    prompt = f"""
Below is text from a job or careers page. Find the individual job postings in it.

PERSON'S PROFILE AND JOB RULES:
{profile}

PERSON'S RESUME:
{resume}

PAGE ({url}):
{page_text}

For each job on the page:
1. If it breaks any "Job rules" in the profile (location must be Islamabad or Remote), skip it.
2. Otherwise score it 0-10 against the resume. 8-10 = APPLY, 5-7 = MAYBE, 0-4 = SKIP.

Only use jobs that are really on this page. NEVER invent a job, company, email, or link.

Reply ONLY with a JSON list (or [] if there are no matching jobs):
[
  {{
    "title": "job title",
    "company": "company name",
    "location": "location",
    "link": "the job's own link from the page, or {url}",
    "apply": "email or link to apply, or not found",
    "score": 8,
    "decision": "APPLY",
    "matching_skills": "list",
    "missing_skills": "list",
    "reason": "one short sentence"
  }}
]
"""
    reply = ask_gemini(prompt)
    if not reply:
        return []
    start, end = reply.find("["), reply.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        return json.loads(reply[start : end + 1])
    except json.JSONDecodeError:
        return []


def send_job(job):
    return send_whatsapp(
        f"🔔 New job match! (Job #{job['id']})\n\n"
        f"JOB: {job.get('title')} at {job.get('company')}\n"
        f"LOCATION: {job.get('location')}\n"
        f"SCORE: {job.get('score')}/10\n"
        f"DECISION: {job.get('decision')}\n"
        f"MATCHING SKILLS: {job.get('matching_skills')}\n"
        f"MISSING SKILLS: {job.get('missing_skills')}\n"
        f"HOW TO APPLY: {job.get('apply')}\n"
        f"REASON: {job.get('reason')}\n"
        f"LINK: {job.get('link')}\n\n"
        f"👉 Reply YES {job['id']} to apply, or NO {job['id']} to skip."
    )


def send_new_good_jobs(jobs, seen):
    # Send good, new jobs to WhatsApp. Returns how many were sent.
    sent = 0
    pending = load_pending()
    for job in jobs:
        key = f"{job.get('title')} | {job.get('company')}"
        if job.get("decision") not in ("APPLY", "MAYBE"):
            continue
        if key in seen:
            print("   already sent before:", key)
            continue
        job["id"] = max((p["id"] for p in pending), default=0) + 1
        print(f"   sending: #{job['id']} {key} ({job.get('score')}/10)")
        if not send_job(job):
            continue  # not sent, so don't mark it; try again next run
        seen.append(key)
        save_seen(seen)
        job["status"] = "WAITING"
        pending.append(job)
        save_pending(pending)
        sent += 1
    return sent
