import streamlit as st
import os
import datetime
from dotenv import load_dotenv
from src.config import LEAGUE_IDS, LEAGUE_EMOJIS
from src.utils import get_matches_by_date, extract_text_from_pdf, get_detailed_stats
from src.analyzer import analyze_match_with_gpt4

# Load environment variables
load_dotenv()

# Page Config
st.set_page_config(page_title="AI Football Analyst", page_icon="⚽", layout="wide")

# --- AUTHENTICATION ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == os.getenv("SITE_PASSWORD", "admin123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Kérlek add meg a jelszót az oldal megtekintéséhez:", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Kérlek add meg a jelszót az oldal megtekintéséhez:", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Helytelen jelszó")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()
# ----------------------

# Custom CSS for dark mode and styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }

    /* Animated Background */
    .stApp {
        background: linear-gradient(to bottom, #0f0c29, #302b63, #24243e);
        color: #fff;
    }
    
    /* Particles */
    .firefly {
        position: fixed;
        left: 50%;
        top: 50%;
        width: 0.4vw;
        height: 0.4vw;
        margin: -0.2vw 0 0 -9.8vw;
        animation: ease 200s alternate infinite;
        pointer-events: none;
        z-index: -1;
    }
    
    .firefly::before,
    .firefly::after {
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        transform-origin: -10vw;
    }
    
    .firefly::before {
        background: black;
        opacity: 0.4;
        animation: drift ease alternate infinite;
    }
    
    .firefly::after {
        background: white;
        opacity: 0;
        box-shadow: 0 0 0vw 0vw yellow;
        animation: drift ease alternate infinite, flash ease infinite;
    }
    
    /* Randomize fireflies using nth-child would be hard in pure CSS injection without HTML structure control. 
       Instead, we will use a simpler "floating orbs" approach with fixed divs injected below. */
    
    /* UI Components */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%);
        color: white;
        border: none;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }

    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.1);
        color: white;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .stSelectbox>div>div>div {
        background-color: rgba(255, 255, 255, 0.1);
        color: white;
        border-radius: 10px;
    }

    h1, h2, h3 {
        color: #00d2ff;
        text-shadow: 0 0 10px rgba(0, 210, 255, 0.5);
    }

    .match-card {
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        margin-bottom: 10px;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #0f0c29; 
    }
    ::-webkit-scrollbar-thumb {
        background: #3a7bd5; 
        border-radius: 5px;
    }
    </style>
    
    <!-- Animated Orbs -->
    <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; overflow: hidden; pointer-events: none;">
        <div style="position: absolute; top: 20%; left: 10%; width: 300px; height: 300px; background: radial-gradient(circle, rgba(0,210,255,0.15) 0%, rgba(0,0,0,0) 70%); border-radius: 50%; animation: float 10s infinite ease-in-out;"></div>
        <div style="position: absolute; top: 70%; left: 80%; width: 200px; height: 200px; background: radial-gradient(circle, rgba(255,0,150,0.15) 0%, rgba(0,0,0,0) 70%); border-radius: 50%; animation: float 15s infinite ease-in-out reverse;"></div>
        <div style="position: absolute; top: 40%; left: 60%; width: 150px; height: 150px; background: radial-gradient(circle, rgba(0,255,100,0.1) 0%, rgba(0,0,0,0) 70%); border-radius: 50%; animation: float 12s infinite ease-in-out 2s;"></div>
        <div style="position: absolute; top: 80%; left: 20%; width: 250px; height: 250px; background: radial-gradient(circle, rgba(255,200,0,0.1) 0%, rgba(0,0,0,0) 70%); border-radius: 50%; animation: float 18s infinite ease-in-out 1s;"></div>
    </div>
    
    <style>
    @keyframes float {
        0% { transform: translate(0, 0); }
        50% { transform: translate(20px, -40px); }
        100% { transform: translate(0, 0); }
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar - League Selection (Dropdown to save API calls)
st.sidebar.title("📌 Bajnokságok")

# Session state to track selected match
if 'selected_match' not in st.session_state:
    st.session_state.selected_match = None

# 0. Select Date
selected_date = st.sidebar.date_input("Dátum választás", datetime.date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# 1. Select League
league_names = list(LEAGUE_IDS.keys())
selected_league = st.sidebar.selectbox("Válassz bajnokságot:", league_names)

# 2. Fetch matches for SELECTED league only
if selected_league:
    matches = get_matches_by_date(selected_league, date_str)
    
    st.sidebar.markdown(f"**{LEAGUE_EMOJIS.get(selected_league, '⚽')} {selected_league}**")
    
    if matches:
        for match in matches:
            btn_label = f"{match['home']} vs {match['away']} ({match['time']})"
            # Use a unique key combining league and match ID
            if st.sidebar.button(btn_label, key=f"{selected_league}_{match['id']}"):
                st.session_state.selected_match = match
    else:
        st.sidebar.info("Ezen a napon nincs meccs ebben a ligában.")

# Main Content
st.title("🤖 GPT-4o Football Analyst")

if st.session_state.selected_match:
    match = st.session_state.selected_match
    st.header(f"Match Analysis: {match['home']} vs {match['away']}")
    
    # PDF Upload
    uploaded_files = st.file_uploader("Upload Match Stats (PDF)", type="pdf", accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("Analyze Match 🚀"):
            with st.spinner("Extracting data and crunching numbers with GPT-4o..."):
                # 1. Extract Text
                pdf_text = ""
                for uploaded_file in uploaded_files:
                    text = extract_text_from_pdf(uploaded_file)
                    pdf_text += f"\n--- FILE: {uploaded_file.name} ---\n{text}\n"
                
                # 2. Analyze with AI (PDF ONLY - No RapidAPI Stats)
                match_name = f"{match['home']} vs {match['away']}"
                analysis_result = analyze_match_with_gpt4(pdf_text, match_name)
                
                if "error" in analysis_result:
                    st.error(analysis_result["error"])
                else:
                    # 3. Display Results
                    st.success("Analysis Complete!")
                    
                    # Sort by confidence (if not already sorted by API, but we did prompt for it)
                    # We assume the AI returns a list under a key, e.g., "predictions"
                    # If the AI returns a flat dict, we adapt.
                    # Our prompt asked for a list. Let's handle the response structure safely.
                    
                    predictions = analysis_result.get("predictions", [])
                    if not predictions and isinstance(analysis_result, list):
                        predictions = analysis_result
                    
                    # Display sorted by confidence
                    st.subheader("🏆 Top Predictions (Sorted by Confidence)")
                    
                    for pred in predictions:
                        confidence = pred.get("confidence", 0)
                        color = "green" if confidence > 75 else "orange" if confidence > 50 else "red"
                        
                        with st.container():
                            col1, col2, col3 = st.columns([2, 1, 4])
                            with col1:
                                st.markdown(f"**{pred.get('market')}**")
                                st.write(f"Pick: {pred.get('prediction')}")
                            with col2:
                                st.markdown(f"**{confidence}%**")
                                st.progress(confidence / 100)
                            with col3:
                                st.caption(pred.get('reasoning'))
                            st.divider()

else:
    st.info("👈 Please select a match from the sidebar to begin.")
    st.markdown("""
    ### How to use:
    1. Open a **League** in the sidebar.
    2. Click on a **Match**.
    3. Upload a **PDF** containing the stats.
    4. Get **GPT-4o** powered predictions sorted by confidence!
    """)
