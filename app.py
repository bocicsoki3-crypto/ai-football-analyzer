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

    /* Prediction Card Design */
    .prediction-card {
        background: rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        border-left: 5px solid #3a7bd5; /* Default blue */
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .prediction-card:hover {
        transform: translateY(-2px);
    }
    .prediction-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .prediction-market {
        font-size: 1.1em;
        font-weight: 700;
        color: #fff;
    }
    .prediction-value {
        font-size: 1.2em;
        font-weight: 800;
        color: #00d2ff;
        margin-top: 5px;
    }
    .confidence-box {
        background: rgba(0, 0, 0, 0.3);
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 0.9em;
        font-weight: 600;
        white-space: nowrap;
    }
    .reasoning-text {
        font-size: 0.95em;
        color: #e0e0e0;
        line-height: 1.6;
        margin-top: 15px;
        border-top: 1px solid rgba(255,255,255,0.1);
        padding-top: 10px;
        font-style: italic;
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
st.title("🤖 GPT-4o Foci Elemző")

if st.session_state.selected_match:
    match = st.session_state.selected_match
    st.header(f"Mérkőzés Elemzés: {match['home']} vs {match['away']}")
    
    # Form for Upload and Analysis to prevent stuttering
    with st.form("analysis_form"):
        uploaded_files = st.file_uploader("Statisztikák Feltöltése (PDF)", type="pdf", accept_multiple_files=True)
        submitted = st.form_submit_button("Elemzés Indítása 🚀")
    
    if submitted:
        if uploaded_files:
            with st.spinner("Adatok kinyerése és elemzés a GPT-4o modellel..."):
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
                    st.success("Elemzés kész! 📊")
                    
                    # Sort by confidence
                    predictions = analysis_result.get("predictions", [])
                    if not predictions and isinstance(analysis_result, list):
                        predictions = analysis_result
                    
                    # Display sorted by confidence
                    st.subheader("🏆 AI Tippek (Magabiztosság szerint)")
                    
                    for pred in predictions:
                        confidence = pred.get("confidence", 0)
                        market = pred.get("market", "Ismeretlen piac")
                        pick = pred.get("prediction", "N/A")
                        reasoning = pred.get("reasoning", "Nincs indoklás.")
                        
                        # Dynamic colors based on confidence
                        if confidence >= 80:
                            border_color = "#4CAF50" # Green
                            icon = "🔥"
                        elif confidence >= 60:
                            border_color = "#FFC107" # Amber
                            icon = "⚠️"
                        else:
                            border_color = "#FF5722" # Red
                            icon = "🎲"
                        
                        # Render HTML Card
                        html_card = f"""
                        <div class="prediction-card" style="border-left: 5px solid {border_color};">
                            <div class="prediction-header">
                                <div>
                                    <div class="prediction-market">{icon} {market}</div>
                                    <div class="prediction-value" style="color: {border_color};">{pick}</div>
                                </div>
                                <div class="confidence-box" style="color: {border_color};">
                                    {confidence}% Magabiztosság
                                </div>
                            </div>
                            <div style="background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px; width: 100%; margin: 15px 0;">
                                <div style="background: {border_color}; height: 100%; border-radius: 4px; width: {confidence}%;"></div>
                            </div>
                            <div class="reasoning-text">
                                💡 {reasoning}
                            </div>
                        </div>
                        """
                        st.markdown(html_card, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Kérlek tölts fel legalább egy PDF fájlt az elemzéshez!")

else:
    st.info("👈 Válassz egy meccset a bal oldali sávból a kezdéshez!")
    st.markdown("""
    ### Használati útmutató:
    1. Válassz egy **Bajnokságot** a bal oldalon.
    2. Kattints egy **Meccsre**.
    3. Töltsd fel a **PDF statisztikákat** (opcionális, de ajánlott).
    4. Kattints az **Analyze Match** gombra a GPT-4o elemzéshez!
    """)
