from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
from parser import ResumeParser
from llm_analyzer import analyze_resume

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
HISTORY_FOLDER = "history"
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(HISTORY_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_history(data):
    name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
    path = os.path.join(HISTORY_FOLDER, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return name

@app.route("/")
def home():
    return jsonify({
        "status": "Resume Analyzer running",
        "mode": "Standalone (No Ollama required)",
        "version": "2.0"
    })

@app.route("/api/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/parse", methods=["POST"])
def parse():
    """Parse and analyze uploaded resume"""
    
    # Check if file is present
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    
    # Check if filename is valid
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Check file extension
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file format. Please upload PDF, DOCX, or TXT"}), 400

    try:
        # Save uploaded file
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        # Parse resume
        parser = ResumeParser()
        result = parser.parse(path)

        # Analyze with standalone analyzer
        ai_result = analyze_resume(result["raw_text"])

        # Add AI analysis to result
        if "error" in ai_result:
            result["llm_summary"] = ai_result
        else:
            result["llm_summary"] = ai_result.get("result", {})

        # Save to history
        save_history(result)

        # Return success response
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({
            "error": f"Processing failed: {str(e)}"
        }), 500
    
    finally:
        # Clean up uploaded file
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

@app.route("/api/test", methods=["POST"])
def test():
    """Test endpoint for quick analysis"""
    data = request.get_json()
    text = data.get("text", "")
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    result = analyze_resume(text)
    return jsonify(result)

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Resume Analyzer Flask Server Starting...")
    print("=" * 60)
    print("📍 Server URL: http://localhost:5000")
    print("📍 API Endpoint: http://localhost:5000/api/parse")
    print("📍 Health Check: http://localhost:5000/api/health")
    print("=" * 60)
    print("✅ No Ollama required - using standalone analyzer")
    print("=" * 60)
    
    # Run server
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,  # Disable debug to avoid watchdog issues
        threaded=True
    )