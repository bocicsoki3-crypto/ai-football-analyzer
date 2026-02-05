import streamlit as st
import os
import datetime
import random
from dotenv import load_dotenv
from src.config import LEAGUE_IDS, LEAGUE_EMOJIS
from src.utils import get_active_leagues_and_matches, extract_text_from_pdf, get_detailed_stats
from src.analyzer import analyze_match_with_gpt4

# Load environment variables
load_dotenv()

# Page Config
st.set_page_config(page_title="AI Football Analyst", page_icon="⚽", layout="wide")

# --- FIREFLY ANIMATION GENERATOR ---
# Generate random fireflies with inline styles for position and animation timing
firefly_html = ""
for i in range(30):
    left = random.randint(0, 100)
    top = random.randint(0, 100)
    delay = random.uniform(0, 20)
    duration = random.uniform(10, 20)
    # Random movement range
    move_x = random.randint(-50, 50)
    move_y = random.randint(-50, 50)
    
    firefly_html += f"""
    <div class="firefly" style="
        left: {left}%; 
        top: {top}%; 
        animation-delay: {delay}s; 
        animation-duration: {duration}s;
        --move-x: {move_x}px;
        --move-y: {move_y}px;
    "></div>
    """

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
    
    /* Particles / Fireflies CSS */
    .firefly {
        position: fixed;
        width: 6px;
        height: 6px;
        background: rgba(255, 255, 255, 0.5);
        border-radius: 50%;
        box-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 0 0 20px rgba(255, 255, 255, 0.4);
        pointer-events: none;
        z-index: 0; /* Changed to 0 to be visible but behind text if containers have background */
        animation: float-firefly 15s infinite alternate ease-in-out;
    }

    @keyframes float-firefly {
        0% {
            transform: translate(0, 0);
            opacity: 0.2;
        }
        50% {
            opacity: 1;
        }
        100% {
            transform: translate(var(--move-x, 30px), var(--move-y, -30px));
            opacity: 0.2;
        }
    }
    
    /* UI Components */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        min-height: 60px; /* Uniform height */
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(90deg, #2E86C1 0%, #1B4F72 100%);
        color: white;
        border: none;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
        white-space: normal; /* Allow wrapping for long names */
        padding: 5px 10px;
        line-height: 1.2;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 10px rgba(0, 0, 0, 0.2);
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
    
    <!-- Animated Fireflies Injected Here -->
    {firefly_html}
    
""", unsafe_allow_html=True)

# Sidebar - League Selection (Dropdown to save API calls)
st.sidebar.title("📌 Bajnokságok")

# Session state to track selected match
if 'selected_match' not in st.session_state:
    st.session_state.selected_match = None

# 0. Select Date
selected_date = st.sidebar.date_input("Dátum választás", datetime.date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# 1. Fetch ALL matches for this date and filter by our leagues
with st.spinner("Meccsek betöltése..."):
    organized_matches = get_active_leagues_and_matches(date_str)

# 2. League Selector (Only show leagues with matches)
if organized_matches:
    active_leagues = sorted(list(organized_matches.keys()))
    selected_league = st.sidebar.selectbox("Válassz bajnokságot (csak aktívak):", active_leagues)
    
    if selected_league:
        st.sidebar.markdown(f"**{LEAGUE_EMOJIS.get(selected_league, '⚽')} {selected_league}**")
        
        matches = organized_matches[selected_league]
        for match in matches:
            # Button Label with Date and Time
            btn_label = f"{match['home']} vs {match['away']}\n({match['date']} {match['time']})"
            
            if st.sidebar.button(btn_label, key=match['id'], use_container_width=True):
                st.session_state.selected_match = match
else:
    st.sidebar.info("Ezen a napon nincs meccs a követett ligákban.")
    selected_league = None # Reset if no matches

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
