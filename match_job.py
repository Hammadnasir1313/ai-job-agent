# Step 2: check if one job matches my resume. Good jobs go to WhatsApp.
# Run:  python match_job.py test_job.txt

import os
import sys

from dotenv import load_dotenv
from pypdf import PdfReader

from ai import ask_gemini
from send_whatsapp import send_whatsapp

load_dotenv()
RESUME_FILE = os.getenv("RESUME_FILE")  # path to my CV (PDF), set in .env
PROFILE_FILE = "my_profile.md"


def read_pdf(path):
    reader = PdfReader(path)
    return "\n".join(page.extract_text() for page in reader.pages)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# Read my resume and my profile (rules) once
resume = read_pdf(RESUME_FILE)
profile = read_text(PROFILE_FILE)


def match_job(job):
    # The instructions for the AI (this is the "prompt")
    prompt = f"""
You check if a job is a good match for a person.

PERSON'S PROFILE AND JOB RULES:
{profile}

PERSON'S RESUME:
{resume}

JOB POSTING:
{job}

Steps:
1. If the job breaks any "Job rules" in the profile, the decision is SKIP.
2. Otherwise compare the job's required skills with the person's skills.
3. Score 0-10. 8-10 = APPLY, 5-7 = MAYBE, 0-4 = SKIP.

Reply in exactly this format and nothing else:
JOB: <job title> at <company>
LOCATION: <location>
SCORE: <number>/10
DECISION: APPLY / MAYBE / SKIP
MATCHING SKILLS: <list>
MISSING SKILLS: <list>
HOW TO APPLY: <email or link, or "not found">
REASON: <one short sentence>
"""
    return ask_gemini(prompt)


def notify_if_good(result, link=""):
    # If it's a good job, send it to me on WhatsApp
    if "DECISION: APPLY" in result or "DECISION: MAYBE" in result:
        message = "🔔 New job match!\n\n" + result
        if link:
            message += "\nLINK: " + link
        send_whatsapp(message)
    else:
        print("Not a good match, no WhatsApp sent.")


if __name__ == "__main__":
    result = match_job(read_text(sys.argv[1]))
    if result:
        print(result)
        notify_if_good(result)
