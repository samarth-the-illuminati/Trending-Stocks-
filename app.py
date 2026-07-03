from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import redis

app = Flask(__name__)

# Ensures your frontend can talk to the backend smoothly
CORS(app)

db = redis.Redis(host='localhost', port=6379, db=1)

@app.route("/")
def home():
    """Serves the user interface dashboard natively from the server root."""
    return send_from_directory('.', 'index.html')

@app.route("/health-check")
def health():
    """API node health endpoint."""
    return jsonify({"status": "healthy", "service": "Data Pipeline Web API Running"})

@app.route("/trending")
def trending():
    raw_data = db.hgetall("live_stock_mentions")
    
    formatted_data = []
    for company_bytes, count_bytes in raw_data.items():
        company = company_bytes.decode('utf-8')
        count = int(count_bytes.decode('utf-8'))
        formatted_data.append([company, count])
        
    sorted_data = sorted(formatted_data, key=lambda x: x[1], reverse=True)
    return jsonify(sorted_data)

@app.route("/trigger-scrape", methods=["POST"])
def manual_trigger():
    from tasks import trigger_global_ingestion
    
    trigger_global_ingestion.delay()
    return jsonify({
        "status": "success",
        "message": "Manual data compilation pipeline queued across available Celery workers."
    })

if __name__ == "__main__":
    # Kept debug=False to maintain your exact server deployment preferences
    app.run(debug=False, port=5000)