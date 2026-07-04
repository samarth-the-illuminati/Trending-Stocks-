import os
import re
import time
import random
import redis
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse

redis_data_url = os.environ.get("RENDER_REDIS_URL", "redis://localhost:6379/1")
db = redis.Redis.from_url(redis_data_url)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
]

def load_companies():
    file_path = "list of top companies in india.txt"
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]

def process_website_pipeline_direct(url):
    companies = load_companies()
    if not companies:
        print("Pipeline tracking target checklist file missing.")
        return
        
    local_counts = {company: 0 for company in companies}
    session = requests.Session()
    
    try:
        session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
        response = session.get(url, timeout=10)
        if response.status_code != 200:
            return

        soup = BeautifulSoup(response.text, "html.parser")
        domain = urlparse(url).netloc
        
        sub_links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(url, href)
            if urlparse(full_url).netloc == domain:
                if not any(x in full_url for x in ["/login", "/sign-up", "/privacy", "/terms"]):
                    sub_links.add(full_url)
        
        # Kept to 10 links to run efficiently inside Render's free RAM limits
        links_to_crawl = list(sub_links)[:10]

        for sub_url in links_to_crawl:
            try:
                time.sleep(random.uniform(0.5, 1.2))
                sub_res = session.get(sub_url, timeout=5)
                if sub_res.status_code != 200:
                    continue
                    
                sub_soup = BeautifulSoup(sub_res.text, "html.parser")
                for element in sub_soup(["script", "style", "meta", "noscript", "header", "footer"]):
                    element.extract()
                    
                clean_text = sub_soup.get_text().lower()

                for company in companies:
                    pattern = r"\b" + re.escape(company) + r"\b"
                    matches = len(re.findall(pattern, clean_text))
                    if matches > 0:
                        local_counts[company] += matches
            except Exception:
                continue

        found_any = any(count > 0 for count in local_counts.values())
        if found_any:
            source_domain = urlparse(url).netloc
            pipe = db.pipeline()
            for company, count in local_counts.items():
                if count > 0:
                    redis_key = f"company_source:{company}"
                    pipe.hincrby(redis_key, source_domain, count)
            pipe.execute()

    except Exception as e:
        print(f"Error crawling {url}: {e}")

def trigger_global_ingestion_direct():
    print("Background thread active: Beginning target text scraping pipeline...")
    TARGET_SOURCES = [
        "https://economictimes.indiatimes.com",
        "https://pulse.zerodha.com",
        "https://www.moneycontrol.com"
    ]
    
    # Flush older cached tracking logs before refreshing metrics
    old_keys = db.keys("company_source:*")
    if old_keys:
        db.delete(*old_keys)
    
    for url in TARGET_SOURCES:
        process_website_pipeline_direct(url)
    print("Background thread active: Scraping extraction pipeline complete.")