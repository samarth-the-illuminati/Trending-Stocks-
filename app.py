from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import redis
import os
app = Flask(__name__)

# Ensures your frontend can talk to the backend smoothly
CORS(app)



# Render automatically provisions a URL variable. If it's missing, it defaults to your local setup.
redis_url = os.environ.get("RENDER_REDIS_URL", "redis://localhost:6379/1")
db = redis.Redis.from_url(redis_url)

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
    # Find all company keys (returns list of bytes)
    company_keys = db.keys("company_source:*")
    
    raw_formatted = []
    
    # Check if database is empty to prevent processing errors
    if not company_keys:
        return jsonify([])
        
    for key in company_keys:
        # Safely decode the main key from bytes to string before splitting
        key_str = key.decode('utf-8')
        company_name = key_str.split(":")[1]
        
        # Pull data out of the specific hash
        source_data = db.hgetall(key)
        
        breakdown = {}
        total_aggregate = 0
        
        for source_bytes, count_bytes in source_data.items():
            source = source_bytes.decode('utf-8')
            # Handles decoding directly from byte values to numbers cleanly
            count = int(count_bytes.decode('utf-8'))
            
            breakdown[source] = count
            total_aggregate += count
            
        raw_formatted.append({
            "company": company_name,
            "total": total_aggregate,
            "sources": breakdown
        })
        
    # Sort the companies by the highest total aggregate mentions
    sorted_data = sorted(raw_formatted, key=lambda x: x['total'], reverse=True)
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
    # Maintained debug=False per your preferences
    app.run(debug=False, port=5000)