# Step 5: send an email with my resume attached, from my own Gmail.
# Test:  python send_email.py   (sends a test email to myself)

import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
MY_NAME = os.getenv("MY_NAME")
RESUME_FILE = os.getenv("RESUME_FILE")
CV_NAME = f"{MY_NAME.replace(' ', '_')}_CV.pdf"  # file name HR sees


def send_email(to, subject, body):
    # Returns True if the email was sent.
    message = EmailMessage()
    message["From"] = f"{MY_NAME} <{GMAIL_ADDRESS}>"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    # Attach my resume
    with open(RESUME_FILE, "rb") as f:
        message.add_attachment(
            f.read(), maintype="application", subtype="pdf", filename=CV_NAME
        )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(message)
        print("Email sent to", to)
        return True
    except Exception as e:
        print("Could not send email:", e)
        return False


if __name__ == "__main__":
    send_email(
        to=GMAIL_ADDRESS,
        subject="Test from my job agent",
        body="Hello! If you can read this, my job agent can send emails.",
    )
