from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests
import re
import os

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/trending")
def trending():

    urls = [
        "https://economictimes.indiatimes.com",
        "https://pulse.zerodha.com",
        "https://www.moneycontrol.com"
    ]

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(BASE_DIR, "companies.txt"), "r") as f:
        companies = [line.strip().lower() for line in f if line.strip()]


    company_count = {company: 0 for company in companies}

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    for url in urls:
        try:
            response = session.get(url, timeout=8)
            html = response.text.lower()

            for company in companies:
                pattern = r"\b" + re.escape(company) + r"\b"
                company_count[company] += len(re.findall(pattern, html))

        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    sorted_companies = sorted(
        company_count.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return jsonify(sorted_companies)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

    
