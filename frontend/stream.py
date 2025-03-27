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
    .candidate-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #1E88E5;
    }
    .rejected-card {
        border-left: 5px solid #E53935;
        opacity: 0.7;
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
    .filter-section {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    hr {
        margin: 1.5rem 0;
        border: none;
        height: 1px;
        background-color: #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# Flask backend URL
BACKEND_URL = "http://127.0.0.1:5000"
API_URL = f"{BACKEND_URL}/analyze"

# Initialize session state for tracking evaluated candidates
if 'evaluated_candidates' not in st.session_state:
    st.session_state.evaluated_candidates = []

# Initialize session state for filtered candidates
if 'filtered_candidates' not in st.session_state:
    st.session_state.filtered_candidates = []

# Initialize filtering conditions
if 'min_score' not in st.session_state:
    st.session_state.min_score = 50
    
if 'required_skills' not in st.session_state:
    st.session_state.required_skills = []

# Check backend health
def check_backend_health():
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Display model information
            if data.get("model_in_use"):
                st.sidebar.info(f"🤖 Using model: {data.get('model_in_use')}")
            
            if data.get("api_version"):
                st.sidebar.info(f"📡 API Version: {data.get('api_version')}")
            
            # Display API key status
            if not data.get("api_key_configured"):
                st.sidebar.warning("⚠️ Backend is running but the Google API key is not configured. Please add it to the .env file.")
                return False
                
            if data.get("api_key_configured") and not data.get("api_key_valid"):
                st.sidebar.error("❌ API key is configured but not valid. Please check your API key in the .env file.")
                if data.get("api_error"):
                    st.sidebar.error(f"Error: {data.get('api_error')}")
                    
                    # Provide helpful advice based on error message
                    error_msg = data.get("api_error", "")
                    if "not found for API version" in error_msg:
                        st.sidebar.warning("""
                        ⚠️ The model may not be available for the current API version. 
                        Try using a different model or API version in the backend.
                        """)
                    elif "API_KEY_INVALID" in error_msg:
                        st.sidebar.warning("""
                        ⚠️ Your API key is invalid. Get a new one from:
                        https://aistudio.google.com/app/apikey
                        """)
                return False
                
            # Test if available models has any items
            if data.get("available_models") and len(data.get("available_models")) > 0:
                # Show what models are being used
                st.sidebar.success("✅ Connection to Google AI API successful")
            
            return True
        else:
            st.sidebar.error(f"❌ Backend returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        st.sidebar.error("""
        ❌ Cannot connect to backend server. 
        Make sure the Flask backend is running at http://127.0.0.1:5000
        
        Run this command in a terminal:
        ```
        cd backend
        python flaskapi.py
        ```
        """)
        return False
    except requests.exceptions.Timeout:
        st.sidebar.error("""
        ⏱️ Backend server connection timed out. 
        The server might be overloaded or experiencing issues.
        """)
        return False
    except Exception as e:
        st.sidebar.error(f"❌ Error checking backend health: {str(e)}")
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
                'value': st.session_state.min_score
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
                "file": uploaded_file,
                "filtered_out": False,  # Added filtered status
                "filter_reason": ""     # Reason for filtering
            }
            
            return candidate, None
        else:
            error = f"Error: {response.json().get('error', 'Unknown error occurred.')}"
            return None, error
    except Exception as e:
        return None, f"An error occurred: {str(e)}"

# Function to filter candidates based on criteria
def filter_candidates():
    filtered = []
    for candidate in st.session_state.evaluated_candidates:
        # Reset filter status
        candidate["filtered_out"] = False
        candidate["filter_reason"] = ""
        
        # Check minimum score
        if candidate["score"] < st.session_state.min_score:
            candidate["filtered_out"] = True
            candidate["filter_reason"] = f"Score below minimum ({candidate['score']} < {st.session_state.min_score})"
            continue

        # Check required skills
        if st.session_state.required_skills:
            candidate_skills_lower = [skill.lower() for skill in candidate["skills"]]
            missing_skills = []

            for skill in st.session_state.required_skills:
                skill_found = False
                for candidate_skill in candidate_skills_lower:
                    if skill.lower() in candidate_skill:
                        skill_found = True
                        break

                if not skill_found:
                    missing_skills.append(skill)

            if missing_skills:
                candidate["filtered_out"] = True
                candidate["filter_reason"] = f"Missing required skills: {', '.join(missing_skills)}"     

        # If not filtered out, add to filtered list
        if not candidate["filtered_out"]:
            filtered.append(candidate)

    # Update filtered candidates
    st.session_state.filtered_candidates = filtered

    return len(filtered)

# Sidebar
st.sidebar.markdown("""
<div class="sidebar-content">
    <h2>🚀 AI Hiring Agent</h2>
    <p>Upload resumes and filter candidates automatically.</p>
    <hr>
    <h3>How it works</h3>
    <ol>
        <li>Enter job requirements</li>
        <li>Upload multiple resumes</li>
        <li>Set filtering conditions</li>
        <li>Get only qualified candidates</li>
    </ol>
</div>
""", unsafe_allow_html=True)

# Check backend health
backend_healthy = check_backend_health()
if not backend_healthy:
    st.error("""
    ⚠️ The backend server is not responsive or has configuration issues.
    
    Please check:
    1. The backend server is running at http://127.0.0.1:5000
    2. Your API key is valid in the .env file
    3. Check the logs in the terminal where the backend is running
    
    If issues persist, try restarting both backend and frontend.
    """)
    # Continue anyway but warn the user
    st.warning("Continuing with limited functionality. Some features may not work correctly.")

# Main content - Two column layout
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<h1 class="main-header">AI Hiring Agent 🤖</h1>', unsafe_allow_html=True)
    st.markdown('<p>Upload resumes and automatically filter candidates based on your criteria.</p>', unsafe_allow_html=True)
                         
    # Create tabs for input and results
    tab1, tab2 = st.tabs(["Job Requirements & Upload", "Candidate Results"])

    with tab1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        job_title = st.text_input("Job Title", "Data Scientist")
        job_description = st.text_area("Job Description", "Enter the job requirements here...", height=150)
                         
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

        analyze_button = st.button("Analyze Resumes", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Filtering Section
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)
        st.subheader("Candidate Filtering")

        # Minimum score filter
        min_score = st.slider("Minimum Score", 0, 100, st.session_state.min_score, 5)
        st.session_state.min_score = min_score

        # Required skills filter
        st.write("Required Skills Filter")
        skills_list = [skill.strip() for skill in key_skills.split(",") if skill.strip()]

        if skills_list:
            selected_skills = st.multiselect(
                "Select skills that are REQUIRED (candidates missing these will be filtered out)",       
                options=skills_list,
                default=st.session_state.required_skills
            )
            st.session_state.required_skills = selected_skills

        # Apply filters button
        if st.button("Apply Filters", use_container_width=True) and st.session_state.evaluated_candidates:
            num_filtered = filter_candidates()
            st.success(f"✅ Filtered candidates: {num_filtered} qualified out of {len(st.session_state.evaluated_candidates)} total")
                         
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)

        # Tabs for different views
        result_tabs = st.tabs(["Qualified Candidates", "All Candidates", "Comparison"])

        with result_tabs[0]:
            if not st.session_state.filtered_candidates and not st.session_state.evaluated_candidates:   
                st.info("No candidates have been evaluated yet. Upload and analyze resumes first.")      
            elif not st.session_state.filtered_candidates and st.session_state.evaluated_candidates:     
                st.warning("No candidates meet your filtering criteria. Try adjusting your filters.")    
            else:
                st.subheader(f"Qualified Candidates ({len(st.session_state.filtered_candidates)})")      

                # Sort by score (highest first)
                sorted_candidates = sorted(st.session_state.filtered_candidates, key=lambda x: x['score'], reverse=True)
                         
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

        with result_tabs[1]:
            if not st.session_state.evaluated_candidates:
                st.info("No candidates have been evaluated yet. Upload and analyze resumes first.")      
            else:
                st.subheader(f"All Candidates ({len(st.session_state.evaluated_candidates)})")

                # Filter display options
                show_filtered = st.checkbox("Show filtered-out candidates", True)

                # Sort by score (highest first)
                sorted_candidates = sorted(st.session_state.evaluated_candidates, key=lambda x: x['score'], reverse=True)
                         
                for candidate in sorted_candidates:
                    if candidate["filtered_out"] and not show_filtered:
                        continue

                    score_color = "score-high" if candidate['score'] >= 70 else "score-medium" if candidate['score'] >= 40 else "score-low"
                    card_class = "candidate-card rejected-card" if candidate["filtered_out"] else "candidate-card"
                         
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h4>{candidate['name']}</h4>
                            <div class="{score_color}" style="padding: 5px 15px; border-radius: 15px;">  
                                {candidate['score']}%
                            </div>
                        </div>
                        <p><strong>Position:</strong> {job_title}</p>
                        <p><strong>Top Skills:</strong> {', '.join(candidate['skills'][:3]) if candidate['skills'] else 'None identified'}</p>
                        {"<p><strong>⚠️ Filtered Out:</strong> " + candidate['filter_reason'] + "</p>" if candidate["filtered_out"] else ""}
                    </div>
                    """, unsafe_allow_html=True)

                if st.button("Clear All Candidates", use_container_width=True):
                    st.session_state.evaluated_candidates = []
                    st.session_state.filtered_candidates = []
                    st.experimental_rerun()

        with result_tabs[2]:
            if len(st.session_state.filtered_candidates) < 2:
                st.info("You need at least 2 qualified candidates to compare them.")
            else:
                st.subheader("Compare Qualified Candidates")

                # Sort by score (highest first)
                sorted_candidates = sorted(st.session_state.filtered_candidates, key=lambda x: x['score'], reverse=True)
                         
                # Create comparison table
                comparison_data = []
                for candidate in sorted_candidates:
                    comparison_data.append({
                        "Name": candidate['name'],
                        "Score": candidate['score'],
                        "Skills": ", ".join(candidate['skills'][:3]) if candidate['skills'] else "None", 
                    })

                comparison_df = pd.DataFrame(comparison_data)

                # Visualization for scores comparison
                fig = px.bar(comparison_df, x='Name', y='Score', color='Score',
                             color_continuous_scale=['#fff9c4', '#c8e6c9'],
                             labels={'Score': 'Match Score'}, title='Candidate Match Scores')
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

                # Display comparison table
                st.write("Detailed Comparison:")
                st.dataframe(comparison_df, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

# Results column
with col2:
    st.markdown('<h2 class="sub-header">Analysis Results</h2>', unsafe_allow_html=True)

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

            # Apply filters automatically
            num_filtered = filter_candidates()
            st.info(f"👉 {num_filtered} candidates meet your filtering criteria")

            # Show filtering summary
            if num_filtered < successful_analyses:
                st.warning(f"⚠️ {successful_analyses - num_filtered} candidates were filtered out")   

            # Show latest results summary
            st.subheader("Top Candidates")

            # Sort by score (highest first)
            latest_results = sorted(st.session_state.filtered_candidates, key=lambda x: x['score'], reverse=True)[:3]
                         
            if latest_results:
                for candidate in latest_results:
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
            else:
                st.warning("No candidates meet the current filtering criteria. Try lowering the minimum score or adjusting required skills.")
                         
        st.markdown('</div>', unsafe_allow_html=True)

    elif not analyze_button or not uploaded_files or not job_description.strip():
        # Show sample/placeholder content when not analyzing
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.info("👆 Upload resumes and enter job details to get started")

        # Explain the filtering process
        st.subheader("How Candidate Filtering Works")
        st.write("1. Upload multiple resumes to analyze")
        st.write("2. Set minimum score requirement")
        st.write("3. Select required skills")
        st.write("4. Automatically filter out unqualified candidates")
        st.write("5. Focus only on the best matches for your job")

        # Sample gauge with min score threshold
        sample_fig = create_score_gauge(75)
        if sample_fig:
            st.plotly_chart(sample_fig, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Add candidate details view
    if st.session_state.evaluated_candidates:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("Candidate Details")

        # First show qualified candidates, then filtered ones
        all_candidates = sorted(
            sorted(st.session_state.evaluated_candidates, key=lambda x: x["score"], reverse=True),       
            key=lambda x: x["filtered_out"]
        )
        candidate_names = [f"{c['name']} ({c['score']}%){' ⚠️' if c['filtered_out'] else ''}" for c in all_candidates]
                         
        selected_candidate = st.selectbox("Select a candidate to view details", candidate_names)

        if selected_candidate:
            # Extract candidate name from formatted string
            candidate_name = selected_candidate.split(" (")[0]
            candidate = next((c for c in st.session_state.evaluated_candidates if c['name'] == candidate_name), None)
                         
            if candidate:
                # Show warning if filtered out
                if candidate["filtered_out"]:
                    st.warning(f"⚠️ This candidate was filtered out: {candidate['filter_reason']}")   

                # Create tabs for different sections of the analysis
                detail_tabs = st.tabs(["Overview", "Full Analysis"])

                with detail_tabs[0]:
                    # Overview tab
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        if candidate['score'] is not None:
                            fig = create_score_gauge(candidate['score'])
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)

                    with col2:
                        st.subheader("Skills")
                        if candidate['skills']:
                            required_skills_lower = [s.lower() for s in st.session_state.required_skills]
                            for skill in candidate['skills']:
                                # Check if skill is required
                                is_required = any(req.lower() in skill.lower() for req in required_skills_lower)
                                if is_required:
                                    st.markdown(f"✅ **{skill}** (Required)")
                                else:
                                    st.markdown(f"✅ {skill}")
                        else:
                            st.write("No specific skills identified")

                with detail_tabs[1]:
                    # Full analysis tab
                    st.subheader("AI Analysis Result")
                    st.markdown(candidate['analysis'])

        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<hr>
<p style="text-align: center; color: #666;">AI Hiring Agent | Developed with Streamlit and Google AI</p> 
""", unsafe_allow_html=True) 