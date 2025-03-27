from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import pdfplumber
import os
from dotenv import load_dotenv
import io

# Load environment variables
load_dotenv()
print("Loading API key from .env file...")

# Try both possible environment variable names
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("GOOGLE_API_KEY not found, trying GEMINI_API_KEY...")
    GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

if not GOOGLE_API_KEY:
    print("ERROR: No API key found in .env file!")
else:
    # Print masked API key for debugging (showing only first 6 chars)
    key_preview = GOOGLE_API_KEY[:6] + "..." if len(GOOGLE_API_KEY) > 6 else "invalid"
    print(f"API key found: {key_preview}***")

# Attempt to determine available models
available_models = []
model_to_use = "gemini-1.5-pro"  # Default to newer model
api_version = "v1"  # Default to v1 instead of v1beta

# Configure the Google AI API
try:
    print(f"Configuring Google Generative AI with API key...")
    # Configure the Gemini API with explicit API version
    genai.configure(
        api_key=GOOGLE_API_KEY,
        transport="rest",
        client_options={"api_endpoint": "generativelanguage.googleapis.com"}
    )
    
    try:
        # Try to list available models
        models = genai.list_models()
        available_models = [model.name for model in models]
        print(f"Available models: {available_models}")
        
        # Check for available models in preferred order
        if "models/gemini-1.5-pro" in available_models or "gemini-1.5-pro" in available_models:
            model_to_use = "gemini-1.5-pro"
        elif "models/gemini-pro" in available_models or "gemini-pro" in available_models:
            model_to_use = "gemini-pro"
        else:
            # Use the first available model that has 'gemini' and 'pro' in the name
            for model in available_models:
                if "gemini" in model.lower() and "pro" in model.lower():
                    model_to_use = model.replace("models/", "")  # Remove 'models/' prefix if present
                    break
        
        print(f"Using model: {model_to_use}")
    except Exception as model_e:
        print(f"Warning: Could not list models: {str(model_e)}. Using default model {model_to_use}.")
    
    print("Google Generative AI configured successfully")
except Exception as e:
    print(f"ERROR configuring Google Generative AI: {str(e)}")
    print("Trying alternative configuration...")
    try:
        # Try alternative configuration with v1beta but fixed endpoint
        genai.configure(
            api_key=GOOGLE_API_KEY,
            transport="rest",
            client_options={"api_endpoint": "generativelanguage.googleapis.com"}
        )
        print("Google Generative AI configured successfully with alternative configuration")
    except Exception as alt_e:
        print(f"ERROR configuring alternative Google Generative AI: {str(alt_e)}")
        GOOGLE_API_KEY = None  # Invalidate the key if configuration fails

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
    if not GOOGLE_API_KEY:
        raise ValueError("Invalid API key. Please configure a valid API key in the .env file.")
    
    try:
        # Specify model version using the detected model
        model = genai.GenerativeModel(model_to_use)
        
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
        
        # Set safety settings
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ]
        
        # Generate content with explicit parameters
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        print(f"Sending analysis request to {model_to_use}...")
        response = model.generate_content(
            prompt, 
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        print("Received response from model")
        return response.text
    except Exception as e:
        print(f"Error in analyze_resume: {str(e)}")
        
        # Try again with a different model if the current one fails
        if "gemini-1.5-pro" in model_to_use and "gemini-pro" in available_models:
            try:
                print("Attempting to use alternative model gemini-pro...")
                backup_model = genai.GenerativeModel("gemini-pro")
                backup_response = backup_model.generate_content(prompt)
                print("Successfully used alternative model")
                return backup_response.text
            except Exception as backup_e:
                print(f"Alternative model also failed: {str(backup_e)}")
        
        # Return a friendly error message with debugging information
        error_message = f"""
        Analysis Error:
        
        There was an error processing this resume. The error was:
        {str(e)}
        
        Score: 0
        Strengths: Unable to determine due to API error
        Weaknesses: Unable to determine due to API error
        Final Verdict: Please try again or contact support with error details.
        """
        return error_message

@app.route('/')
def index():
    return """
    <h1>AI Hiring Agent API</h1>
    <p>Available endpoints:</p>
    <ul>
        <li><a href="/health">Health Check</a> - Check if the API is running</li>
        <li><b>/analyze</b> - POST endpoint for resume analysis</li>
    </ul>
    <p>To use this application, please visit the Streamlit frontend at <a href="http://localhost:8503">http://localhost:8503</a></p>
    """

@app.route('/health', methods=['GET'])
def health_check():
    # Check if API key is valid by trying a simple generation
    api_key_valid = False
    api_error = None
    test_results = {}
    
    try:
        if GOOGLE_API_KEY:
            # First attempt to list models as a basic connectivity test
            test_results["list_models"] = "Not tested"
            test_results["generate_content"] = "Not tested"
            
            try:
                # Test model listing
                models = genai.list_models()
                model_names = [model.name for model in models]
                test_results["list_models"] = "Success"
                test_results["available_models"] = model_names
                
                # Check if our chosen model is in the list
                model_available = any(model_to_use in model_name or model_name.endswith(f"/{model_to_use}") for model_name in model_names)
                test_results["model_available"] = model_available
                
                # If not, suggest alternatives
                if not model_available:
                    gemini_models = [m for m in model_names if "gemini" in m.lower()]
                    test_results["suggested_models"] = gemini_models[:5] if gemini_models else []
            except Exception as list_e:
                test_results["list_models"] = f"Failed: {str(list_e)}"
            
            # Test content generation
            try:
                model = genai.GenerativeModel(model_to_use)
                response = model.generate_content("Hello, are you working?")
                if response and response.text:
                    api_key_valid = True
                    test_results["generate_content"] = "Success"
                    print("API key validation successful!")
            except Exception as gen_e:
                api_error = str(gen_e)
                test_results["generate_content"] = f"Failed: {str(gen_e)}"
                print(f"Health check failed: {api_error}")
                api_key_valid = False
    except Exception as e:
        api_error = str(e)
        print(f"Health check failed: {api_error}")
        api_key_valid = False
    
    return jsonify({
        "status": "healthy", 
        "api_key_configured": bool(GOOGLE_API_KEY),
        "api_key_valid": api_key_valid,
        "api_error": api_error,
        "model_in_use": model_to_use,
        "api_version": api_version,
        "available_models": available_models,
        "test_results": test_results
    }), 200

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

    except ValueError as ve:
        print(f"Validation error: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"Error in /analyze endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    print(f"Starting Flask backend on http://127.0.0.1:5000")
    print(f"API key configured: {bool(GOOGLE_API_KEY)}")
    print(f"Model in use: {model_to_use}")
    print(f"API Version: {api_version}")
    app.run(host='127.0.0.1', port=5000, debug=True)
