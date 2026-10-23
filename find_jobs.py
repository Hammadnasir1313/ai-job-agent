# Step 3: find real jobs on the web, check them, send good ones to WhatsApp.
# Run:  python find_jobs.py

import time

from ddgs import DDGS

from jobs import check_page, load_seen, read_page, send_new_good_jobs

MAX_PAGES = 6  # pages to read per run (each page = 1 Gemini call)

SEARCHES = [
    "Laravel developer jobs Islamabad",
    "PHP developer jobs Islamabad",
    "Full stack PHP developer jobs Islamabad",
    "WordPress developer jobs Islamabad",
    "remote PHP Laravel developer jobs Pakistan",
]

# Sites we never read: they block bots, or don't allow them (LinkedIn)
SKIP_SITES = ["indeed.com", "glassdoor.", "linkedin.com", "jooble.org", "rozee.pk"]


def search_web():
    # Search with free search engines and collect page links
    links = []
    for query in SEARCHES:
        print("Searching:", query)
        try:
            results = DDGS(timeout=20).text(
                query, max_results=8, backend="bing, brave, yahoo, mojeek"
            )
        except Exception as e:
            print("   search failed:", e)
            continue
        for r in results:
            link = r["href"]
            if link not in links and not any(site in link for site in SKIP_SITES):
                links.append(link)
    return links


# 1. Search the web for job pages
links = search_web()
print(f"\nFound {len(links)} pages. Reading up to {MAX_PAGES}.\n")

# 2. Read each page, let Gemini find and score the jobs, send good ones
seen = load_seen()
sent = 0

for url in links[:MAX_PAGES]:
    print("Reading:", url)
    try:
        page_text = read_page(url)
    except Exception as e:
        print("   could not open page:", e)
        continue
    if not page_text:
        print("   page blocked or empty, skipping")
        continue

    jobs = check_page(url, page_text)
    print(f"   {len(jobs)} matching jobs on this page")
    sent += send_new_good_jobs(jobs, seen)
    time.sleep(5)  # small pause so the free Gemini plan doesn't block us

print(f"\nDone. Sent {sent} new jobs to WhatsApp.")
