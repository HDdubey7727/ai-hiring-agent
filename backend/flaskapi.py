from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai  # Changed import back to standard format
import pdfplumber
import os
from dotenv import load_dotenv
import io

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

if not GOOGLE_API_KEY:
    print("WARNING: API key not found in .env file!")

# Configure the Google AI API
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Flask App
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins for frontend-backend communication

# Extract text from PDF resume
def extract_text_from_pdf(file):
    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {str(e)}")
        return None

# AI-Powered Resume Analysis using Gemini API
def analyze_resume(resume_text, job_description):
    model = genai.GenerativeModel("gemini-pro")
    
    prompt = f"""
    Analyze the following resume for the job description.
    Provide:
    - Score (0-100)
    - Strengths
    - Weaknesses
    - Final Verdict

    Job Description:
    {job_description}

    Resume:
    {resume_text}
    """
    
    response = model.generate_content(prompt)
    return response.text

@app.route('/')
def index():
    return """
    <h1>AI Hiring Agent API</h1>
    <p>Available endpoints:</p>
    <ul>
        <li><a href="/health">Health Check</a> - Check if the API is running</li>
        <li><b>/analyze</b> - POST endpoint for resume analysis</li>
    </ul>
    <p>To use this application, please visit the Streamlit frontend at <a href="http://localhost:8502">http://localhost:8502</a></p>
    """

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "api_key_configured": bool(GOOGLE_API_KEY)}), 200

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        job_description = request.form.get('job_description')
        uploaded_file = request.files.get('resume')

        if not job_description or not uploaded_file:
            return jsonify({"error": "Job description and resume are required"}), 400

        resume_text = extract_text_from_pdf(uploaded_file)
        if not resume_text:
            return jsonify({"error": "Could not extract text from the PDF"}), 400

        result = analyze_resume(resume_text, job_description)

        return jsonify({"analysis": result}), 200

    except Exception as e:
        print(f"Error in /analyze endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    print(f"Starting Flask backend on http://127.0.0.1:5000")
    print(f"API key configured: {bool(GOOGLE_API_KEY)}")
    app.run(host='127.0.0.1', port=5000, debug=True)
