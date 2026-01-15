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

# Sidebar for API Keys
with st.sidebar:
    st.header("🔑 API Kulcsok")
    
    # Check if keys are already in env (e.g. from secrets or previous input)
    default_rapid = os.environ.get("RAPIDAPI_KEY", "")
    default_groq = os.environ.get("GROQ_API_KEY", "")

    rapidapi_key = st.text_input("RapidAPI Key", value=default_rapid, type="password")
    groq_key = st.text_input("Groq Cloud API Key", value=default_groq, type="password")
    
    if st.button("Mentés"):
        os.environ["RAPIDAPI_KEY"] = rapidapi_key
        os.environ["GROQ_API_KEY"] = groq_key
        st.success("Kulcsok mentve a munkamenetre!")
        st.rerun()

# Main content
st.title("⚽ AI Committee Football Analyzer Pro")
st.markdown("---")

# Tabs
tab1, tab2 = st.tabs(["📅 Napi Elemzés", "📚 Archívum/Tanulságok"])

with tab1:
    st.header("Mai Mérkőzések Elemzése")
    
    if not os.environ.get("RAPIDAPI_KEY"):
        st.warning("Kérlek add meg a RapidAPI kulcsot a bal oldali sávban!")
    else:
        if st.button("Mai meccsek betöltése"):
            with st.spinner("Meccsek letöltése..."):
                fixtures = data_manager.get_todays_fixtures()
                if isinstance(fixtures, list) and fixtures:
                    st.session_state['fixtures'] = fixtures
                    st.success(f"{len(fixtures)} mérkőzés található mára.")
                elif isinstance(fixtures, dict) and "error" in fixtures:
                    st.error(f"Hiba: {fixtures['error']}")
                else:
                    st.info("Nincs mai mérkőzés vagy hiba történt.")

        if 'fixtures' in st.session_state:
            fixtures = st.session_state['fixtures']
            
            # Ligák kinyerése és rendezése
            leagues = sorted(list(set([f['league']['name'] for f in fixtures])))
            selected_league = st.selectbox("1. Válassz bajnokságot:", leagues)
            
            # Meccsek szűrése a kiválasztott ligára
            league_fixtures = [f for f in fixtures if f['league']['name'] == selected_league]
            
            # Meccs opciók összeállítása időponttal
            match_options = {}
            for f in league_fixtures:
                try:
                    # Időpont konvertálása és formázása (HH:MM)
                    match_time = pd.to_datetime(f['fixture']['date']).strftime('%H:%M')
                except:
                    match_time = "??:??"
                
                match_label = f"⏰ {match_time} | {f['teams']['home']['name']} vs {f['teams']['away']['name']}"
                match_options[match_label] = f
                
            selected_match_name = st.selectbox("2. Válassz mérkőzést:", list(match_options.keys()))
            
            if st.button("ELEMZÉS INDÍTÁSA"):
                selected_match = match_options[selected_match_name]
                fixture_id = selected_match['fixture']['id']
                home_id = selected_match['teams']['home']['id']
                away_id = selected_match['teams']['away']['id']
                league_id = selected_match['league']['id']
                season = selected_match['league']['season']
                
                with st.spinner("Adatok gyűjtése és Bizottság összehívása..."):
                    # 1. Gather detailed data
                    match_details = data_manager.get_match_details(fixture_id, home_id, away_id, league_id, season)
                    
                    # 2. Get learned lessons
                    lessons = db_manager.get_lessons()
                    
                    # 3. Run AI Committee
                    results = ai_committee.analyze_match(match_details, selected_match['teams']['home']['name'], selected_match['teams']['away']['name'], lessons)
                    
                    st.session_state['analysis_results'] = results
                    st.session_state['current_match'] = selected_match_name
                    st.session_state['selected_match_data'] = selected_match # Store full match data for saving

            if 'analysis_results' in st.session_state:
                results = st.session_state['analysis_results']
                
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
                
                # Save to DB automatically if not already saved (simple check could be added, but for now we just save)
                if st.button("Eredmény mentése az Archívumba"):
                    # Use stored match data if available, otherwise fallback (safer)
                    if 'selected_match_data' in st.session_state:
                         home_team = st.session_state['selected_match_data']['teams']['home']['name']
                         away_team = st.session_state['selected_match_data']['teams']['away']['name']
                    else:
                         # Fallback parsing if state was lost (less reliable with new format)
                         home_team = "Ismeretlen Hazai" 
                         away_team = "Ismeretlen Vendég"

                    db_manager.save_prediction(
                        home_team, 
                        away_team, 
                        results, 
                        results['boss']
                    )
                    st.success("Mentve az adatbázisba!")

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
