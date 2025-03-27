# AI Hiring Agent for Startups

A tool that uses AI to evaluate candidate resumes against job descriptions.

## Features

- Upload PDF resumes
- Analyze resumes against job descriptions
- Get AI-powered feedback on candidate fit

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Add your Google API key to the `.env` file in the root directory:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   ```
   You can obtain a Google API key from the [Google AI Studio](https://ai.google.dev/).

## Running the Application

Start each service separately in different terminal windows:

1. Start the backend:
   ```
   cd backend
   python flaskapi.py
   ```
   This will start the Flask API at http://127.0.0.1:5000

2. Start the frontend:
   ```
   cd frontend
   streamlit run stream.py
   ```
   This will launch the Streamlit UI at http://localhost:8502

Make sure the backend is running before starting the frontend.

## How to Use

1. Once both services are running, open your browser to http://localhost:8502
2. Enter the job description in the text area
3. Upload a resume in PDF format
4. Click "Evaluate Candidate" to get the AI analysis

## Troubleshooting

- If you see "Backend server is not running" error, make sure the Flask backend is started and running on port 5000
- If you get an authentication error, verify your Google API key is correctly set in the `.env` file
- For PDF extraction issues, ensure your PDF is readable and not password-protected

## API Endpoints

The backend provides the following endpoints:

- `GET /` - Homepage with API information
- `GET /health` - Check the health status of the API
- `POST /analyze` - Analyze a resume against a job description

## Frontend Configuration

The frontend uses a configuration file to connect to the backend. The configuration file is located in the `frontend` directory and is named `config.py`.

```python
BACKEND_URL = "http://127.0.0.1:5000"
API_URL = f"{BACKEND_URL}/analyze"
```

This configuration ensures that the frontend can communicate with the backend.