# Step 5: apply to a job I said YES to.
# Run:  python apply.py        -> list jobs waiting for my YES
#       python apply.py 3      -> apply to job #3 (shows the email first)
# whatsapp_server.py also uses apply_to_job() when I reply "YES 3" on WhatsApp.

import os
import re
import sys

from ai import ask_gemini
from jobs import load_pending, save_pending
from match_job import resume
from send_email import CV_NAME, send_email

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MY_NAME = os.getenv("MY_NAME")
MY_PHONE = os.getenv("MY_PHONE")
MY_EMAIL = os.getenv("GMAIL_ADDRESS")


def write_email(job):
    # Let Gemini write a short, honest application email. Returns (subject, body).
    prompt = f"""
Write a short job application email (120-180 words) from {MY_NAME}.

JOB: {job['title']} at {job['company']} ({job['location']})
WHY IT MATCHES: {job.get('matching_skills')}

{MY_NAME.upper()}'S RESUME:
{resume}

Rules:
- Only mention skills and experience that are really in the resume. Never invent anything.
- Mention that the CV is attached.
- Polite and professional. No placeholders like [Your Name].
- End with: {MY_NAME}, {MY_PHONE}, {MY_EMAIL}

Reply in exactly this format:
SUBJECT: <subject line>
BODY:
<email body>
"""
    reply = ask_gemini(prompt)
    if not reply or "BODY:" not in reply:
        return None, None
    subject = reply.split("BODY:")[0].replace("SUBJECT:", "").strip()
    body = reply.split("BODY:")[1].strip()
    return subject, body


def apply_to_job(job_id, ask_me=True):
    # Applies to job #job_id. Returns a short message about what happened.
    # ask_me=True shows the email in the terminal and asks before sending.
    pending = load_pending()
    job = next((j for j in pending if j["id"] == job_id), None)
    if not job:
        return f"Job #{job_id} not found."
    if job["status"] != "WAITING":
        return f"Job #{job_id} is already {job['status']}."

    # No email to apply to? Then I must apply on the website myself.
    found = EMAIL.search(job.get("apply") or "")
    if not found:
        job["status"] = "APPLY_ON_WEBSITE"
        save_pending(pending)
        link = job.get("apply") if job.get("apply") not in ("", "not found") else job.get("link")
        return f"Job #{job_id} has no apply email. Apply on the website yourself:\n{link}"
    hr_email = found.group()

    subject, body = write_email(job)
    if not subject:
        return f"Could not write the email for job #{job_id}. Try again later."

    if ask_me:
        print("\n" + "=" * 60)
        print("TO:      ", hr_email)
        print("SUBJECT: ", subject)
        print("ATTACH:  ", CV_NAME)
        print("-" * 60)
        print(body)
        print("=" * 60)
        if input("\nSend this email? (yes/no): ").strip().lower() not in ("yes", "y"):
            return "Not sent."

    if not send_email(hr_email, subject, body):
        return f"Could not send the email for job #{job_id}."

    job["status"] = "APPLIED"
    save_pending(pending)
    return (
        f"✅ Applied! Job #{job_id}: {job['title']} at {job['company']}\n"
        f"Sent to: {hr_email}\n\n"
        f"SUBJECT: {subject}\n\n{body}"
    )


def skip_job(job_id):
    pending = load_pending()
    job = next((j for j in pending if j["id"] == job_id), None)
    if not job:
        return f"Job #{job_id} not found."
    job["status"] = "SKIPPED"
    save_pending(pending)
    return f"👍 Skipped job #{job_id}: {job['title']} at {job['company']}"


if __name__ == "__main__":
    from send_whatsapp import send_whatsapp

    # No job number? Show the list of waiting jobs.
    if len(sys.argv) < 2:
        waiting = [j for j in load_pending() if j["status"] == "WAITING"]
        if not waiting:
            print("No jobs waiting.")
        for j in waiting:
            print(f"#{j['id']}  {j['title']} at {j['company']}  ({j['score']}/10)  apply: {j['apply']}")
        sys.exit()

    result = apply_to_job(int(sys.argv[1]))
    print(result)
    if result.startswith("✅"):
        send_whatsapp(result.split("\n\nSUBJECT:")[0])
