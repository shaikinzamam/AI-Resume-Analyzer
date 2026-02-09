import streamlit as st
import requests
import os
import json
from datetime import datetime
import uuid
import plotly.graph_objects as go
import plotly.express as px

# Page configuration
st.set_page_config(
    page_title="AI Resume Analyzer Pro",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "AI Resume Analyzer Pro - Get instant career insights"
    }
)

# Force white theme
st.markdown("""
    <style>
    /* Force white background on everything */
    .stApp, body, html {
        background-color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# Custom CSS - Complete White Theme with All Text Visible
st.markdown("""
    <style>
    /* ========== GLOBAL OVERRIDES ========== */
    /* Force all elements to have dark text */
    .stApp {
        background-color: #ffffff !important;
    }
    
    .main {
        background-color: #ffffff !important;
        padding: 0rem 1rem;
    }
    
    /* Top header bar */
    header[data-testid="stHeader"] {
        background-color: #ffffff !important;
    }
    
    /* Toolbar */
    [data-testid="stToolbar"] {
        background-color: #ffffff !important;
    }
    
    /* Entire viewport */
    section[data-testid="stAppViewContainer"] {
        background-color: #ffffff !important;
    }
    
    /* Main content area */
    [data-testid="stMain"] {
        background-color: #ffffff !important;
    }
    
    /* Make ALL text dark and visible by default */
    p, span, div, label, li, h1, h2, h3, h4, h5, h6, a {
        color: #2c3e50 !important;
    }
    
    /* ========== SIDEBAR ========== */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 2px solid #e8e8e8;
    }
    
    [data-testid="stSidebar"] * {
        color: #2c3e50 !important;
    }
    
    [data-testid="stSidebar"] label {
        color: #2c3e50 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }
    
    /* Radio buttons */
    [data-testid="stSidebar"] [role="radiogroup"] label {
        color: #2c3e50 !important;
        font-size: 1.05rem !important;
        font-weight: 500 !important;
    }
    
    /* ========== BUTTONS ========== */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        font-weight: 600;
        transition: all 0.3s;
        background-color: #2c3e50;
        color: white !important;
        border: 2px solid #2c3e50;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(44, 62, 80, 0.3);
        background-color: #34495e;
    }
    
    /* ========== FILE UPLOADER ========== */
    [data-testid="stFileUploader"] {
        background-color: white !important;
        border: 3px dashed #3498db !important;
        border-radius: 15px !important;
        padding: 2.5rem !important;
    }
    
    [data-testid="stFileUploader"] label {
        color: #2c3e50 !important;
        font-weight: 700 !important;
        font-size: 1.2rem !important;
    }
    
    [data-testid="stFileUploader"] section {
        border-color: #3498db !important;
        background-color: #f8f9fa !important;
        border-radius: 10px !important;
    }
    
    [data-testid="stFileUploader"] section > div {
        color: #2c3e50 !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }
    
    /* Drag and drop text */
    [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] p {
        color: #2c3e50 !important;
        font-weight: 700 !important;
        font-size: 1.15rem !important;
    }
    
    /* File type and size limit text */
    [data-testid="stFileUploader"] small {
        color: #34495e !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    
    /* The actual drag text inside uploader */
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] span {
        color: #2c3e50 !important;
        font-weight: 600 !important;
    }
    
    /* Center section text */
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
        background-color: #f0f3f7 !important;
        border: 2px dashed #3498db !important;
    }
    
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] p {
        color: #2c3e50 !important;
        font-weight: 700 !important;
        font-size: 1.2rem !important;
    }
    
    /* Browse files button */
    [data-testid="stFileUploader"] button {
        background-color: #2c3e50 !important;
        color: white !important;
        font-weight: 700 !important;
        border: none !important;
    }
    
    /* ========== HERO SECTION ========== */
    .hero-section {
        background: white;
        padding: 3rem;
        border-radius: 15px;
        border: 3px solid #e8e8e8;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .hero-title {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        color: #2c3e50 !important;
    }
    .hero-subtitle {
        font-size: 1.2rem;
        color: #7f8c8d !important;
        font-weight: 500;
    }
    
    /* ========== CARDS ========== */
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #e8e8e8;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* ========== METRIC CARDS ========== */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        transition: transform 0.3s;
        border: 2px solid #e8e8e8;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .metric-card:hover {
        transform: scale(1.05);
        border-color: #2c3e50;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #2c3e50 !important;
    }
    .metric-label {
        color: #7f8c8d !important;
        font-size: 0.9rem;
        margin-top: 0.5rem;
        font-weight: 500;
    }
    
    /* ========== BADGES ========== */
    .strength-badge {
        background: white;
        color: #27ae60 !important;
        padding: 0.6rem 1.2rem;
        border-radius: 20px;
        border: 2px solid #27ae60;
        display: inline-block;
        margin: 0.3rem;
        font-weight: 600;
    }
    .weakness-badge {
        background: white;
        color: #e74c3c !important;
        padding: 0.6rem 1.2rem;
        border-radius: 20px;
        border: 2px solid #e74c3c;
        display: inline-block;
        margin: 0.3rem;
        font-weight: 600;
    }
    .skill-badge {
        background: white;
        color: #3498db !important;
        padding: 0.6rem 1.2rem;
        border-radius: 20px;
        border: 2px solid #3498db;
        display: inline-block;
        margin: 0.3rem;
        font-weight: 600;
    }
    .role-badge {
        background: white;
        color: #9b59b6 !important;
        padding: 0.6rem 1.2rem;
        border-radius: 20px;
        border: 2px solid #9b59b6;
        display: inline-block;
        margin: 0.3rem;
        font-weight: 600;
    }
    
    /* ========== SUMMARY CARD ========== */
    .summary-card {
        background: white;
        color: #2c3e50 !important;
        padding: 2rem;
        border-radius: 15px;
        margin: 1.5rem 0;
        border: 2px solid #e8e8e8;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .summary-card h2 {
        color: #2c3e50 !important;
    }
    
    .summary-card p {
        color: #34495e !important;
    }
    
    /* ========== TABS ========== */
    .tab-content {
        padding: 1rem 0;
        background: white;
    }
    
    [data-baseweb="tab-list"] button {
        color: #2c3e50 !important;
        font-weight: 600 !important;
    }
    
    [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #2c3e50 !important;
        font-weight: 700 !important;
    }
    
    /* ========== FOOTER ========== */
    .footer-text {
        text-align: center;
        color: #7f8c8d !important;
        padding: 2rem;
    }
    
    .footer-text p {
        color: #7f8c8d !important;
        font-weight: 500;
    }
    
    /* ========== INFO/SUCCESS/WARNING BOXES ========== */
    .stAlert {
        background-color: white !important;
        border: 2px solid #e8e8e8 !important;
    }
    
    .stAlert p {
        color: #2c3e50 !important;
        font-weight: 500;
    }
    
    /* ========== DOWNLOAD BUTTONS ========== */
    .stDownloadButton button {
        background-color: white !important;
        color: #2c3e50 !important;
        border: 2px solid #2c3e50 !important;
        font-weight: 600 !important;
    }
    
    .stDownloadButton button:hover {
        background-color: #2c3e50 !important;
        color: white !important;
    }
    
    /* ========== EXPANDERS ========== */
    [data-testid="stExpander"] {
        background-color: white;
        border: 2px solid #e8e8e8;
    }
    
    [data-testid="stExpander"] summary {
        color: #2c3e50 !important;
        font-weight: 600 !important;
    }
    
    /* ========== DIVIDERS ========== */
    hr {
        border-color: #e8e8e8 !important;
    }
    
    /* ========== SPINNER ========== */
    .stSpinner > div {
        border-color: #2c3e50 !important;
    }
    
    /* ========== HEADERS ========== */
    h1, h2, h3, h4, h5, h6 {
        color: #2c3e50 !important;
        font-weight: 700 !important;
    }
    
    /* ========== MARKDOWN TEXT ========== */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span {
        color: #2c3e50 !important;
        font-weight: 500;
    }
    
    [data-testid="stMarkdownContainer"] strong {
        color: #2c3e50 !important;
        font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)

API = "http://localhost:5000/api/parse"

# Initialize session state
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'history' not in st.session_state:
    st.session_state.history = []

def calculate_resume_score(llm_data):
    """Calculate an overall resume score"""
    score = 50  # Base score
    
    # Add points for strengths (max 30 points)
    strengths = llm_data.get('strengths', [])
    score += min(len(strengths) * 6, 30)
    
    # Deduct points for weaknesses (max -20 points)
    weaknesses = llm_data.get('weaknesses', [])
    score -= min(len(weaknesses) * 5, 20)
    
    # Deduct points for missing skills (max -10 points)
    missing = llm_data.get('missing_skills', [])
    score -= min(len(missing) * 2, 10)
    
    # Add points for job role matches (max 10 points)
    roles = llm_data.get('suggested_job_roles', [])
    score += min(len(roles) * 2, 10)
    
    return max(0, min(100, score))

def create_gauge_chart(score):
    """Create a gauge chart for resume score - White theme"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Resume Score", 'font': {'size': 24, 'color': '#2c3e50'}},
        delta = {'reference': 75},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#2c3e50"},
            'bar': {'color': "#2c3e50"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e8e8e8",
            'steps': [
                {'range': [0, 40], 'color': '#fee'},
                {'range': [40, 70], 'color': '#ffd'},
                {'range': [70, 100], 'color': '#efe'}],
            'threshold': {
                'line': {'color': "#e74c3c", 'width': 4},
                'thickness': 0.75,
                'value': 85}}))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={'color': "#2c3e50", 'family': "Arial"}
    )
    
    return fig

def create_skills_chart(llm_data):
    """Create a bar chart for skills analysis - White theme"""
    categories = ['Strengths', 'Weaknesses', 'Missing Skills', 'Job Matches']
    values = [
        len(llm_data.get('strengths', [])),
        len(llm_data.get('weaknesses', [])),
        len(llm_data.get('missing_skills', [])),
        len(llm_data.get('suggested_job_roles', []))
    ]
    colors = ['#27ae60', '#e74c3c', '#f39c12', '#9b59b6']
    
    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=values,
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Skills Analysis Overview",
        title_font_color="#2c3e50",
        xaxis_title="Category",
        yaxis_title="Count",
        height=300,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={'color': "#2c3e50", 'family': "Arial"}
    )
    
    fig.update_xaxes(showgrid=False, showline=True, linewidth=2, linecolor='#e8e8e8')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')
    
    return fig

# Sidebar
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 1.5rem 0; background: white;">
            <h1 style="color: #2c3e50 !important; font-size: 1.6rem; margin-bottom: 0.5rem; font-weight: 700;">📄 Resume Analyzer Pro</h1>
            <p style="color: #34495e !important; font-size: 1rem; font-weight: 600;">AI-Powered Career Insights</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown('<p style="color: #2c3e50 !important; font-weight: 700 !important; margin-bottom: 0.8rem; font-size: 1.1rem;">📍 Navigation</p>', unsafe_allow_html=True)
    
    page = st.radio(
        "Navigation",
        ["🔍 Upload & Analyze", "📊 Dashboard", "📜 History", "ℹ️ About"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    st.markdown("""
        <div style="padding: 1.2rem; background: white; border-radius: 10px; border: 2px solid #e8e8e8;">
            <h4 style="color: #2c3e50 !important; margin-top: 0; margin-bottom: 1rem; font-weight: 700;">✨ Features</h4>
            <ul style="color: #34495e !important; font-size: 0.95rem; line-height: 2; padding-left: 1.5rem; list-style-type: none;">
                <li style="color: #2c3e50 !important; font-weight: 600;">🤖 AI-Powered Analysis</li>
                <li style="color: #2c3e50 !important; font-weight: 600;">📊 Visual Analytics</li>
                <li style="color: #2c3e50 !important; font-weight: 600;">💯 Resume Scoring</li>
                <li style="color: #2c3e50 !important; font-weight: 600;">🎯 Skill Gap Analysis</li>
                <li style="color: #2c3e50 !important; font-weight: 600;">🎨 Job Matching</li>
                <li style="color: #2c3e50 !important; font-weight: 600;">📥 Export Reports</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

# Main Content
if page == "🔍 Upload & Analyze":
    st.markdown("""
        <div class="hero-section">
            <div class="hero-title">📄 Upload Your Resume</div>
            <div class="hero-subtitle">Get instant AI-powered insights and recommendations</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 15px; border: 3px dashed #3498db; margin-bottom: 1.5rem;">
            <p style="color: #2c3e50 !important; font-weight: 700 !important; font-size: 1.2rem; margin-bottom: 0.5rem; text-align: center;">
                📁 Choose your resume file
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose your resume file",
        type=["pdf", "docx", "txt"],
        help="Drag and drop file here • Limit 200MB per file • PDF, DOCX, TXT",
        label_visibility="collapsed"
    )
    
    # Additional helper text
    st.markdown("""
        <p style="text-align: center; color: #34495e !important; font-weight: 600 !important; font-size: 1rem; margin-top: 0.5rem;">
            Drag and drop your file above or click Browse files
        </p>
        <p style="text-align: center; color: #7f8c8d !important; font-weight: 600 !important; font-size: 0.95rem;">
            Supported formats: PDF, DOCX, TXT • Maximum size: 200MB
        </p>
    """, unsafe_allow_html=True)
    
    if uploaded_file:
        st.success(f"✅ File uploaded: **{uploaded_file.name}** ({uploaded_file.size / 1024:.2f} KB)")
        
        if st.button("🚀 Analyze Resume", type="primary"):
            with st.spinner("🔄 AI is analyzing your resume..."):
                try:
                    files = {"file": uploaded_file.getvalue()}
                    response = requests.post(API, files={"file": (uploaded_file.name, uploaded_file.getvalue())}, timeout=60)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.analysis_done = True
                        st.session_state.analysis_data = data
                        
                        # Add to history
                        st.session_state.history.append({
                            "filename": uploaded_file.name,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "data": data
                        })
                        
                        st.success("✅ Analysis complete!")
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {response.json().get('error', 'Unknown error')}")
                
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out. Please ensure the Flask server is running.")
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
    
    # Display results
    if st.session_state.analysis_done and st.session_state.analysis_data:
        st.markdown("---")
        
        data = st.session_state.analysis_data
        llm_data = data.get('llm_summary', {})
        
        if 'error' not in llm_data:
            score = calculate_resume_score(llm_data)
            
            # Score Display
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.plotly_chart(create_gauge_chart(score), use_container_width=True)
            
            # Professional Summary
            st.markdown(f"""
                <div class="summary-card">
                    <h2 style="margin-top: 0; color: #2c3e50 !important; font-weight: 700;">📝 Professional Summary</h2>
                    <p style="font-size: 1.1rem; line-height: 1.6; color: #34495e !important; font-weight: 500;">
                        {llm_data.get('professional_summary', 'No summary available')}
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            # Tabs for detailed analysis
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "💪 Strengths & Weaknesses", "🎯 Skills & Roles", "📧 Contact"])
            
            with tab1:
                st.markdown('<div class="tab-content">', unsafe_allow_html=True)
                
                # Metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{len(llm_data.get('strengths', []))}</div>
                        <div class="metric-label">Key Strengths</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{len(llm_data.get('weaknesses', []))}</div>
                        <div class="metric-label">Areas to Improve</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{len(llm_data.get('missing_skills', []))}</div>
                        <div class="metric-label">Missing Skills</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{len(llm_data.get('suggested_job_roles', []))}</div>
                        <div class="metric-label">Job Matches</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("")
                
                # Chart
                st.plotly_chart(create_skills_chart(llm_data), use_container_width=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            with tab2:
                st.markdown('<div class="tab-content">', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<h3 style="color: #2c3e50 !important; font-weight: 700;">💪 Key Strengths</h3>', unsafe_allow_html=True)
                    strengths = llm_data.get('strengths', [])
                    if strengths:
                        for strength in strengths:
                            st.markdown(f'<span class="strength-badge">✓ {strength}</span>', unsafe_allow_html=True)
                    else:
                        st.info("No strengths identified")
                
                with col2:
                    st.markdown('<h3 style="color: #2c3e50 !important; font-weight: 700;">⚠️ Areas for Improvement</h3>', unsafe_allow_html=True)
                    weaknesses = llm_data.get('weaknesses', [])
                    if weaknesses:
                        for weakness in weaknesses:
                            st.markdown(f'<span class="weakness-badge">! {weakness}</span>', unsafe_allow_html=True)
                    else:
                        st.success("No weaknesses identified")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            with tab3:
                st.markdown('<div class="tab-content">', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<h3 style="color: #2c3e50 !important; font-weight: 700;">🎯 Skills to Acquire</h3>', unsafe_allow_html=True)
                    missing = llm_data.get('missing_skills', [])
                    if missing:
                        for skill in missing:
                            st.markdown(f'<span class="skill-badge">→ {skill}</span>', unsafe_allow_html=True)
                    else:
                        st.success("No critical skills missing!")
                
                with col2:
                    st.markdown('<h3 style="color: #2c3e50 !important; font-weight: 700;">🎯 Recommended Job Roles</h3>', unsafe_allow_html=True)
                    roles = llm_data.get('suggested_job_roles', [])
                    if roles:
                        for role in roles:
                            st.markdown(f'<span class="role-badge">🎯 {role}</span>', unsafe_allow_html=True)
                    else:
                        st.info("No job roles suggested")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            with tab4:
                st.markdown('<div class="tab-content">', unsafe_allow_html=True)
                
                contact_col1, contact_col2 = st.columns(2)
                
                with contact_col1:
                    st.markdown(f"""
                    <div class="card">
                        <h3 style="color: #2c3e50 !important; font-weight: 700;">📧 Email Address</h3>
                        <p style="font-size: 1.2rem; color: #3498db !important; font-weight: 600;">{data.get('email', 'Not found')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with contact_col2:
                    st.markdown(f"""
                    <div class="card">
                        <h3 style="color: #2c3e50 !important; font-weight: 700;">📱 Phone Number</h3>
                        <p style="font-size: 1.2rem; color: #3498db !important; font-weight: 600;">{data.get('phone', 'Not found')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Download section
            st.markdown('<h3 style="color: #2c3e50 !important; font-weight: 700;">📥 Export Your Analysis</h3>', unsafe_allow_html=True)
            download_col1, download_col2, download_col3 = st.columns(3)
            
            with download_col1:
                json_data = json.dumps(data, indent=2)
                st.download_button(
                    label="📄 Download as JSON",
                    data=json_data,
                    file_name=f"resume_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with download_col2:
                txt_report = f"""
RESUME ANALYSIS REPORT
Score: {score}/100
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CONTACT INFORMATION
Email: {data.get('email', 'Not found')}
Phone: {data.get('phone', 'Not found')}

PROFESSIONAL SUMMARY
{llm_data.get('professional_summary', 'N/A')}

KEY STRENGTHS ({len(llm_data.get('strengths', []))})
{chr(10).join('• ' + s for s in llm_data.get('strengths', []))}

AREAS FOR IMPROVEMENT ({len(llm_data.get('weaknesses', []))})
{chr(10).join('• ' + w for w in llm_data.get('weaknesses', []))}

SKILLS TO ACQUIRE ({len(llm_data.get('missing_skills', []))})
{chr(10).join('• ' + m for m in llm_data.get('missing_skills', []))}

RECOMMENDED JOB ROLES ({len(llm_data.get('suggested_job_roles', []))})
{chr(10).join('• ' + r for r in llm_data.get('suggested_job_roles', []))}
"""
                st.download_button(
                    label="📝 Download as TXT",
                    data=txt_report,
                    file_name=f"resume_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        else:
            st.warning(f"⚠️ AI Analysis unavailable: {llm_data.get('error', 'Unknown error')}")

elif page == "📊 Dashboard":
    st.markdown("""
        <div class="hero-section">
            <div class="hero-title">📊 Analytics Dashboard</div>
            <div class="hero-subtitle">Visualize your resume insights</div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.analysis_done:
        data = st.session_state.analysis_data
        llm_data = data.get('llm_summary', {})
        
        if 'error' not in llm_data:
            score = calculate_resume_score(llm_data)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.plotly_chart(create_gauge_chart(score), use_container_width=True)
            
            with col2:
                st.plotly_chart(create_skills_chart(llm_data), use_container_width=True)
        else:
            st.info("No analytics available. Please analyze a resume first.")
    else:
        st.info("No data available. Please upload and analyze a resume first.")

elif page == "📜 History":
    st.markdown("""
        <div class="hero-section">
            <div class="hero-title">📜 Analysis History</div>
            <div class="hero-subtitle">View your past resume analyses</div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.history:
        for idx, item in enumerate(reversed(st.session_state.history)):
            with st.expander(f"📄 {item['filename']} - {item['timestamp']}"):
                st.json(item['data'])
    else:
        st.info("No history available yet. Analyze some resumes to see them here!")

else:  # About page
    st.markdown("""
        <div class="hero-section">
            <div class="hero-title">ℹ️ About Resume Analyzer Pro</div>
            <div class="hero-subtitle">AI-powered career insights</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<h3 style="color: #2c3e50 !important; font-weight: 700;">🎯 What is Resume Analyzer Pro?</h3>', unsafe_allow_html=True)
    
    st.markdown("""
    <p style="color: #34495e !important; font-weight: 500; line-height: 1.8;">
    Resume Analyzer Pro is an AI-powered tool that helps you improve your resume by providing:
    </p>
    
    <ul style="color: #34495e !important; font-weight: 500; line-height: 2;">
        <li><strong style="color: #2c3e50 !important;">Intelligent Analysis:</strong> Using advanced AI to understand your resume content</li>
        <li><strong style="color: #2c3e50 !important;">Visual Insights:</strong> Beautiful charts and graphs to visualize your strengths</li>
        <li><strong style="color: #2c3e50 !important;">Actionable Feedback:</strong> Specific recommendations for improvement</li>
        <li><strong style="color: #2c3e50 !important;">Job Matching:</strong> Suggestions for suitable job roles</li>
        <li><strong style="color: #2c3e50 !important;">Skill Gap Analysis:</strong> Identify missing skills for your target roles</li>
    </ul>
    """, unsafe_allow_html=True)
    
    st.markdown('<h3 style="color: #2c3e50 !important; font-weight: 700; margin-top: 2rem;">🚀 How to Use</h3>', unsafe_allow_html=True)
    
    st.markdown("""
    <ol style="color: #34495e !important; font-weight: 500; line-height: 2;">
        <li><strong style="color: #2c3e50 !important;">Upload</strong> your resume in PDF, DOCX, or TXT format</li>
        <li><strong style="color: #2c3e50 !important;">Wait</strong> for AI to analyze your content</li>
        <li><strong style="color: #2c3e50 !important;">Review</strong> the detailed feedback and visualizations</li>
        <li><strong style="color: #2c3e50 !important;">Download</strong> your analysis report</li>
        <li><strong style="color: #2c3e50 !important;">Improve</strong> your resume based on insights</li>
    </ol>
    """, unsafe_allow_html=True)
    
    st.markdown('<h3 style="color: #2c3e50 !important; font-weight: 700; margin-top: 2rem;">🛠️ Technology Stack</h3>', unsafe_allow_html=True)
    
    st.markdown("""
    <ul style="color: #34495e !important; font-weight: 500; line-height: 2;">
        <li><strong style="color: #2c3e50 !important;">Frontend:</strong> Streamlit</li>
        <li><strong style="color: #2c3e50 !important;">Backend:</strong> Flask API</li>
        <li><strong style="color: #2c3e50 !important;">AI Engine:</strong> Standalone Analyzer (Fast & Efficient)</li>
        <li><strong style="color: #2c3e50 !important;">Charts:</strong> Plotly</li>
        <li><strong style="color: #2c3e50 !important;">File Processing:</strong> PyPDF2, python-docx</li>
    </ul>
    """, unsafe_allow_html=True)
    
    st.markdown('<h3 style="color: #2c3e50 !important; font-weight: 700; margin-top: 2rem;">📞 Support</h3>', unsafe_allow_html=True)
    st.markdown('<p style="color: #34495e !important; font-weight: 500;">Need help? Have suggestions? Feel free to reach out!</p>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div class="footer-text">
    <p style="font-size: 1.1rem; color: #34495e !important; font-weight: 600;">Made with ❤️ using AI and Modern Web Technologies</p>
    <p style="font-size: 0.95rem; color: #7f8c8d !important; font-weight: 500;">Powered by Python • Built with Streamlit & Flask</p>
</div>
""", unsafe_allow_html=True)