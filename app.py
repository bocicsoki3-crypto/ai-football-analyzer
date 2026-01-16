import streamlit as st
import os
import pandas as pd
import re
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
        background: linear-gradient(180deg, #000000 0%, #1a1a1a 100%);
        color: #e0e0e0;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid rgba(255, 215, 0, 0.1);
    }
    
    /* Glassmorphism Cards/Expanders */
    div[data-testid="stExpander"] {
        background: rgba(20, 20, 20, 0.8);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 16px;
        border: 1px solid rgba(255, 215, 0, 0.2);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        margin-bottom: 15px;
        overflow: hidden;
    }
    
    /* Headers inside Expanders */
    .streamlit-expanderHeader {
        background-color: transparent !important;
        color: #FFD700 !important; /* Gold */
        font-weight: 600;
        text-shadow: 0 0 5px rgba(255, 215, 0, 0.3);
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #B8860B 0%, #FFD700 100%);
        color: #000000;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 800;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        text-transform: uppercase;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.2);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 20px rgba(255, 215, 0, 0.6);
        color: #000000;
    }
    
    /* Inputs & Selectboxes */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: rgba(30, 30, 30, 0.8);
        color: #FFD700;
        border-radius: 10px;
        border: 1px solid rgba(255, 215, 0, 0.2);
    }
    
    /* Typography - Golden Glow */
    h1, h2, h3 {
        color: #FFD700 !important;
        text-shadow: 0 0 10px rgba(255, 215, 0, 0.5), 0 0 20px rgba(255, 165, 0, 0.3);
        font-family: 'Arial', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Custom Match Button in Sidebar */
    .match-btn {
        width: 100%;
        text-align: left;
        margin: 5px 0;
    }
    
    /* Metric Cards */
    .metric-card {
        background: rgba(0, 0, 0, 0.6);
        border: 1px solid #FFD700;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #FFD700;
        text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
    }
    .metric-label {
        color: #aaa;
        font-size: 0.9rem;
        text-transform: uppercase;
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
def get_managers(version=5):
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
        
        # Group by Country
        countries = sorted(list(set([f['league']['country'] for f in fixtures])))
        
        st.markdown("### 🌍 Mérkőzések")
        for country in countries:
            country_fixtures = [f for f in fixtures if f['league']['country'] == country]
            
            # Expander for Country
            with st.expander(f"{country} ({len(country_fixtures)})"):
                # Group by League inside Country
                leagues = sorted(list(set([f['league']['name'] for f in country_fixtures])))
                
                for league in leagues:
                    st.markdown(f"**🏆 {league}**")
                    league_fixtures = [f for f in country_fixtures if f['league']['name'] == league]
                    
                    for f in league_fixtures:
                        try:
                            # Convert to CET (Europe/Budapest)
                            match_dt = pd.to_datetime(f['fixture']['date'])
                            if match_dt.tzinfo is None:
                                match_dt = match_dt.tz_localize('UTC')
                            match_dt_cet = match_dt.tz_convert('Europe/Budapest')
                            match_time_str = match_dt_cet.strftime('%Y.%m.%d. %H:%M')
                        except:
                            match_time_str = "??"
                        
                        # Button for each match
                        btn_label = f"⏰ {match_time_str} | {f['teams']['home']['name']} vs {f['teams']['away']['name']}"
                        if st.button(btn_label, key=f"btn_{f['fixture']['id']}", use_container_width=True):
                             st.session_state['current_match_obj'] = f
                             # Clear previous analysis if switching match
                             if 'analysis_results' in st.session_state:
                                 del st.session_state['analysis_results']
                             st.rerun()

import json

# Helper to clean JSON
def clean_json_string(s):
    # Remove markdown code blocks
    s = re.sub(r'```json\s*', '', s)
    s = re.sub(r'```\s*', '', s)
    # Find first { and last }
    start = s.find("{")
    end = s.rfind("}") + 1
    if start != -1 and end != -1:
        s = s[start:end]
    return s

# Main content
st.title("⚽ AI Committee Football Analyzer Pro")
st.markdown("---")

# Tabs
tab1, tab2, tab3 = st.tabs(["📅 Napi Elemzés", "📊 Részletes Adatok (Forrás)", "📚 Archívum/Tanulságok"])

with tab2:
    if 'current_match_obj' in st.session_state:
        match = st.session_state['current_match_obj']
        fixture_id = match['fixture']['id']
        home_id = match['teams']['home']['id']
        away_id = match['teams']['away']['id']
        league_id = match['league']['id']
        season = match['league']['season']
        
        st.header("🔍 Részletes Mérkőzés Adatok (Nyers Forrás)")
        
        # We need to fetch details if not already fetched, but usually we fetch on analyze.
        # Let's provide a button to view raw data even before analysis
        if st.button("📥 Nyers Adatok Betöltése Megtekintéshez"):
             with st.spinner("Adatok lekérése az API-ból..."):
                 raw_details = data_manager.get_match_details(fixture_id, home_id, away_id, league_id, season)
                 st.session_state['raw_match_details'] = raw_details
        
        if 'raw_match_details' in st.session_state:
            details = st.session_state['raw_match_details']
            
            # Create sub-tabs for data categories
            d_tab1, d_tab2, d_tab3, d_tab4, d_tab5 = st.tabs(["🏆 Tabella", "🚑 Sérültek", "⚔️ H2H", "📊 Csapat Statok", "🌐 Hírszerző Források"])
            
            with d_tab1:
                st.subheader("Bajnoki Tabella")
                st.dataframe(details.get('standings', []))
                
            with d_tab2:
                st.subheader("Sérültek és Eltiltottak")
                injuries = details.get('injuries', [])
                if injuries:
                    for inj in injuries:
                        st.write(f"🩹 {inj}")
                else:
                    st.info("Nincs jelentett sérült az adatbázisban.")
                    
            with d_tab3:
                st.subheader("Egymás Elleni Eredmények (H2H)")
                h2h = details.get('h2h', [])
                if h2h:
                    for h in h2h:
                        st.write(f"⚔️ {h}")
                else:
                    st.info("Nincs korábbi H2H adat.")
            
            with d_tab4:
                st.subheader("Csapat Statisztikák")
                col_h, col_a = st.columns(2)
                with col_h:
                    st.write(f"**{match['teams']['home']['name']}**")
                    st.json(details.get('home_team', {}))
                with col_a:
                    st.write(f"**{match['teams']['away']['name']}**")
                    st.json(details.get('away_team', {}))

            with d_tab5:
                st.subheader("🌐 Felhasznált Hírforrások (Tavily)")
                if 'analysis_results' in st.session_state:
                    scout_res = st.session_state['analysis_results']['scout']
                    # Try to extract sources from Scout report text if formatted
                    st.write(scout_res) 
                    st.info("A fenti szöveg a Hírszerző által talált és feldolgozott információkat tartalmazza.")
                else:
                    st.warning("Még nem futott le az elemzés, így nincs hírszerzési adat.")

    else:
        st.info("Válassz egy meccset a bal oldali menüből az adatok megtekintéséhez!")

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
            
            with st.status("🕵️ A Bizottság ülésezik...", expanded=True) as status:
                # 1. Gather detailed data
                st.write("📊 Adatok gyűjtése a mérkőzésről (Sérültek, H2H, Statisztikák)...")
                match_details = data_manager.get_match_details(fixture_id, home_id, away_id, league_id, season)
                # Store raw details for the other tab
                st.session_state['raw_match_details'] = match_details
                
                # Extract referee and venue if available
                referee = match['fixture'].get('referee', 'Ismeretlen')
                venue = match['fixture'].get('venue', {}).get('name', 'Ismeretlen')
                
                # 2. Get learned lessons
                st.write("🧠 Korábbi tapasztalatok betöltése...")
                lessons = db_manager.get_lessons()
                
                # 3. Run AI Committee Steps Manually for Progress
                # Statistician
                st.write("📈 A Statisztikus számolja az esélyeket (xG, Forma)...")
                stat_report = ai_committee.run_statistician(match_details)
                
                # Scout
                st.write("🔍 A Hírszerző elemzi a hiányzókat és a bírót...")
                # We extract injuries and h2h inside analyze_match now, but we pass referee/venue
                injuries = match_details.get('injuries', [])
                h2h = match_details.get('h2h', [])
                scout_report = ai_committee.run_scout(home_name, away_name, injuries, h2h, referee, venue)
                
                # Tactician
                st.write("♟️ A Taktikus vizsgálja a stílusokat...")
                tactician_report = ai_committee.run_tactician(match_details)
                
                # Prophet
                st.write("🔮 A Próféta megírja a forgatókönyvet...")
                prophet_report = ai_committee.run_prophet(match_details, home_name, away_name)
                
                # Boss
                st.write("👔 A Főnök meghozza a végső döntést...")
                boss_report = ai_committee.run_boss(stat_report, scout_report, tactician_report, match_details, lessons)
                
                results = {
                    "statistician": stat_report,
                    "scout": scout_report,
                    "tactician": tactician_report,
                    "prophet": prophet_report,
                    "boss": boss_report
                }
                
                status.update(label="Elemzés elkészült! 🚀", state="complete", expanded=False)
                
                st.session_state['analysis_results'] = results
                st.session_state['selected_match_data'] = match

        # Display Results
        if 'analysis_results' in st.session_state:
            results = st.session_state['analysis_results']
            
            st.markdown("---")
            
            # Extract Tips using Regex
            boss_text = results['boss']
            score_match = re.search(r'\*\*PONTOS VÉGEREDMÉNY TIPP\*\*:\s*(.*)', boss_text, re.IGNORECASE)
            value_match = re.search(r'\*\*VALUE TIPP\*\*:\s*(.*)', boss_text, re.IGNORECASE)
            
            score_tip = score_match.group(1).strip() if score_match else "Nincs adat"
            value_tip = value_match.group(1).strip() if value_match else "Nincs adat"
            
            # Display Big Metrics
            st.markdown("<h2 style='text-align: center;'>🏆 A Bizottság Döntése</h2>", unsafe_allow_html=True)
            
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.markdown(f"""
                <div style="background: rgba(0, 210, 255, 0.1); padding: 20px; border-radius: 15px; border: 1px solid rgba(0, 210, 255, 0.3); text-align: center;">
                    <h3 style="margin:0; color: #00d2ff;">PONTOS EREDMÉNY</h3>
                    <h1 style="margin:10px 0; font-size: 3rem;">{score_tip}</h1>
                </div>
                """, unsafe_allow_html=True)
            with m_col2:
                st.markdown(f"""
                <div style="background: rgba(255, 0, 100, 0.1); padding: 20px; border-radius: 15px; border: 1px solid rgba(255, 0, 100, 0.3); text-align: center;">
                    <h3 style="margin:0; color: #ff0064;">VALUE TIPP</h3>
                    <h2 style="margin:15px 0; font-size: 1.8rem;">{value_tip}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            # --- NEW METRICS SECTION ---
            st.markdown("---")
            st.markdown("<h3 style='text-align: center; color: #FFD700;'>⚡ KULCS MUTATÓK (STATISZTIKUS)</h3>", unsafe_allow_html=True)
            
            # Parse Statistician JSON
            stat_json = {}
            try:
                stat_content = results['statistician']
                if isinstance(stat_content, str):
                    cleaned = clean_json_string(stat_content)
                    stat_json = json.loads(cleaned)
                else:
                    stat_json = stat_content
            except Exception as e:
                # Fallback extraction with regex if JSON fails
                try:
                    stat_json['expected_corners'] = re.search(r'"expected_corners":\s*"([^"]+)"', stat_content).group(1)
                    stat_json['expected_cards'] = re.search(r'"expected_cards":\s*"([^"]+)"', stat_content).group(1)
                    stat_json['btts_percent'] = re.search(r'"btts_percent":\s*"([^"]+)"', stat_content).group(1)
                    stat_json['over_2_5_percent'] = re.search(r'"over_2_5_percent":\s*"([^"]+)"', stat_content).group(1)
                    stat_json['analysis'] = re.search(r'"analysis":\s*"([^"]+)"', stat_content).group(1)
                except:
                    pass
            
            # Clean up Boss output (Remove explanations)
            if score_tip and len(score_tip) > 20:
                # Try to extract just the score (e.g., 2-1)
                short_score = re.search(r'(\d+-\d+)', score_tip)
                if short_score:
                    score_tip = short_score.group(1)
            
            if value_tip and "MIVEL" in value_tip.upper():
                value_tip = value_tip.split("MIVEL")[0].strip()
                if value_tip.endswith(","):
                    value_tip = value_tip[:-1]
            if value_tip and "BECAUSE" in value_tip.upper():
                 value_tip = value_tip.split("BECAUSE")[0].strip()

            k_col1, k_col2, k_col3, k_col4 = st.columns(4)
            
            with k_col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">🚩 SZÖGLETEK</div>
                    <div class="metric-value">{stat_json.get('expected_corners', 'N/A')}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with k_col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">🟨 LAPOK</div>
                    <div class="metric-value">{stat_json.get('expected_cards', 'N/A')}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with k_col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">⚽ BTTS %</div>
                    <div class="metric-value">{stat_json.get('btts_percent', 'N/A')}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with k_col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">📈 OVER 2.5 %</div>
                    <div class="metric-value">{stat_json.get('over_2_5_percent', 'N/A')}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("📝 Részletes Jelentések")
            
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("📊 STATISZTIKUS JELENTÉSE (Groq)", expanded=True):
                    if stat_json:
                         # Beautiful Progress Bars for Win Probabilities
                         st.markdown("##### 🎲 Győzelmi Valószínűségek")
                         p_col1, p_col2, p_col3 = st.columns(3)
                         
                         # Helper to clean percent string
                         def clean_pct(val):
                             if not val or val == 'N/A': return 0
                             return int(re.sub(r'\D', '', str(val)))

                         h_val = clean_pct(stat_json.get('home_win_percent', '0'))
                         d_val = clean_pct(stat_json.get('draw_percent', '0'))
                         a_val = clean_pct(stat_json.get('away_win_percent', '0'))
                         
                         with p_col1:
                             st.write(f"🏠 Hazai: **{stat_json.get('home_win_percent', 'N/A')}**")
                             st.progress(min(h_val, 100) / 100)
                         with p_col2:
                             st.write(f"⚖️ Döntetlen: **{stat_json.get('draw_percent', 'N/A')}**")
                             st.progress(min(d_val, 100) / 100)
                         with p_col3:
                             st.write(f"✈️ Vendég: **{stat_json.get('away_win_percent', 'N/A')}**")
                             st.progress(min(a_val, 100) / 100)
                         
                         st.markdown("---")
                         st.markdown("##### 🧠 Elemzés")
                         st.info(stat_json.get('analysis', 'Nincs elérhető szöveges elemzés.'))
                    else:
                        st.error("Nem sikerült értelmezni a Statisztikus válaszát.")
                        st.code(results['statistician'])
                        
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


with tab3:
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
            
            col1, col2 = st.columns(2)
            with col1:
                new_result = st.text_input("Tényleges végeredmény:", value=row['actual_result'] if row['actual_result'] else "")
                is_correct = st.checkbox("Helyes volt a tipp?", value=bool(row['is_correct']))
                lesson = st.text_area("Tanulság (ha tévedett a rendszer):", value=row['lesson_learned'] if row['lesson_learned'] else "")
                
                if st.button("💾 Frissítés és Tanulás", type="primary"):
                    db_manager.update_result(pred_id, new_result, is_correct, lesson)
                    st.success("Adatbázis frissítve! A rendszer tanulni fog ebből.")
                    st.rerun()
            
            with col2:
                st.write("---")
                st.warning("⚠️ Veszélyes Zóna")
                if st.button("🗑️ Tipp Törlése Véglegesen", type="secondary"):
                    db_manager.delete_prediction(pred_id)
                    st.success("Tipp sikeresen törölve!")
                    st.rerun()
    else:
        st.info("Még nincs mentett elemzés.")
