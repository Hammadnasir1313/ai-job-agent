# Talks to Gemini. Used by match_job.py, jobs.py and apply.py.

import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# The free plan has a daily limit for EACH model.
# If one model's limit is used up, we try the next one.
MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
]


def ask_gemini(prompt, search=False):
    # search=True lets Gemini use Google Search to find real web pages.
    config = None
    if search:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )

    for model in MODELS:
        # If Google is busy (error 503), wait and try again (up to 5 times).
        for attempt in range(1, 6):
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                return response.text
            except errors.ServerError:
                wait = attempt * 15
                print(f"Google is busy. Waiting {wait} seconds, then trying again ({attempt}/5)...")
                time.sleep(wait)
            except errors.ClientError as e:
                # 429 = daily limit used up, 404 = model not available. Try the next model.
                if e.code in (429, 404):
                    print(f"Model {model} not available now ({e.code}). Trying the next model...")
                    break
                raise

    print("All Gemini models are busy or used up. Please try again later.")
    return None
