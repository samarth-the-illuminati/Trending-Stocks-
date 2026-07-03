import os
import re
import time
import random
import redis
from celery import Celery
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse

celery_app = Celery('stock_pipeline', broker='redis://localhost:6379/0')

db = redis.Redis(host='localhost', port=6379, db=1)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
]

def load_companies():
    """Reads and sanitizes the tracking targets from the company ledger."""
    file_path = "list of top companies in india.txt"
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        return [line.strip().lower() for line in f if line.strip()]

@celery_app.task
def process_website_pipeline(url):
    """
    Deep ETL Pipeline Worker Task.
    Extracts links from the main page, crawls sub-pages, and loads cumulative metrics to Redis.
    """
    companies = load_companies()
    if not companies:
        return "Pipeline aborted: 'list of top companies in india.txt' is empty or missing."
        
    local_counts = {company: 0 for company in companies}
    session = requests.Session()
    
    try:
        session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
        response = session.get(url, timeout=10)
        if response.status_code != 200:
            return f"Skipped seed {url}: HTTP {response.status_code}"

        # Stage 1: Parse main page and extract sub-links
        soup = BeautifulSoup(response.text, "html.parser")
        domain = urlparse(url).netloc
        
        sub_links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Convert relative paths (e.g., /market/news) to full URLs
            full_url = urljoin(url, href)
            
            # Filter: Ensure we only crawl links belonging to the same website
            if urlparse(full_url).netloc == domain:
                # Optional: Ignore obvious non-article pages to save time/bandwidth
                if not any(x in full_url for x in ["/login", "/sign-up", "/privacy", "/terms"]):
                    sub_links.add(full_url)
        
        # Limit sub-links per domain so tasks don't run forever (e.g., top 15 links)
        links_to_crawl = list(sub_links)[:15]
        print(f"🔗 Found {len(sub_links)} links on {url}. Crawling top {len(links_to_crawl)} articles...")

        # Stage 2: Deep crawl the extracted links
        processed_count = 0
        for sub_url in links_to_crawl:
            try:
                # Polite delay between internal requests
                time.sleep(random.uniform(0.5, 1.5))
                
                sub_res = session.get(sub_url, timeout=7)
                if sub_res.status_code != 200:
                    continue
                    
                sub_soup = BeautifulSoup(sub_res.text, "html.parser")
                
                # Clean up junk elements
                for element in sub_soup(["script", "style", "meta", "noscript", "header", "footer"]):
                    element.extract()
                    
                clean_text = sub_soup.get_text().lower()

                # Run regex analysis on article content
                for company in companies:
                    pattern = r"\b" + re.escape(company) + r"\b"
                    matches = len(re.findall(pattern, clean_text))
                    if matches > 0:
                        local_counts[company] += matches
                
                processed_count += 1
                
            except Exception:
                continue # Skip broken links silently and keep moving

        # Stage 3: Batch load the aggregated mentions into Redis
        found_any = any(count > 0 for count in local_counts.values())
        if found_any:
            pipe = db.pipeline()
            for company, count in local_counts.items():
                if count > 0:
                    pipe.hincrby("live_stock_mentions", company, count)
            pipe.execute()
            
        return f"Successfully deep-scraped {processed_count} articles from seed: {url}"

    except Exception as e:
        return f"Pipeline failure processing {url}: {str(e)}"

@celery_app.task
def trigger_global_ingestion():
    TARGET_SOURCES = [
        "https://economictimes.indiatimes.com",
        "https://pulse.zerodha.com",
        "https://www.moneycontrol.com",
        "https://www.livemint.com",
        "https://www.financialexpress.com"
    ]
    
    db.delete("live_stock_mentions")
    
    print(f"📢 Ingestion scheduler triggered: Dispatching {len(TARGET_SOURCES)} workers.")
    for url in TARGET_SOURCES:
        process_website_pipeline.delay(url)

celery_app.conf.beat_schedule = {
    'run-scrape-every-5-minutes': {
        'task': 'tasks.trigger_global_ingestion',
        'schedule': 300.0, 
    },
}
celery_app.conf.timezone = 'UTC'