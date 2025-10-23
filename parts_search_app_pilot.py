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
    
    /* EXPANDABLE SECTIONS */
    .streamlit-expanderHeader {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
        padding: 14px 18px !important;
        color: #0f172a !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: #f8fafc !important;
        border-color: #94a3b8 !important;
    }
    
    .streamlit-expanderContent {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
        padding: 20px !important;
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

# Diagnostic analysis function
def perform_diagnostic_analysis(client, model_number: str, problem_description: str) -> Dict:
    """Perform comprehensive diagnostic analysis with detailed solutions"""
    
    # Search the web for relevant information
    search_query = f"{model_number} {problem_description} repair parts"
    web_results = search_web(search_query, 15)
    
    # Create context from web results
    web_context = "\n".join([f"- {r['title']}: {r['snippet']}" for r in web_results[:10]])
    
    diagnostic_prompt = f"""You are an expert appliance repair technician with 20+ years experience.

Model: {model_number}
Problem: {problem_description}

Web Research Context:
{web_context}

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
    # Gradient header
    st.markdown("""
        <div class="gradient-header">
            <h1 style="font-size: 42px; margin: 0;">🔧 TechCheck Pilot</h1>
            <p style="font-size: 18px; margin: 12px 0 0 0; opacity: 0.95;">
                AI-Powered Kitchen Appliance Diagnostics with Probability Analysis
            </p>
            <p style="font-size: 14px; margin: 8px 0 0 0; opacity: 0.85; font-style: italic;">
                Editor-curated diagnostics • Vendor pricing • Repair guidance
            </p>
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
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📋 About")
        st.info("""
**TechCheck Pilot** uses AI to:
- Analyze symptoms
- Calculate probabilities
- Recommend parts
- Provide repair steps
- Find vendors
        """)
        
        if st.button("🔄 Start New Diagnosis", use_container_width=True):
            st.session_state.diagnosis = None
            st.session_state.diagnostic_complete = False
            st.session_state.expanded_solutions = {}
            st.rerun()
    
    # Main input section
    if not st.session_state.diagnostic_complete:
        st.markdown("## 🏷️ Enter Appliance Information")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            model_number = st.text_input(
                "Model Number *",
                placeholder="e.g., FRFS2823AD, WRS325SDHZ, GDT665SSNSS",
                help="Find this on the appliance label or manual"
            )
        
        with col2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.info("💡 Required field")
        
        st.markdown("### 📋 Problem Description")
        problem_description = st.text_area(
            "What's happening with your appliance? *",
            placeholder="Be specific: sounds, leaks, error codes, when it happens, etc.",
            height=120,
            help="More details = better diagnosis"
        )
        
        # Example
        with st.expander("💡 See example descriptions"):
            st.markdown("""
**Good examples:**
- "Leaking water from bottom front after defrost cycle"
- "Not cooling, compressor runs constantly, frost in freezer"
- "Making loud grinding noise when dispensing ice"
- "Display shows E1 error, not heating"
            """)
        
        st.markdown("---")
        
        # Diagnose button
        can_diagnose = bool(model_number and model_number.strip() and problem_description and problem_description.strip())
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        
        with col_btn2:
            if st.button("🔬 Perform AI Diagnosis", type="primary", use_container_width=True, disabled=not can_diagnose):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("🌐 Searching web...")
                progress_bar.progress(33)
                time.sleep(0.3)
                
                status_text.text("🧠 Analyzing with AI...")
                progress_bar.progress(66)
                
                diagnosis = perform_diagnostic_analysis(client, model_number, problem_description)
                
                progress_bar.progress(100)
                status_text.text("✅ Complete!")
                time.sleep(0.5)
                
                st.session_state.diagnosis = diagnosis
                st.session_state.diagnostic_complete = True
                st.session_state.model_number = model_number
                st.session_state.problem_description = problem_description
                
                progress_bar.empty()
                status_text.empty()
                st.rerun()
        
        if not can_diagnose:
            st.warning("⚠️ Please enter both model number and problem description.")
    
    # Display diagnostic results
    else:
        diagnosis = st.session_state.diagnosis
        
        if "error" in diagnosis:
            st.error(f"❌ {diagnosis['error']}")
            return
        
        # Model info header
        st.markdown(f"""
            <div class="gradient-header">
                <h2 style="margin: 0; font-size: 28px;">🔬 Diagnostic Results</h2>
                <p style="margin: 12px 0 0 0; font-size: 18px; font-weight: 600;">
                    Model: {st.session_state.model_number}
                </p>
                <p style="margin: 8px 0 0 0; font-size: 15px; opacity: 0.9;">
                    {st.session_state.problem_description[:120]}{'...' if len(st.session_state.problem_description) > 120 else ''}
                </p>
            </div>
        """, unsafe_allow_html=True)
        
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
                        
                        # Action chips with REAL information
                        st.markdown("**📋 Solution Details:**")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if st.button("🔩 Part #", key=f"parts_{idx}", use_container_width=True):
                                if issue_details['parts']:
                                    st.markdown("### 🔩 Parts Needed")
                                    for part_idx, part in enumerate(issue_details['parts'], 1):
                                        st.markdown(f"**{part_idx}.** {part}")
                                        st.markdown("")
                                else:
                                    st.info("No specific parts required for this repair. Try basic troubleshooting first.")
                        
                        with col2:
                            if st.button("✅ Verify", key=f"verify_{idx}", use_container_width=True):
                                if issue_details['verify_steps']:
                                    st.markdown("### ✅ Verification Steps")
                                    for step_idx, step in enumerate(issue_details['verify_steps'], 1):
                                        st.markdown(f"**{step_idx}.** {step}")
                                        st.markdown("")
                                    
                                    if issue_details['safety_warnings']:
                                        st.warning("**⚠️ Safety Warnings:**")
                                        for warning in issue_details['safety_warnings']:
                                            st.markdown(f"• {warning}")
                                else:
                                    st.info("Standard verification: Check if the issue is resolved after repair.")
                        
                        with col3:
                            if st.button("🎥 Video", key=f"video_{idx}", use_container_width=True):
                                if issue_details['video_searches']:
                                    st.markdown("### 🎥 Video Tutorials")
                                    st.markdown("**Search on YouTube:**")
                                    for vid_idx, search in enumerate(issue_details['video_searches'], 1):
                                        youtube_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(search)}"
                                        st.markdown(f"**{vid_idx}.** [{search}]({youtube_url})")
                                        st.markdown("")
                                else:
                                    search_term = f"{st.session_state.model_number} {title} repair"
                                    youtube_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(search_term)}"
                                    st.markdown(f"[Search YouTube: {search_term}]({youtube_url})")
                        
                        with col4:
                            if st.button("📖 Details", key=f"details_{idx}", use_container_width=True):
                                if issue_details['repair_steps']:
                                    st.markdown("### 📖 Step-by-Step Repair Guide")
                                    for repair_idx, step in enumerate(issue_details['repair_steps'], 1):
                                        st.markdown(f"**Step {repair_idx}:** {step}")
                                        st.markdown("")
                                    
                                    if issue_details['safety_warnings']:
                                        st.error("**⚠️ Safety Warnings:**")
                                        for warning in issue_details['safety_warnings']:
                                            st.markdown(f"• {warning}")
                                else:
                                    # Fallback to showing relevant section from full analysis
                                    st.markdown("### 📖 Repair Information")
                                    st.markdown(diagnosis["full_analysis"][:1000])
                        
                        # Shopping links with actual part numbers
                        st.markdown("---")
                        st.markdown("### 🛒 Where to Buy Parts")
                        
                        if issue_details['parts']:
                            st.markdown("**Search for these specific parts:**")
                            
                            # Extract part numbers from parts list
                            part_numbers = []
                            for part in issue_details['parts']:
                                # Look for numbers that could be part numbers
                                numbers = re.findall(r'\b\d{7,12}\b', part)
                                if numbers:
                                    part_numbers.extend(numbers)
                            
                            if part_numbers:
                                for pn in part_numbers[:3]:  # Show up to 3 parts
                                    st.markdown(f"**Part #{pn}:**")
                                    col_a, col_b, col_c = st.columns(3)
                                    
                                    with col_a:
                                        ra_url = "https://maps.google.com/?q=Rochester+Appliance"
                                        st.markdown(f"[🏪 Rochester Appliance]({ra_url})")
                                        st.caption("Free pickup")
                                    
                                    with col_b:
                                        amazon_url = f"https://www.amazon.com/s?k={urllib.parse.quote_plus(pn)}"
                                        st.markdown(f"[📦 Amazon]({amazon_url})")
                                        st.caption("Fast shipping")
                                    
                                    with col_c:
                                        ps_url = f"https://www.partselect.com/search?searchterm={urllib.parse.quote_plus(pn)}"
                                        st.markdown(f"[🔧 PartSelect]({ps_url})")
                                        st.caption("OEM parts")
                                    
                                    st.markdown("")
                            else:
                                # Generic search if no specific part numbers found
                                search_term = f"{st.session_state.model_number} {title}"
                                col_a, col_b, col_c = st.columns(3)
                                
                                with col_a:
                                    st.markdown(f"[🏪 Rochester Appliance](https://maps.google.com/?q=Rochester+Appliance)")
                                    st.caption("Free pickup")
                                
                                with col_b:
                                    st.markdown(f"[📦 Amazon](https://www.amazon.com/s?k={urllib.parse.quote_plus(search_term)})")
                                    st.caption("Fast shipping")
                                
                                with col_c:
                                    st.markdown(f"[🔧 PartSelect](https://www.partselect.com/search?searchterm={urllib.parse.quote_plus(search_term)})")
                                    st.caption("OEM parts")
                        else:
                            st.info("No parts needed for basic troubleshooting. Try the verification steps first.")
                        
                        # Outcome tracking
                        st.markdown("---")
                        st.markdown("#### 📊 Did this recommendation resolve the problem?")
                        
                        col_yes, col_no, _ = st.columns([1, 1, 2])
                        
                        with col_yes:
                            if st.button("✅ Yes — Resolved", key=f"yes_{idx}", type="primary", use_container_width=True):
                                st.success("🎉 Great! Your feedback has been recorded.")
                        
                        with col_no:
                            if st.button("❌ No — Not resolved", key=f"no_{idx}", use_container_width=True):
                                st.warning("📝 Noted. Try the next solution or contact a technician.")
                
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
Model: {st.session_state.model_number}
Problem: {st.session_state.problem_description}
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
                st.info("For professional assistance, contact a certified appliance technician.")

if __name__ == "__main__":
    main()
