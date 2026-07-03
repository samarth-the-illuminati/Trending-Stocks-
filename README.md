Trending Stocks - Real-Time Mentions Analytics Pipeline
A distributed data ingestion pipeline that deep-scrapes financial news homepages, extracts internal news articles, and runs concurrent phrase-matching algorithms to see which Indian companies are being talked about the most right now.

The project uses a two-stage extraction method to uncover deep-linked content and aggregates company mention metrics into a live dashboard.

**Architecture Overview**
The system architecture is split into three decoupled components to handle I/O-bound scaling smoothly:

Data Core (Redis): Acts as both the task message broker (DB 0) and the ultra-low latency metrics datastore (DB 1).

Distributed Background Workers (Celery & BeautifulSoup4): A scheduled orchestrator (celery beat) automatically fires off a global ingestion cycle every 5 minutes. Parallel worker processes fetch seed domains, safely scrape up to 15 sub-article links per site, parse out HTML clutter (headers, footers, scripts), and track keyword hits using tokenized regex matching.

Web API Gateway & Frontend (Flask & CORS): A responsive web server that pulls calculated telemetry data straight out of Redis pipelines and feeds it to a web dashboard via an optimized, pre-sorted JSON stream.

**Tech Stack**
Backend Framework: Flask

Task Management & Concurrency: Celery

Caching & Brokerage: Redis DB

Scraping & Extraction: Requests, BeautifulSoup4

Frontend Environment: Pure HTML5 / JavaScript (with CORS integrations)

**How to Spin It Up Locally**
Make sure you have Redis running in your background environment (WSL2/Linux or Native) before launching the python components.

1. Fire Up the Celery Workers & Scheduler
Open your Linux terminal (or WSL2 shell) and execute the background worker block to bind to your Redis broker:

Bash
celery -A tasks worker --beat --loglevel=info
Note: The --beat flag is required to handle the persistent 5-minute automated scraping routine.

2. Run the Web Server API
Open a secondary, native terminal window (like PowerShell) and start up your web platform gateway:

PowerShell
python app.py
3. Check the Live Dashboard
Navigate your web browser to your host interface root:

Plaintext
http://127.0.0.1:5000/
To view the raw sorted data metrics matrix directly via the API node, access:

Plaintext
http://127.0.0.1:5000/trending
**Data Streams Managed**
The crawler target configuration currently maps live market feeds across these prominent business aggregates:

The Economic Times

Zerodha Pulse

LiveMint

Financial Express

Business Standard (Note: Rate limits may apply)

Business Standard

Tracking definitions are dynamically updated by editing the company tracking ledger located directly inside list of top companies in india.txt.
