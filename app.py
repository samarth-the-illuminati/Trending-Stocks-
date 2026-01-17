from flask import Flask, jsonify
from flask_cors import CORS
import requests
import re

app = Flask(__name__)
CORS(app)

@app.route("/")
def health():
    return "✅ Backend is running"

@app.route("/trending")
def trending():

    urls = [
        "https://economictimes.indiatimes.com",
        "https://pulse.zerodha.com",
        "https://www.moneycontrol.com"
    ]

    with open("list of top companies in india.txt", "r") as f:
        companies = [line.strip().lower() for line in f if line.strip()]

    company_count = {company: 0 for company in companies}

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0"
    })

    for url in urls:
        try:
            response = session.get(url, timeout=10)
            html = response.text.lower()

            for company in companies:
                pattern = r"\b" + re.escape(company) + r"\b"
                matches = re.findall(pattern, html)
                company_count[company] += len(matches)

        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    sorted_companies = sorted(
        company_count.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return jsonify(sorted_companies)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
