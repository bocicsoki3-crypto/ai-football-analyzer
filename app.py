import streamlit as st
import os
import pandas as pd
from datetime import date
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

from src.data_manager import DataManager
from src.ai_agents import AICommittee
from src.db_manager import DBManager

# Page configuration
st.set_page_config(
    page_title="AI Committee Football Analyzer Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Glassmorphism & Dark Theme ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        color: #e0e0e0;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.3);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Glassmorphism Cards/Expanders */
    div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        margin-bottom: 15px;
        overflow: hidden;
    }
    
    /* Headers inside Expanders */
    .streamlit-expanderHeader {
        background-color: transparent !important;
        color: #ffffff !important;
        font-weight: 600;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        text-transform: uppercase;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 210, 255, 0.4);
    }
    
    /* Inputs & Selectboxes */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: rgba(255, 255, 255, 0.1);
        color: white;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Typography */
    h1, h2, h3 {
        color: #ffffff;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Custom Match Button in Sidebar */
    .match-btn {
        width: 100%;
        text-align: left;
        margin: 5px 0;
    }
    </style>
""", unsafe_allow_html=True)
# -----------------------------------------------

# --- Authentication ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == os.environ.get("APP_PASSWORD", "admin123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Kérem a jelszót az alkalmazás eléréséhez", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Kérem a jelszót az alkalmazás eléréséhez", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Helytelen jelszó")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()
# ----------------------

# Initialize modules
@st.cache_resource
def get_managers():
    return DataManager(), AICommittee(), DBManager()

data_manager, ai_committee, db_manager = get_managers()

# Sidebar for Navigation
with st.sidebar:
    st.markdown("## ⚽ Vezérlőpult")
    
    # API Check (Silent if keys exist)
    if not os.environ.get("RAPIDAPI_KEY") or not os.environ.get("GROQ_API_KEY"):
        st.error("⚠️ Hiányzó API Kulcsok! Ellenőrizd a .env fájlt.")
    
    # Load Matches Button
    if st.button("🔄 Mai meccsek frissítése", use_container_width=True):
        with st.spinner("Meccsek letöltése..."):
            fixtures = data_manager.get_todays_fixtures()
            if isinstance(fixtures, list) and fixtures:
                st.session_state['fixtures'] = fixtures
                st.success(f"✅ {len(fixtures)} meccs betöltve!")
            elif isinstance(fixtures, dict) and "error" in fixtures:
                st.error(f"Hiba: {fixtures['error']}")
            else:
                st.error("Nem találtam mai meccset.")
                
    st.markdown("---")
    
    # Display Leagues and Matches
    if 'fixtures' in st.session_state:
        fixtures = st.session_state['fixtures']
        leagues = sorted(list(set([f['league']['name'] for f in fixtures])))
        
        st.markdown("### 🏆 Bajnokságok")
        for league in leagues:
            league_fixtures = [f for f in fixtures if f['league']['name'] == league]
            # Expander for each league
            with st.expander(f"{league} ({len(league_fixtures)})"):
                for f in league_fixtures:
                    try:
                        match_time = pd.to_datetime(f['fixture']['date']).strftime('%H:%M')
                    except:
                        match_time = "??"
                    
                    # Button for each match
                    btn_label = f"{match_time} | {f['teams']['home']['name']} vs {f['teams']['away']['name']}"
                    if st.button(btn_label, key=f"btn_{f['fixture']['id']}", use_container_width=True):
                         st.session_state['current_match_obj'] = f
                         # Clear previous analysis if switching match
                         if 'analysis_results' in st.session_state:
                             del st.session_state['analysis_results']
                         st.rerun()

# Main content
st.title("⚽ AI Committee Football Analyzer Pro")
st.markdown("---")

# Tabs
tab1, tab2 = st.tabs(["📅 Napi Elemzés", "📚 Archívum/Tanulságok"])

with tab1:
    if 'current_match_obj' in st.session_state:
        match = st.session_state['current_match_obj']
        home_name = match['teams']['home']['name']
        away_name = match['teams']['away']['name']
        
        st.markdown(f"<h1 style='text-align: center; font-size: 3rem;'>{home_name} <span style='color:#00d2ff'>VS</span> {away_name}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; opacity: 0.7; font-size: 1.2rem;'>🏆 {match['league']['name']} | 🏟️ {match['fixture']['venue']['name'] or 'Ismeretlen stadion'}</p>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Analysis Trigger
        col_center = st.columns([1, 2, 1])
        with col_center[1]:
            analyze_clicked = st.button("🚀 BIZOTTSÁG ÖSSZEHÍVÁSA (ELEMZÉS START)", use_container_width=True)
        
        if analyze_clicked:
            fixture_id = match['fixture']['id']
            home_id = match['teams']['home']['id']
            away_id = match['teams']['away']['id']
            league_id = match['league']['id']
            season = match['league']['season']
            
            with st.spinner("🕵️ Az ügynökök dolgoznak... (Ez eltarthat 10-20 másodpercig)"):
                # 1. Gather detailed data
                match_details = data_manager.get_match_details(fixture_id, home_id, away_id, league_id, season)
                
                # 2. Get learned lessons
                lessons = db_manager.get_lessons()
                
                # 3. Run AI Committee
                results = ai_committee.analyze_match(match_details, home_name, away_name, lessons)
                
                st.session_state['analysis_results'] = results
                st.session_state['selected_match_data'] = match

        # Display Results
        if 'analysis_results' in st.session_state:
            results = st.session_state['analysis_results']
            
            st.markdown("---")
            st.subheader("📝 A Bizottság Jelentése")
            
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("📊 STATISZTIKUS JELENTÉSE (Groq)", expanded=True):
                    st.write(results['statistician'])
                with st.expander("🕵️ HÍRSZERZŐ JELENTÉSE (Groq)", expanded=True):
                    st.write(results['scout'])
            with col2:
                with st.expander("🧠 TAKTIKUS JELENTÉSE (Groq)", expanded=True):
                    st.write(results['tactician'])
                with st.expander("👔 A FŐNÖK DÖNTÉSE (Groq)", expanded=True):
                    st.markdown(results['boss'])
            
            # Save to DB
            if st.button("💾 Eredmény mentése az Archívumba", use_container_width=True):
                # Use stored match data if available
                if 'selected_match_data' in st.session_state:
                        home_team = st.session_state['selected_match_data']['teams']['home']['name']
                        away_team = st.session_state['selected_match_data']['teams']['away']['name']
                else:
                        home_team = home_name
                        away_team = away_name

                db_manager.save_prediction(
                    home_team, 
                    away_team, 
                    results, 
                    results['boss']
                )
                st.success("✅ Mentve az adatbázisba!")
                
    else:
        # Welcome Screen
        st.markdown("""
        <div style='text-align: center; padding: 100px 20px; background: rgba(255,255,255,0.05); border-radius: 20px;'>
            <h1 style='font-size: 5rem;'>⚽</h1>
            <h2>Üdvözöllek az Elemző Központban!</h2>
            <p style='font-size: 1.2rem; opacity: 0.8;'>Kezdéshez töltsd be a mai meccseket, majd válassz egyet a bal oldali sávból!</p>
            <p>👈 (Nyisd le a bajnokságokat a bal oldalon)</p>
        </div>
        """, unsafe_allow_html=True)


with tab2:
    st.header("Archívum és Tanulságok")
    
    predictions = db_manager.get_all_predictions()
    if predictions:
        df = pd.DataFrame(predictions)
        st.dataframe(df[['date', 'home_team', 'away_team', 'predicted_result', 'actual_result', 'is_correct', 'lesson_learned']])
        
        st.subheader("Eredmény Frissítése & Tanulás")
        pred_id = st.selectbox("Válassz egy korábbi tippet frissítéshez (ID):", df['id'].tolist())
        
        if pred_id:
            row = df[df['id'] == pred_id].iloc[0]
            st.write(f"Meccs: {row['home_team']} vs {row['away_team']}")
            st.write(f"Tipp: {row['predicted_result']}")
            
            new_result = st.text_input("Tényleges végeredmény:", value=row['actual_result'] if row['actual_result'] else "")
            is_correct = st.checkbox("Helyes volt a tipp?", value=bool(row['is_correct']))
            lesson = st.text_area("Tanulság (ha tévedett a rendszer):", value=row['lesson_learned'] if row['lesson_learned'] else "")
            
            if st.button("Frissítés és Tanulás"):
                db_manager.update_result(pred_id, new_result, is_correct, lesson)
                st.success("Adatbázis frissítve! A rendszer tanulni fog ebből.")
                st.rerun()
    else:
        st.info("Még nincs mentett elemzés.")
