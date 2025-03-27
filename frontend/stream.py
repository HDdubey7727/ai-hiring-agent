import streamlit as st
import requests
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import io
import base64
import json

# Page configuration
st.set_page_config(
    page_title="AI Hiring Agent",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #424242;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .dashboard-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .highlight-text {
        color: #1E88E5;
        font-weight: 600;
    }
    .score-card {
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        font-size: 1.8rem;
        font-weight: 700;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .score-high {
        background-color: #c8e6c9;
        color: #2e7d32;
    }
    .score-medium {
        background-color: #fff9c4;
        color: #f57f17;
    }
    .score-low {
        background-color: #ffcdd2;
        color: #c62828;
    }
    .skill-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .candidate-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #1E88E5;
    }
    .sidebar-content {
        padding: 1.5rem 1rem;
    }
    .stButton button {
        background-color: #1E88E5;
        color: white;
        font-weight: 600;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton button:hover {
        background-color: #1565C0;
    }
    hr {
        margin: 1.5rem 0;
        border: none;
        height: 1px;
        background-color: #e0e0e0;
    }
    .compare-table {
        width: 100%;
        border-collapse: collapse;
    }
    .compare-table th {
        background-color: #f1f8ff;
        padding: 8px;
        text-align: left;
        border-bottom: 2px solid #ddd;
    }
    .compare-table td {
        padding: 8px;
        border-bottom: 1px solid #ddd;
    }
    .compare-table tr:nth-child(even) {
        background-color: #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

# Flask backend URL
BACKEND_URL = "http://127.0.0.1:5000"
API_URL = f"{BACKEND_URL}/analyze"

# Initialize session state for tracking evaluated candidates
if 'evaluated_candidates' not in st.session_state:
    st.session_state.evaluated_candidates = []

# Check backend health
def check_backend_health():
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if not data.get("api_key_configured"):
                st.sidebar.warning("⚠️ Backend is running but the Google API key is not configured. Please add it to the .env file.")
            return True
        return False
    except requests.exceptions.RequestException:
        return False

# Function to extract skills from analysis
def extract_skills(analysis_text):
    skills = []
    
    # Simple extraction logic - can be enhanced
    if "Strengths:" in analysis_text:
        strengths_text = analysis_text.split("Strengths:")[1].split("Weaknesses:")[0]
        # Extract individual skills
        for line in strengths_text.split("\n"):
            if line.strip().startswith("-"):
                skills.append(line.strip()[2:])
    
    return skills

# Function to extract score
def extract_score(analysis_text):
    if "Score" in analysis_text:
        try:
            score_text = analysis_text.split("Score")[1].split("\n")[0]
            score = int(''.join(filter(str.isdigit, score_text)))
            return score
        except:
            return None
    return None

# Function to create score gauge
def create_score_gauge(score):
    if score is None:
        return None
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Match Score", 'font': {'size': 24}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "royalblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 40], 'color': '#ffcdd2'},
                {'range': [40, 70], 'color': '#fff9c4'},
                {'range': [70, 100], 'color': '#c8e6c9'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    
    return fig

# Function to analyze a single resume
def analyze_single_resume(uploaded_file, job_description):
    try:
        # Prepare data for API request
        files = {"resume": uploaded_file}
        data = {"job_description": job_description}
        
        response = requests.post(API_URL, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            analysis_text = result.get("analysis", "No analysis provided.")
            score = extract_score(analysis_text)
            skills = extract_skills(analysis_text)
            
            # Extract verdict
            verdict = ""
            if "Final Verdict" in analysis_text:
                verdict = analysis_text.split("Final Verdict")[1].strip()
            else:
                verdict = analysis_text.split("\n\n")[-1]
            
            # Create candidate record
            candidate = {
                "name": uploaded_file.name.split('.')[0],
                "analysis": analysis_text,
                "score": score if score is not None else 0,
                "skills": skills,
                "verdict": verdict,
                "file": uploaded_file
            }
            
            return candidate, None
        else:
            error = f"Error: {response.json().get('error', 'Unknown error occurred.')}"
            return None, error
    except Exception as e:
        return None, f"An error occurred: {str(e)}"

# Sidebar
st.sidebar.markdown("""
<div class="sidebar-content">
    <h2>🚀 AI Hiring Agent</h2>
    <p>This tool uses AI to evaluate candidate resumes against job descriptions.</p>
    <hr>
    <h3>How it works</h3>
    <ol>
        <li>Enter a job description</li>
        <li>Upload candidate resume(s)</li>
        <li>Get detailed AI-powered analysis</li>
    </ol>
    <hr>
    <h3>Features</h3>
    <ul>
        <li>Match score calculation</li>
        <li>Skills analysis</li>
        <li>Strengths & weaknesses identification</li>
        <li>Multiple candidate comparison</li>
        <li>Final recommendation</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Check if backend is running
backend_status = check_backend_health()
if not backend_status:
    st.error("⚠️ Backend server is not running. Please start the Flask backend first.")
    st.code("cd backend\npython flaskapi.py", language="bash")
    st.stop()

# Main content - Two column layout
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<h1 class="main-header">AI Hiring Agent for Startups</h1>', unsafe_allow_html=True)
    st.markdown('<p>Upload resumes and enter a job description to get AI-based candidate evaluations.</p>', unsafe_allow_html=True)

    # Create tabs for input, saved candidates, and comparison
    tab1, tab2, tab3 = st.tabs(["New Evaluation", "Saved Candidates", "Compare Candidates"])
    
    with tab1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        job_title = st.text_input("Job Title", "Data Scientist")
        job_description = st.text_area("Job Description", "Enter the job requirements here...", height=200)
        
        # Experience level selector
        experience_level = st.select_slider(
            "Required Experience Level",
            options=["Entry Level", "Junior", "Mid-Level", "Senior", "Expert"],
            value="Mid-Level"
        )
        
        # Key skills for the job
        key_skills = st.text_input("Key Skills Required (comma separated)", "Python, Data Analysis, Machine Learning")
        
        # Upload multiple files
        uploaded_files = st.file_uploader("Upload Resumes (PDF)", type=["pdf"], accept_multiple_files=True)
        
        # Create enhanced job description
        enhanced_job_description = f"""
        Job Title: {job_title}
        Experience Level: {experience_level}
        Key Skills: {key_skills}
        
        Job Description:
        {job_description}
        """
        
        if uploaded_files:
            st.write(f"📄 {len(uploaded_files)} resume(s) uploaded")
        
        analyze_button = st.button("Evaluate Candidates", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        
        if not st.session_state.evaluated_candidates:
            st.markdown('<p>No candidates have been evaluated yet. Upload resumes in the "New Evaluation" tab.</p>', unsafe_allow_html=True)
        else:
            st.markdown(f"<h3>Saved Candidates ({len(st.session_state.evaluated_candidates)})</h3>", unsafe_allow_html=True)
            
            # Sort candidates by score (highest first)
            sorted_candidates = sorted(st.session_state.evaluated_candidates, key=lambda x: x['score'], reverse=True)
            
            for candidate in sorted_candidates:
                score_color = "score-high" if candidate['score'] >= 70 else "score-medium" if candidate['score'] >= 40 else "score-low"
                
                st.markdown(f"""
                <div class="candidate-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4>{candidate['name']}</h4>
                        <div class="{score_color}" style="padding: 5px 15px; border-radius: 15px;">
                            {candidate['score']}%
                        </div>
                    </div>
                    <p><strong>Position:</strong> {job_title}</p>
                    <p><strong>Top Skills:</strong> {', '.join(candidate['skills'][:3]) if candidate['skills'] else 'None identified'}</p>
                    <p><strong>Verdict:</strong> {candidate['verdict'][:100]}...</p>
                </div>
                """, unsafe_allow_html=True)
        
        if st.session_state.evaluated_candidates:
            if st.button("Clear All Candidates", use_container_width=True):
                st.session_state.evaluated_candidates = []
                st.experimental_rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        
        if len(st.session_state.evaluated_candidates) < 2:
            st.markdown('<p>You need at least 2 evaluated candidates to compare them. Upload and evaluate multiple resumes first.</p>', unsafe_allow_html=True)
        else:
            st.markdown("<h3>Candidate Comparison</h3>", unsafe_allow_html=True)
            
            # Sort candidates by score (highest first)
            sorted_candidates = sorted(st.session_state.evaluated_candidates, key=lambda x: x['score'], reverse=True)
            
            # Create comparison table
            comparison_data = []
            for candidate in sorted_candidates:
                comparison_data.append({
                    "Name": candidate['name'],
                    "Score": candidate['score'],
                    "Skills": ", ".join(candidate['skills'][:3]) if candidate['skills'] else "None",
                    "Verdict": candidate['verdict'][:50] + "..." if len(candidate['verdict']) > 50 else candidate['verdict']
                })
            
            comparison_df = pd.DataFrame(comparison_data)
            
            # Visualization for scores comparison
            fig = px.bar(comparison_df, x='Name', y='Score', color='Score',
                         color_continuous_scale=['#ffcdd2', '#fff9c4', '#c8e6c9'],
                         labels={'Score': 'Match Score'}, title='Candidate Match Scores')
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display comparison table
            st.write("Detailed Comparison:")
            st.dataframe(comparison_df, use_container_width=True)
            
            # Top candidate highlight
            if sorted_candidates:
                top_candidate = sorted_candidates[0]
                st.markdown(f"""
                <div style="background-color: #f1f8ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
                    <h4>🏆 Top Candidate: {top_candidate['name']}</h4>
                    <p>Score: <span class="highlight-text">{top_candidate['score']}%</span></p>
                    <p>{top_candidate['verdict'][:200]}...</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# Results column
with col2:
    st.markdown('<h2 class="sub-header">Evaluation Results</h2>', unsafe_allow_html=True)
    
    # Process for analysis
    if analyze_button and uploaded_files and job_description.strip():
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_files = len(uploaded_files)
        successful_analyses = 0
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.write(f"Analyzing {uploaded_file.name}... ({i+1}/{total_files})")
            
            candidate, error = analyze_single_resume(uploaded_file, enhanced_job_description)
            
            if candidate and not error:
                # Add to session state if not already there
                if not any(c['name'] == candidate['name'] for c in st.session_state.evaluated_candidates):
                    st.session_state.evaluated_candidates.append(candidate)
                successful_analyses += 1
            else:
                st.error(f"Error analyzing {uploaded_file.name}: {error}")
            
            # Update progress
            progress_bar.progress((i + 1) / total_files)
        
        # Success message
        if successful_analyses > 0:
            st.success(f"✅ Successfully analyzed {successful_analyses} out of {total_files} resumes!")
            
            # Show latest results summary
            st.subheader("Latest Results Summary")
            
            # Sort by score (highest first)
            latest_results = sorted([c for c in st.session_state.evaluated_candidates if c['name'] in [file.name.split('.')[0] for file in uploaded_files]], 
                                   key=lambda x: x['score'], reverse=True)
            
            for candidate in latest_results[:3]:  # Show top 3
                score_color = "score-high" if candidate['score'] >= 70 else "score-medium" if candidate['score'] >= 40 else "score-low"
                
                st.markdown(f"""
                <div class="candidate-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4>{candidate['name']}</h4>
                        <div class="{score_color}" style="padding: 5px 15px; border-radius: 15px;">
                            {candidate['score']}%
                        </div>
                    </div>
                    <p><strong>Top Skills:</strong> {', '.join(candidate['skills'][:3]) if candidate['skills'] else 'None identified'}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Show message to navigate to tabs
            st.info("👈 Check the 'Saved Candidates' and 'Compare Candidates' tabs for detailed results.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    elif not analyze_button or not uploaded_files or not job_description.strip():
        # Show sample/placeholder content when not analyzing
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.info("👈 Upload one or more resumes and enter job details to see evaluation results here.")
        
        # Sample visualizations to show potential
        st.markdown("<h3>Sample Analysis Preview</h3>", unsafe_allow_html=True)
        
        # Sample gauge chart
        sample_fig = create_score_gauge(75)
        if sample_fig:
            st.plotly_chart(sample_fig, use_container_width=True)
        
        # Sample skills match
        sample_data = pd.DataFrame({
            'Skill': ['Python', 'SQL', 'Machine Learning', 'Data Visualization', 'Communication'],
            'Match': [90, 85, 70, 60, 80]
        })
        
        fig = px.bar(sample_data, x='Skill', y='Match', 
                    title='Sample Skills Match Analysis',
                    color='Match',
                    color_continuous_scale='Blues',
                    range_y=[0, 100])
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Add functionality for viewing individual candidate details
    if st.session_state.evaluated_candidates:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("Candidate Details")
        
        candidate_names = [c['name'] for c in st.session_state.evaluated_candidates]
        selected_candidate = st.selectbox("Select a candidate to view details", candidate_names)
        
        if selected_candidate:
            candidate = next((c for c in st.session_state.evaluated_candidates if c['name'] == selected_candidate), None)
            
            if candidate:
                # Create tabs for different sections of the analysis
                detail_tabs = st.tabs(["Overview", "Full Analysis", "Skills"])
                
                with detail_tabs[0]:
                    # Overview tab
                    score_col, verdict_col = st.columns([1, 2])
                    
                    with score_col:
                        if candidate['score'] is not None:
                            fig = create_score_gauge(candidate['score'])
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                    
                    with verdict_col:
                        st.subheader("Final Verdict")
                        st.write(candidate['verdict'])
                
                with detail_tabs[1]:
                    # Full analysis tab
                    st.markdown(candidate['analysis'])
                
                with detail_tabs[2]:
                    # Skills tab
                    if candidate['skills']:
                        for skill in candidate['skills']:
                            st.markdown(f"✅ {skill}")
                    else:
                        st.write("No specific skills identified.")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Add additional information at the bottom
    with st.expander("ℹ️ How scoring works"):
        st.markdown("""
        <div class="dashboard-card">
            <p>Our AI evaluates resumes based on several factors:</p>
            <ul>
                <li><b>Skills Match:</b> How well the candidate's skills align with job requirements</li>
                <li><b>Experience Relevance:</b> How relevant their experience is to the role</li>
                <li><b>Education:</b> Educational background and its relevance</li>
                <li><b>Overall Fit:</b> The holistic evaluation of the candidate</li>
            </ul>
            <p>Scores are calculated on a scale of 0-100:</p>
            <ul>
                <li><b>70-100:</b> Strong match - highly recommended</li>
                <li><b>40-69:</b> Moderate match - potential fit with some gaps</li>
                <li><b>0-39:</b> Low match - significant gaps in qualifications</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("""
<hr>
<p style="text-align: center; color: #666;">AI Hiring Agent | Developed with ❤️ using Streamlit and Google AI</p>
""", unsafe_allow_html=True)
