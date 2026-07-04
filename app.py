from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import redis
import os
import threading

# Import the scraping function directly from tasks
from tasks import trigger_global_ingestion_direct

app = Flask(__name__)
CORS(app)

# Fallback to local configuration, but Render will override via environment variables
redis_url = os.environ.get("RENDER_REDIS_URL", "redis://localhost:6379/1")
db = redis.Redis.from_url(redis_url)

@app.route("/")
def home():
    return send_from_directory('.', 'index.html')

@app.route("/health-check")
def health():
    return jsonify({"status": "healthy", "service": "Data Pipeline Web API Running"})

@app.route("/trending")
def trending():
    company_keys = db.keys("company_source:*")
    raw_formatted = []
    
    if not company_keys:
        return jsonify([])
        
    for key in company_keys:
        key_str = key.decode('utf-8')
        company_name = key_str.split(":")[1]
        source_data = db.hgetall(key)
        
        breakdown = {}
        total_aggregate = 0
        
        for source_bytes, count_bytes in source_data.items():
            source = source_bytes.decode('utf-8')
            count = int(count_bytes.decode('utf-8'))
            breakdown[source] = count
            total_aggregate += count
            
        raw_formatted.append({
            "company": company_name,
            "total": total_aggregate,
            "sources": breakdown
        })
        
    sorted_data = sorted(raw_formatted, key=lambda x: x['total'], reverse=True)
    return jsonify(sorted_data)

@app.route("/trigger-scrape", methods=["POST", "GET"])
def manual_trigger():
    # Spin up an isolated background thread inside this service container to avoid HTTP timeouts
    threading.Thread(target=trigger_global_ingestion_direct).start()
    return jsonify({
        "status": "success",
        "message": "Scraping pipeline started safely in the background!"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)