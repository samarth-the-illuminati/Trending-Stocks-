import os
import re
import time
import random
import redis
from celery import Celery
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse

# Celery uses DB 0 for scheduling messages, Flask handles data metrics on DB 1
celery_broker_url = os.environ.get("RENDER_CELERY_BROKER", "redis://localhost:6379/0")[cite: 10]
redis_data_url = os.environ.get("RENDER_REDIS_URL", "redis://localhost:6379/1")[cite: 10]

celery_app = Celery('stock_pipeline', broker=celery_broker_url)[cite: 10]
db = redis.Redis.from_url(redis_data_url)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
][cite: 10]

def load_companies():
    """Reads and sanitizes the tracking targets from the company ledger."""
    file_path = "list of top companies in india.txt"[cite: 10]
    if not os.path.exists(file_path):[cite: 10]
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()][cite: 10]

@celery_app.task
def process_website_pipeline(url):
    """
    Deep ETL Pipeline Worker Task.
    Extracts links from the main page, crawls sub-pages, and loads cumulative metrics to Redis.
    """
    companies = load_companies()[cite: 10]
    if not companies:[cite: 10]
        return "Pipeline aborted: 'list of top companies in india.txt' is empty or missing."[cite: 10]
        
    local_counts = {company: 0 for company in companies}[cite: 10]
    session = requests.Session()[cite: 10]
    
    try:
        session.headers.update({"User-Agent": random.choice(USER_AGENTS)})[cite: 10]
        response = session.get(url, timeout=10)[cite: 10]
        if response.status_code != 200:[cite: 10]
            return f"Skipped seed {url}: HTTP {response.status_code}"[cite: 10]

        # Stage 1: Parse main page and extract sub-links
        soup = BeautifulSoup(response.text, "html.parser")[cite: 10]
        domain = urlparse(url).netloc[cite: 10]
        
        sub_links = set()[cite: 10]
        for a_tag in soup.find_all("a", href=True):[cite: 10]
            href = a_tag["href"][cite: 10]
            full_url = urljoin(url, href)[cite: 10]
            
            if urlparse(full_url).netloc == domain:[cite: 10]
                if not any(x in full_url for x in ["/login", "/sign-up", "/privacy", "/terms"]):[cite: 10]
                    sub_links.add(full_url)[cite: 10]
        
        links_to_crawl = list(sub_links)[:15][cite: 10]
        print(f"🔗 Found {len(sub_links)} links on {url}. Crawling top {len(links_to_crawl)} articles...")[cite: 10]

        # Stage 2: Deep crawl the extracted links
        processed_count = 0[cite: 10]
        for sub_url in links_to_crawl:[cite: 10]
            try:
                time.sleep(random.uniform(0.5, 1.5))[cite: 10]
                sub_res = session.get(sub_url, timeout=7)[cite: 10]
                if sub_res.status_code != 200:[cite: 10]
                    continue[cite: 10]
                    
                sub_soup = BeautifulSoup(sub_res.text, "html.parser")[cite: 10]
                
                for element in sub_soup(["script", "style", "meta", "noscript", "header", "footer"]):[cite: 10]
                    element.extract()[cite: 10]
                    
                clean_text = sub_soup.get_text().lower()[cite: 10]

                for company in companies:[cite: 10]
                    pattern = r"\b" + re.escape(company) + r"\b"[cite: 10]
                    matches = len(re.findall(pattern, clean_text))[cite: 10]
                    if matches > 0:[cite: 10]
                        local_counts[company] += matches[cite: 10]
                
                processed_count += 1[cite: 10]
                
            except Exception:
                continue

        # Stage 3: Batch load the aggregated mentions into Redis
        found_any = any(count > 0 for count in local_counts.values())[cite: 10]
        if found_any:[cite: 10]
            source_domain = urlparse(url).netloc[cite: 10]
            pipe = db.pipeline()[cite: 10]
            for company, count in local_counts.items():[cite: 10]
                if count > 0:[cite: 10]
                    redis_key = f"company_source:{company}"[cite: 10]
                    pipe.hincrby(redis_key, source_domain, count)[cite: 10]
            pipe.execute()[cite: 10]
            
        return f"Successfully deep-scraped {processed_count} articles from seed: {url}"[cite: 10]

    except Exception as e:
        return f"Pipeline failure processing {url}: {str(e)}"[cite: 10]

@celery_app.task
def trigger_global_ingestion():
    TARGET_SOURCES = [
        "https://economictimes.indiatimes.com",
        "https://pulse.zerodha.com",
        "https://www.moneycontrol.com",
        "https://www.livemint.com",
        "https://www.financialexpress.com"
    ][cite: 10]
    
    old_keys = db.keys("company_source:*")[cite: 10]
    if old_keys:[cite: 10]
        db.delete(*old_keys)[cite: 10]
    
    print(f"📢 Ingestion scheduler triggered: Dispatching {len(TARGET_SOURCES)} workers.")[cite: 10]
    for url in TARGET_SOURCES:[cite: 10]
        process_website_pipeline.delay(url)[cite: 10]

# Standardized programmatic task configuration dictionary
celery_app.conf.update(
    beat_schedule={
        'run-scrape-every-5-minutes': {
            'task': 'tasks.trigger_global_ingestion',
            'schedule': 300.0, 
        },
    },
    timezone='UTC'
)