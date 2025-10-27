import streamlit as st
import openai
import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Tuple, Optional
import re
from datetime import datetime
import urllib.parse
from dataclasses import dataclass

# Configure the page
st.set_page_config(
    page_title="TechCheck Pilot - Appliance Diagnostics",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS - Fix all white-on-white issues and match React UI
st.markdown("""
<style>
    /* Global background and text - FORCE dark text on light bg */
    * {
        color: #1e293b !important;
    }
    
    .stApp {
        background: linear-gradient(180deg, #fafafa 0%, #f1f5f9 100%) !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Force all text to be dark */
    p, span, div, label, h1, h2, h3, h4, h5, h6, li, a {
        color: #1e293b !important;
    }
    
    /* INPUT FIELDS - White background with dark text */
    .stTextInput input, .stTextArea textarea {
        background-color: #ffffff !important;
        color: #1e293b !important;
        border: 2px solid #cbd5e1 !important;
        border-radius: 10px !important;
        padding: 14px !important;
        font-size: 15px !important;
        font-weight: 500 !important;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15) !important;
        outline: none !important;
    }
    
    /* Labels */
    .stTextInput label, .stTextArea label {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        margin-bottom: 8px !important;
    }
    
    /* BUTTONS - Solid colors with good contrast */
    .stButton button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 14px 28px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5) !important;
    }
    
    /* Secondary buttons */
    .stButton button[kind="secondary"] {
        background: #ffffff !important;
        color: #1e293b !important;
        border: 2px solid #cbd5e1 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }
    
    /* PROBABILITY BADGE - Match React exactly */
    .prob-badge {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        background: #e2e8f0;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 12px 18px;
        min-width: 90px;
    }
    
    .prob-value {
        font-size: 32px;
        font-weight: 900;
        color: #1e293b;
        line-height: 1;
    }
    
    .prob-label {
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        margin-top: 4px;
        font-weight: 700;
    }
    
    /* CAUSE CARDS - Match React styling */
    .cause-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 24px;
        margin: 20px 0;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }
    
    .cause-high {
        background: linear-gradient(to right, #fef2f2 0%, #ffffff 40%);
        border-left: 5px solid #ef4444;
    }
    
    .cause-medium {
        background: linear-gradient(to right, #fffbeb 0%, #ffffff 40%);
        border-left: 5px solid #f59e0b;
    }
    
    .cause-low {
        background: linear-gradient(to right, #f0fdf4 0%, #ffffff 40%);
        border-left: 5px solid #10b981;
    }
    
    /* CHIP BUTTONS - React style */
    .chip-button {
        display: inline-flex;
        align-items: center;
        padding: 8px 16px;
        background: #f1f5f9;
        color: #334155;
        border: 1px solid #cbd5e1;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin: 6px 4px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .chip-blue {
        background: #eff6ff;
        color: #1e40af;
        border-color: #bfdbfe;
    }
    
    .chip-green {
        background: #f0fdf4;
        color: #166534;
        border-color: #bbf7d0;
    }
    
    .chip-red {
        background: #fef2f2;
        color: #991b1b;
        border-color: #fecaca;
    }
    
    .chip-violet {
        background: #faf5ff;
        color: #6b21a8;
        border-color: #e9d5ff;
    }
    
    /* INFO BADGES */
    .info-badge {
        display: inline-flex;
        align-items: center;
        padding: 6px 12px;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 700;
        color: #475569;
        margin: 4px;
    }
    
    /* EXPANDABLE SECTIONS - Better sizing */
    .streamlit-expanderHeader {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
        padding: 16px 20px !important;
        color: #0f172a !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
        min-height: 48px !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: #f8fafc !important;
        border-color: #94a3b8 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }
    
    .streamlit-expanderContent {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
        padding: 24px !important;
        max-height: 600px !important;
        overflow-y: auto !important;
    }
    
    /* Expander arrow icon */
    details summary {
        cursor: pointer !important;
    }
    
    details[open] summary {
        border-bottom: 1px solid #e2e8f0 !important;
        margin-bottom: 16px !important;
    }
    
    /* HEADERS - Gradient style */
    .gradient-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #ffffff !important;
        padding: 32px;
        border-radius: 16px;
        margin: 24px 0;
        text-align: center;
    }
    
    .gradient-header h1, .gradient-header h2, .gradient-header p {
        color: #ffffff !important;
    }
    
    /* VENDOR CARDS */
    .vendor-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        margin: 12px 0;
    }
    
    .vendor-header {
        background: #f8fafc;
        padding: 12px 16px;
        border-radius: 10px 10px 0 0;
        font-weight: 700;
        color: #1e293b;
        border-bottom: 1px solid #e2e8f0;
    }
    
    /* PROGRESS BARS */
    .stProgress > div > div {
        background: #e2e8f0 !important;
        height: 10px !important;
        border-radius: 6px !important;
    }
    
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%) !important;
    }
    
    /* ALERTS */
    .stAlert {
        background: #ffffff !important;
        border: 2px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 18px !important;
        color: #1e293b !important;
    }
    
    .stSuccess {
        background: #f0fdf4 !important;
        border-color: #10b981 !important;
        border-left-width: 5px !important;
    }
    
    .stWarning {
        background: #fffbeb !important;
        border-color: #f59e0b !important;
        border-left-width: 5px !important;
    }
    
    .stError {
        background: #fef2f2 !important;
        border-color: #ef4444 !important;
        border-left-width: 5px !important;
    }
    
    .stInfo {
        background: #eff6ff !important;
        border-color: #3b82f6 !important;
        border-left-width: 5px !important;
    }
    
    /* OUTCOME BUTTONS */
    .outcome-yes {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: #ffffff !important;
    }
    
    .outcome-no {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
        color: #ffffff !important;
    }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background: #f8fafc !important;
        border-right: 1px solid #e2e8f0 !important;
    }
    
    /* Links */
    a {
        color: #3b82f6 !important;
        text-decoration: none !important;
        font-weight: 600 !important;
    }
    
    a:hover {
        color: #2563eb !important;
        text-decoration: underline !important;
    }
</style>
""", unsafe_allow_html=True)

# Load API key
@st.cache_data
def load_api_key():
    # Try Streamlit secrets first (for cloud deployment)
    try:
        return st.secrets["OPENAI_API_KEY"]
    except (KeyError, FileNotFoundError):
        # Fall back to api.txt for local development
        try:
            with open('api.txt', 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            st.error("⚠️ API key not found. Please add OPENAI_API_KEY to Streamlit secrets or create api.txt file.")
            return None

# Initialize OpenAI client
def init_openai_client():
    api_key = load_api_key()
    if api_key:
        return openai.OpenAI(api_key=api_key)
    return None

# Web search function
def search_web(query: str, num_results: int = 10) -> List[Dict]:
    """Web search for parts and diagnostic information"""
    try:
        enhanced_query = f"{query} appliance parts troubleshooting repair"
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(enhanced_query)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem and snippet_elem:
                    results.append({
                        'title': title_elem.get_text().strip(),
                        'url': title_elem.get('href', ''),
                        'snippet': snippet_elem.get_text().strip()
                    })
            
            return results
        return []
    except Exception as e:
        return []

# Diagnostic analysis function - GPT-5 with built-in web search
def perform_diagnostic_analysis(client, model_number: str, problem_description: str) -> Dict:
    """Perform comprehensive diagnostic analysis using GPT-5 with web search"""
    
    diagnostic_prompt = f"""You are an expert appliance repair technician with 20+ years experience.

Model: {model_number}
Problem: {problem_description}

Search the web for the latest repair information, part numbers, and troubleshooting guides for this specific model.

Provide a HIGHLY DETAILED diagnostic analysis in this EXACT format:

1. **PROBABILITY DISTRIBUTION** (Must sum to 100%)
   Format: [XX%] Issue Title | One-line description
   List 3-5 issues in descending order

2. **For EACH issue above, provide COMPLETE details:**

   **Issue: [Issue Title]**
   
   **Difficulty:** [X/100]
   **Estimated Time:** [X minutes]
   
   **Detailed Explanation:**
   [2-3 sentences explaining the issue and why these symptoms indicate this problem]
   
   **Parts Needed:**
   - Part Name: [Exact part number if available, e.g., "5304475102"] - Description
   - [Additional parts if needed]
   
   **Verification Steps:**
   • Step 1: [Specific test to confirm issue]
   • Step 2: [Another verification method]
   • Step 3: [Final confirmation check]
   
   **Step-by-Step Repair:**
   1. [First step with specifics]
   2. [Second step with details]
   3. [Continue with clear instructions]
   
   **Safety Warnings:**
   - [Any electrical/mechanical safety concerns]
   
   **Video Resources:**
   - Search: "[Model] [issue] repair" on YouTube
   - Search: "[Part name] replacement tutorial"

Repeat this format for ALL issues. Be extremely specific with part numbers, verification steps, and repair instructions."""

    try:
        # Use GPT-4 Turbo with DuckDuckGo web search
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert appliance diagnostician. Provide extremely detailed, actionable guidance with specific part numbers and step-by-step instructions."},
                {"role": "user", "content": diagnostic_prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        analysis = response.choices[0].message.content
        
        # Web search using DuckDuckGo
        search_query = f"{model_number} {problem_description} repair parts"
        web_results = search_web(search_query, 15)
        
        # Extract probabilities
        probability_pattern = r'\[(\d+)%\]\s*([^|]+)\|\s*([^\n]+)'
        probabilities = re.findall(probability_pattern, analysis, re.MULTILINE)
        
        if not probabilities:
            probability_pattern = r'\[(\d+)%\]\s*([^-\n]+?)(?:\s*-\s*|\s*:\s*)([^\n]+)'
            probabilities = re.findall(probability_pattern, analysis, re.MULTILINE)
        
        structured_probs = []
        for p in probabilities:
            try:
                percent = int(p[0])
                title = p[1].strip()
                description = p[2].strip()
                structured_probs.append((percent, title, description))
            except (ValueError, IndexError):
                continue
        
        structured_probs.sort(key=lambda x: x[0], reverse=True)
        
        return {
            "full_analysis": analysis,
            "probabilities": structured_probs,
            "web_results": web_results,
            "timestamp": datetime.now().isoformat(),
            "model_number": model_number,
            "problem": problem_description
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "full_analysis": f"Unable to perform diagnostic analysis: {str(e)}",
            "probabilities": [],
            "web_results": [],
            "timestamp": datetime.now().isoformat()
        }

# Extract detailed information for each issue
def extract_issue_details(full_analysis: str, issue_title: str) -> Dict:
    """Extract detailed information for a specific issue from the analysis - WORKING VERSION"""
    
    # Find the issue section - the AI uses "Issue: [Title]" format
    issue_patterns = [
        rf'###?\s*Issue:\s*{re.escape(issue_title)}(.*?)(?=###?\s*Issue:|$)',
        rf'\*\*Issue:\s*{re.escape(issue_title)}\*\*(.*?)(?=\*\*Issue:|$)',
        rf'Issue:\s*{re.escape(issue_title)}(.*?)(?=Issue:|$)'
    ]
    
    section = None
    for pattern in issue_patterns:
        match = re.search(pattern, full_analysis, re.DOTALL | re.IGNORECASE)
        if match:
            section = match.group(1)
            break
    
    if not section:
        # Fallback: try to find any section with the issue title
        section = full_analysis
    
    # Extract difficulty - the format is "**Difficulty:** 60/100" (bold inline)
    difficulty = "N/A"
    diff_match = re.search(r'\*\*Difficulty:\*\*\s*(\d+)/100', section)
    if diff_match:
        difficulty = diff_match.group(1)
    
    # Extract time - the format is "**Estimated Time:** 45 minutes" (bold inline)
    time = "N/A"
    time_match = re.search(r'\*\*Estimated Time:\*\*\s*(\d+)\s*minutes?', section)
    if time_match:
        time = time_match.group(1)
    
    # Extract explanation - **Detailed Explanation:** followed by text
    explanation = ""
    expl_match = re.search(r'\*\*Detailed Explanation:\*\*(.*?)(?=\*\*|$)', section, re.DOTALL)
    if expl_match:
        explanation = expl_match.group(1).strip()
    
    # Extract parts - look for **Parts Needed:** section with list items
    parts = []
    parts_match = re.search(r'\*\*Parts Needed:\*\*(.*?)(?=\*\*|$)', section, re.DOTALL)
    if parts_match:
        parts_text = parts_match.group(1)
        # Look for list items (either numbered or bulleted)
        part_items = re.findall(r'[-•*]\s*(.+?)(?=\n[-•*]|\n\n|\*\*|$)', parts_text, re.DOTALL)
        parts = [p.strip() for p in part_items if p.strip() and len(p.strip()) > 5]
    
    # Extract verification steps - **Verification Steps:** with list
    verify_steps = []
    verify_match = re.search(r'\*\*Verification Steps:\*\*(.*?)(?=\*\*|$)', section, re.DOTALL)
    if verify_match:
        verify_text = verify_match.group(1)
        # Look for bullet points or numbered items
        steps = re.findall(r'[-•*]\s*(.+?)(?=\n[-•*]|\n\n|\*\*|$)', verify_text, re.DOTALL)
        if not steps:
            steps = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|\*\*|$)', verify_text, re.DOTALL)
        verify_steps = [s.strip() for s in steps if s.strip() and len(s.strip()) > 10]
    
    # Extract repair steps - **Step-by-Step Repair:** with numbered list
    repair_steps = []
    repair_match = re.search(r'\*\*Step-by-Step Repair:\*\*(.*?)(?=\*\*|$)', section, re.DOTALL)
    if repair_match:
        repair_text = repair_match.group(1)
        # Look for numbered or bulleted items
        steps = re.findall(r'[-•*]\s*(.+?)(?=\n[-•*]|\n\n|\*\*|$)', repair_text, re.DOTALL)
        if not steps:
            steps = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|\*\*|$)', repair_text, re.DOTALL)
        repair_steps = [s.strip() for s in steps if s.strip() and len(s.strip()) > 10]
    
    # Extract safety warnings - **Safety Warnings:** with list
    safety_warnings = []
    safety_match = re.search(r'\*\*Safety Warnings?:\*\*(.*?)(?=\*\*|$)', section, re.DOTALL)
    if safety_match:
        safety_text = safety_match.group(1)
        warnings = re.findall(r'[-•*]\s*(.+?)(?=\n[-•*]|\n\n|\*\*|$)', safety_text, re.DOTALL)
        safety_warnings = [w.strip() for w in warnings if w.strip() and len(w.strip()) > 10]
    
    # Extract video resources - **Video Resources:** with list
    video_searches = []
    video_match = re.search(r'\*\*Video Resources?:\*\*(.*?)(?=\*\*|$)', section, re.DOTALL)
    if video_match:
        video_text = video_match.group(1)
        videos = re.findall(r'[-•*]\s*(?:Search:\s*)?["\']?(.+?)["\']?(?:\s+on YouTube)?(?=\n[-•*]|\n\n|\*\*|$)', video_text, re.DOTALL)
        video_searches = [v.strip() for v in videos if v.strip() and len(v.strip()) > 5]
    
    return {
        "parts": parts,
        "verify_steps": verify_steps,
        "repair_steps": repair_steps,
        "safety_warnings": safety_warnings,
        "video_searches": video_searches,
        "difficulty": difficulty,
        "time": time,
        "explanation": explanation
    }

# Display probability badge
def display_probability_badge(percent: int):
    """Display React-style probability badge"""
    st.markdown(f"""
        <div class="prob-badge">
            <div class="prob-value">{percent}<span style="font-size:18px;">%</span></div>
            <div class="prob-label">PROBABILITY</div>
        </div>
    """, unsafe_allow_html=True)

# Main app
def main():
    # Compressed header - single line
    st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 20px; border-radius: 12px; margin: 16px 0; text-align: center;">
            <h1 style="font-size: 24px; margin: 0; font-weight: 700;">
                🔧 TechCheckPilot — Diagnostics with probability analysis
            </h1>
        </div>
    """, unsafe_allow_html=True)
    
    # Initialize OpenAI client
    client = init_openai_client()
    if not client:
        st.stop()
    
    # Initialize session state
    if "diagnosis" not in st.session_state:
        st.session_state.diagnosis = None
    if "diagnostic_complete" not in st.session_state:
        st.session_state.diagnostic_complete = False
    if "expanded_solutions" not in st.session_state:
        st.session_state.expanded_solutions = {}
    
    # Enhanced sidebar
    with st.sidebar:
        st.markdown("### 📋 About TechCheck Pilot")
        st.info("""
**AI-Powered Diagnostics** that:
- 🎯 Analyzes symptoms
- 📊 Calculates probabilities  
- 🔩 Recommends specific parts
- 📖 Provides repair steps
- 🛒 Finds vendor pricing
- ✅ Tracks outcomes
        """)
        
        st.markdown("---")
        st.markdown("### 🏪 Rochester Appliance")
        st.success("""
**Free Pickup Available!**

Visit us for all your appliance parts and expert advice.
        """)
        
        st.markdown("---")
        st.markdown("### 💡 Pro Tips")
        st.markdown("""
**For Best Results:**
- Be specific about symptoms
- Include error codes
- Note when issues occur
- Try high % causes first
        """)
        
        st.markdown("---")
        
        if st.button("🔄 Start New Diagnosis", use_container_width=True, type="primary"):
            st.session_state.diagnosis = None
            st.session_state.diagnostic_complete = False
            st.session_state.expanded_solutions = {}
            st.rerun()
        
        # Add statistics if diagnosis is complete
        if st.session_state.get("diagnostic_complete"):
            st.markdown("---")
            st.markdown("### 📊 Current Diagnosis")
            st.metric("Model", st.session_state.get("model_number", "N/A"))
            if st.session_state.get("diagnosis") and st.session_state["diagnosis"].get("probabilities"):
                st.metric("Issues Found", len(st.session_state["diagnosis"]["probabilities"]))
                top_prob = st.session_state["diagnosis"]["probabilities"][0][0]
                st.metric("Top Probability", f"{top_prob}%")
    
    # Main input section - NO section headers
    if not st.session_state.diagnostic_complete:
        # Tech Name and Job Name/Number
        col_emp, col_prob = st.columns(2)
        
        with col_emp:
            tech_name = st.text_input(
                "Tech Name *",
                placeholder="e.g., John Smith",
                help="Technician name"
            )
        
        with col_prob:
            job_number = st.text_input(
                "Job Name / Number *",
                placeholder="e.g., JOB-2024-001",
                help="Job or ticket number"
            )
        
        # Model Number (no "Appliance Information" header)
        model_number = st.text_input(
            "Model Number *",
            placeholder="e.g., FRFS2823AD, WRS325SDHZ, GDT665SSNSS",
            help="Find this on the appliance label or manual"
        )
        
        # Symptoms (renamed from Problem Description)
        problem_description = st.text_area(
            "Symptoms *",
            placeholder="What's happening with your appliance/HVAC unit?",
            height=120,
            help="Be specific about sounds, leaks, error codes, timing"
        )
        
        # Enhanced example section
        with st.expander("💡 See example descriptions & tips"):
            col_ex1, col_ex2 = st.columns(2)
            
            with col_ex1:
                st.markdown("**✅ Good Examples:**")
                st.success("""
- "Leaking water from bottom front after defrost cycle"
- "Not cooling, compressor runs constantly, frost in freezer"
- "Making loud grinding noise when dispensing ice"  
- "Display shows E1 error, not heating"
                """)
            
            with col_ex2:
                st.markdown("**❌ Too Vague:**")
                st.error("""
- "It's broken"
- "Not working"
- "Makes noise"
- "Has a problem"
                """)
            
            st.markdown("---")
            st.markdown("**💡 Include these details:**")
            st.markdown("""
- **When:** Does it happen all the time? Only when cooling? During defrost?
- **Sounds:** Grinding? Buzzing? Clicking? Silent?
- **Leaks:** Where exactly? How much? What color?
- **Error Codes:** Any numbers or letters on display?
            """)
        
        st.markdown("---")
        
        # Diagnose button - requires all 4 fields
        can_diagnose = bool(
            tech_name and tech_name.strip() and
            job_number and job_number.strip() and
            model_number and model_number.strip() and 
            problem_description and problem_description.strip()
        )
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        
        with col_btn2:
            if st.button("🔬 Perform Diagnosis", type="primary", use_container_width=True, disabled=not can_diagnose):
                # Use a SINGLE container for all status updates (prevents extra bars)
                status_container = st.empty()
                
                with status_container.container():
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Enhanced loading with better messages
                    status_text.markdown("**🧠 Analyzing with GPT-5 reasoning...**")
                    progress_bar.progress(30)
                    time.sleep(0.4)
                    
                    status_text.markdown("**🌐 Searching web for latest repair data...**")
                    progress_bar.progress(60)
                    time.sleep(0.3)
                    
                    diagnosis = perform_diagnostic_analysis(client, model_number, problem_description)
                    
                    progress_bar.progress(80)
                    status_text.markdown("**🔍 Extracting part numbers and solutions...**")
                    time.sleep(0.3)
                    
                    progress_bar.progress(100)
                    status_text.markdown("**✅ Diagnosis complete!**")
                    time.sleep(0.5)
                
                # Clear the entire container
                status_container.empty()
                
                st.session_state.diagnosis = diagnosis
                st.session_state.diagnostic_complete = True
                st.session_state.tech_name = tech_name
                st.session_state.job_number = job_number
                st.session_state.model_number = model_number
                st.session_state.problem_description = problem_description
                
                st.rerun()
        
        if not can_diagnose:
            st.warning("⚠️ Please fill in all required fields: Tech Name, Job Name/Number, Model Number, and Symptoms.")
    
    # Display diagnostic results
    else:
        diagnosis = st.session_state.diagnosis
        
        if "error" in diagnosis:
            st.error(f"❌ {diagnosis['error']}")
            return
        
        # Results header
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 20px; border-radius: 12px; margin: 16px 0; text-align: center;">
                <h2 style="margin: 0; font-size: 24px; font-weight: 700;">🔬 Diagnostic Results</h2>
                <p style="margin: 8px 0 0 0; font-size: 13px; opacity: 0.85;">
                    Tech: {st.session_state.tech_name} • Job: {st.session_state.job_number}
                </p>
                <p style="margin: 10px 0 0 0; font-size: 16px; font-weight: 600;">
                    Model: {st.session_state.model_number}
                </p>
                <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.9;">
                    {st.session_state.problem_description[:100]}{'...' if len(st.session_state.problem_description) > 100 else ''}
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Quick stats summary - FIXED to show actual web sources
        if diagnosis.get("probabilities"):
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            
            with col_stat1:
                st.markdown("""
                <div style="background: white; padding: 16px; border-radius: 10px; text-align: center; border: 2px solid #e2e8f0;">
                    <div style="font-size: 32px; font-weight: 800; color: #3b82f6;">
                        {}</div>
                    <div style="font-size: 13px; color: #64748b; margin-top: 4px;">
                        Probable Causes</div>
                </div>
                """.format(len(diagnosis["probabilities"])), unsafe_allow_html=True)
            
            with col_stat2:
                top_prob = diagnosis["probabilities"][0][0]
                st.markdown("""
                <div style="background: white; padding: 16px; border-radius: 10px; text-align: center; border: 2px solid #e2e8f0;">
                    <div style="font-size: 32px; font-weight: 800; color: #ef4444;">
                        {}%</div>
                    <div style="font-size: 13px; color: #64748b; margin-top: 4px;">
                        Top Probability</div>
                </div>
                """.format(top_prob), unsafe_allow_html=True)
            
            with col_stat3:
                # Count actual web results properly
                web_results = diagnosis.get("web_results", [])
                web_count = len([r for r in web_results if r.get('title') or r.get('url')])
                
                # Also count extracted videos and resources
                total_sources = web_count
                for prob, title, desc in diagnosis.get("probabilities", [])[:3]:
                    details = extract_issue_details(diagnosis["full_analysis"], title)
                    total_sources += len(details.get("video_searches", []))
                
                st.markdown("""
                <div style="background: white; padding: 16px; border-radius: 10px; text-align: center; border: 2px solid #e2e8f0;">
                    <div style="font-size: 32px; font-weight: 800; color: #10b981;">
                        {}</div>
                    <div style="font-size: 13px; color: #64748b; margin-top: 4px;">
                        Total Sources</div>
                </div>
                """.format(total_sources), unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Display probability distribution
        if diagnosis.get("probabilities"):
            st.markdown("## 🎯 Probable Causes (Ranked by Likelihood)")
            
            # Display top 3 causes
            for idx, (percent, title, desc) in enumerate(diagnosis["probabilities"][:3]):
                # Determine styling
                if percent >= 40:
                    card_class = "cause-high"
                    icon = "🔴"
                elif percent >= 20:
                    card_class = "cause-medium"
                    icon = "🟡"
                else:
                    card_class = "cause-low"
                    icon = "🟢"
                
                st.markdown(f'<div class="cause-card {card_class}">', unsafe_allow_html=True)
                
                col_badge, col_content = st.columns([1, 5])
                
                with col_badge:
                    display_probability_badge(percent)
                
                with col_content:
                    st.markdown(f"### {icon} {title}")
                    st.markdown(f"*{desc}*")
                    
                    # Solutions expander
                    with st.expander("🔧 View Solutions & Parts", expanded=False):
                        # Extract detailed information for this specific issue
                        issue_details = extract_issue_details(diagnosis["full_analysis"], title)
                        
                        # Display difficulty and time at top
                        col_diff, col_time = st.columns(2)
                        with col_diff:
                            st.markdown(f"**Difficulty:** {issue_details['difficulty']}/100")
                        with col_time:
                            st.markdown(f"**Estimated Time:** {issue_details['time']} min")
                        
                        # Explanation
                        if issue_details['explanation']:
                            st.markdown("**About This Issue:**")
                            st.info(issue_details['explanation'])
                        
                        st.markdown("---")
                        
                        # Action chips REORDERED: Verify, Part #, Video, Details
                        st.markdown("**📋 Solution Details:**")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if st.button("✅ Verify", key=f"verify_{idx}", use_container_width=True):
                                if issue_details['verify_steps']:
                                    st.markdown("### ✅ Verification Steps")
                                    st.markdown("*Complete these checks to confirm the diagnosis:*")
                                    for step_idx, step in enumerate(issue_details['verify_steps'], 1):
                                        st.markdown(f"""
                                        <div style="background: #f0fdf4; padding: 10px; border-radius: 8px; 
                                                    border-left: 4px solid #10b981; margin: 8px 0;">
                                            <strong style="color: #166534;">✓ Step {step_idx}:</strong><br>
                                            <span style="color: #14532d;">{step}</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    
                                    if issue_details['safety_warnings']:
                                        st.markdown("---")
                                        st.error("**⚠️ Safety Warnings:**")
                                        for warning in issue_details['safety_warnings']:
                                            st.markdown(f"🔴 {warning}")
                                else:
                                    st.info("✅ Standard verification: Check if the issue is resolved after repair.")
                        
                        with col2:
                            if st.button("🔩 Part #", key=f"parts_{idx}", use_container_width=True):
                                if issue_details['parts']:
                                    st.markdown("### 🔩 Parts Needed")
                                    for part_idx, part in enumerate(issue_details['parts'], 1):
                                        # Format: PartNumber — PartName (remove "Part Name:" prefix)
                                        # Extract part number
                                        part_match = re.search(r'(\d{7,12})\s*[-–—]\s*(.+)', part)
                                        if part_match:
                                            pn = part_match.group(1)
                                            name = part_match.group(2).replace("Part Name:", "").strip()
                                            display_text = f"{pn} — {name}"
                                        else:
                                            display_text = part.replace("Part Name:", "").strip()
                                        
                                        st.markdown(f"""
                                        <div style="background: #f8fafc; padding: 12px; border-radius: 8px; 
                                                    border-left: 4px solid #3b82f6; margin: 8px 0;">
                                            <strong style="color: #1e293b;">{display_text}</strong>
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.info("✅ No specific parts required for this repair. Try basic troubleshooting first.")
                        
                        with col3:
                            if st.button("🎥 Video", key=f"video_{idx}", use_container_width=True):
                                st.markdown("### 🎥 Video Tutorials")
                                st.markdown("*Click to watch repair guides on YouTube:*")
                                
                                if issue_details['video_searches']:
                                    for vid_idx, search in enumerate(issue_details['video_searches'], 1):
                                        youtube_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(search)}"
                                        st.markdown(f"""
                                        <div style="background: #fef2f2; padding: 10px; border-radius: 8px; 
                                                    border-left: 4px solid #ef4444; margin: 8px 0;">
                                            <strong style="color: #991b1b;">📺 Tutorial {vid_idx}:</strong><br>
                                            <a href="{youtube_url}" target="_blank" style="color: #dc2626; text-decoration: none;">
                                                {search} →
                                            </a>
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    search_term = f"{st.session_state.model_number} {title} repair"
                                    youtube_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(search_term)}"
                                    st.markdown(f"""
                                    <div style="background: #fef2f2; padding: 12px; border-radius: 8px; 
                                                border-left: 4px solid #ef4444; margin: 8px 0;">
                                        <a href="{youtube_url}" target="_blank" style="color: #dc2626; font-weight: 600;">
                                            📺 Search YouTube: {search_term} →
                                        </a>
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                        with col4:
                            if st.button("📖 Details", key=f"details_{idx}", use_container_width=True):
                                if issue_details['repair_steps']:
                                    st.markdown("### 📖 Step-by-Step Repair Guide")
                                    st.markdown(f"*Follow these {len(issue_details['repair_steps'])} steps carefully:*")
                                    
                                    for repair_idx, step in enumerate(issue_details['repair_steps'], 1):
                                        st.markdown(f"""
                                        <div style="background: #faf5ff; padding: 12px; border-radius: 8px; 
                                                    border-left: 4px solid #8b5cf6; margin: 10px 0;">
                                            <strong style="color: #6b21a8;">🔧 Step {repair_idx}:</strong><br>
                                            <span style="color: #581c87;">{step}</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    
                                    if issue_details['safety_warnings']:
                                        st.markdown("---")
                                        st.error("**⚠️ IMPORTANT Safety Warnings:**")
                                        for warning in issue_details['safety_warnings']:
                                            st.markdown(f"🔴 {warning}")
                                else:
                                    st.markdown("### 📖 Repair Information")
                                    st.info(issue_details['explanation'] if issue_details['explanation'] else "Detailed repair information available in full diagnostic report.")
                        
                        # NO vendor links section - removed per manager request
                        
                        # Outcome tracking - Radio buttons in colored box
                        st.markdown("---")
                        
                        # Initialize outcome state for this solution
                        outcome_key = f"outcome_{idx}"
                        if outcome_key not in st.session_state:
                            st.session_state[outcome_key] = None
                        
                        # Determine box color based on selection
                        if st.session_state[outcome_key] == "Yes, resolved":
                            box_color = "#f0fdf4"  # Green tint
                            border_color = "#10b981"
                        elif st.session_state[outcome_key] == "No, not resolved":
                            box_color = "#fff7ed"  # Amber tint
                            border_color = "#f59e0b"
                        else:
                            box_color = "#f8fafc"  # Neutral
                            border_color = "#cbd5e1"
                        
                        st.markdown(f"""
                        <div style="background: {box_color}; border: 2px solid {border_color}; 
                                    border-radius: 10px; padding: 16px; margin: 12px 0;">
                            <strong style="color: #1e293b; font-size: 14px;">📊 Did this recommendation resolve the problem?</strong>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Radio buttons for outcome
                        outcome = st.radio(
                            "Select outcome:",
                            options=["Yes, resolved", "No, not resolved"],
                            key=outcome_key,
                            horizontal=False,
                            label_visibility="collapsed"
                        )
                
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
            
            # Escalation card if more than 3 issues
            if len(diagnosis["probabilities"]) > 3:
                st.markdown("""
                    <div class="cause-card" style="background: #fffbeb; border-left: 5px solid #f59e0b;">
                        <h3 style="color: #92400e; margin: 0 0 12px 0;">
                            ⚠️ Additional Higher-Technical Possibilities
                        </h3>
                        <p style="color: #78350f; margin: 0; font-size: 15px;">
                            Beyond the top recommendations shown, there are other less common, higher-technical 
                            issues that may apply. Please contact a qualified technician if the above solutions 
                            don't resolve the problem.
                        </p>
                    </div>
                """, unsafe_allow_html=True)
        
        # Full report
        with st.expander("📄 View Full Diagnostic Report"):
            st.markdown(diagnosis["full_analysis"])
        
        # Web sources
        if diagnosis.get("web_results"):
            with st.expander("🌐 Web Research Sources"):
                for idx, result in enumerate(diagnosis["web_results"][:10], 1):
                    st.markdown(f"{idx}. [{result['title']}]({result['url']})")
                    st.caption(result['snippet'])
                    st.markdown("---")
        
        # Action buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 New Diagnosis", use_container_width=True):
                st.session_state.diagnosis = None
                st.session_state.diagnostic_complete = False
                st.session_state.expanded_solutions = {}
                st.rerun()
        
        with col2:
            report_text = f"""DIAGNOSTIC REPORT
Tech: {st.session_state.tech_name}
Job: {st.session_state.job_number}
Model: {st.session_state.model_number}
Symptoms: {st.session_state.problem_description}
Generated: {diagnosis['timestamp']}

{diagnosis['full_analysis']}
"""
            st.download_button(
                label="📥 Download Report",
                data=report_text,
                file_name=f"diagnostic_{st.session_state.model_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col3:
            if st.button("📞 Contact Technician", use_container_width=True):
                st.info("📞 **Need professional help?** Contact Rochester Appliance or a certified appliance technician in your area.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; padding: 20px; background: #f8fafc; 
                    border-radius: 10px; margin-top: 32px;">
            <p style="color: #64748b; font-size: 12px; margin: 0;">
                <strong style="color: #1e293b;">TechCheckPilot</strong> — Some diagnostic information is AI-generated. 
                Please verify with a professional technician for complex repairs.
            </p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
