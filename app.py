import streamlit as st
import os
import pandas as pd
import re
import time
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
def get_managers(version=12):
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
        
        # --- League Priority Handling ---
        # Define priority leagues (Hungarian names might be needed depending on API, but using standard English/API names)
        # We will check partial matches for flexibility
        PRIORITY_LEAGUES = [
            "UEFA Champions League",
            "UEFA Europa League",
            "Premier League",
            "La Liga",
            "Bundesliga",
            "Serie A",
            "Ligue 1",
            "OTP Bank Liga", # Hungarian NB I
            "NB I",
            "Eredivisie",
            "Primeira Liga",
            "Championship"
        ]

        def get_league_priority(league_name):
            league_name_lower = league_name.lower()
            for i, p_league in enumerate(PRIORITY_LEAGUES):
                if p_league.lower() in league_name_lower:
                    return i
            return 999 # Non-priority leagues

        # Group by Country -> League
        country_map = {}
        for f in fixtures:
            l_name = f['league']['name']
            l_country = f['league']['country']
            
            if l_country not in country_map:
                country_map[l_country] = {}
            
            if l_name not in country_map[l_country]:
                country_map[l_country][l_name] = []
            
            country_map[l_country][l_name].append(f)
            
        # Sort Countries Alphabetically
        sorted_countries = sorted(country_map.keys())

        st.markdown("### 🌍 Bajnokságok")
        
        for country in sorted_countries:
            leagues_in_country = country_map[country]
            
            # Country Expander (Collapsed by default as requested)
            with st.expander(f"🏳️ {country}", expanded=False):
                
                # Sort Leagues within Country by Priority
                sorted_leagues = sorted(
                    leagues_in_country.keys(),
                    key=lambda l: (get_league_priority(l), l)
                )
                
                for l_name in sorted_leagues:
                    league_fixtures = leagues_in_country[l_name]
                    
                    # Nested Expander for League (Also Collapsed)
                    # Note: Streamlit doesn't support nested expanders perfectly in UI, 
                    # but we can use markdown headers or just list them.
                    # Since users want hierarchy: Country -> League -> Match
                    # Let's use a subheader or bold text for League inside Country Expander
                    
                    st.markdown(f"**🏆 {l_name}**")
                    
                    for f in league_fixtures:
                        try:
                            # Convert to CET (Europe/Budapest)
                            match_dt = pd.to_datetime(f['fixture']['date'])
                            if match_dt.tzinfo is None:
                                match_dt = match_dt.tz_localize('UTC')
                            match_dt_cet = match_dt.tz_convert('Europe/Budapest')
                            match_time_str = match_dt_cet.strftime('%H:%M') # Only time is enough inside list
                        except:
                            match_time_str = "??"
                        
                        # Button for each match
                        # home vs away (Time)
                        btn_label = f"{match_time_str} | {f['teams']['home']['name']} - {f['teams']['away']['name']}"
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
            d_tab1, d_tab2, d_tab3, d_tab4, d_tab5, d_tab6 = st.tabs(["🏆 Tabella", "🚑 Sérültek", "⚔️ H2H", "📊 Csapat Statok", "🌐 Hírszerző Források", "🛠️ Prompt Debug"])
            
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
                
                # Show computed stats if available
                if 'computed_stats' in details:
                    st.write("##### 🧮 Kiszámolt Átlagok (AI Bemenet)")
                    st.json(details['computed_stats'])
                    st.markdown("---")

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

            with d_tab6:
                st.subheader("🛠️ AI Prompt Log (Fejlesztői mód)")
                st.info("Itt láthatod, hogy pontosan milyen utasításokat kapott az AI. Ellenőrizd a bemeneti adatokat!")
                
                prompts = ai_committee.get_last_prompts()
                if prompts:
                    for agent, prompt in prompts.items():
                        with st.expander(f"📝 {agent.upper()} Prompt", expanded=False):
                            st.code(prompt, language="markdown")
                else:
                    st.warning("Még nincs rögzített prompt. Futtass egy elemzést!")


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
            try:
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
                    stat_report = ai_committee.run_statistician(home_name, away_name)
                    time.sleep(2) # Delay to avoid rate limits
                    
                    # Scout
                    st.write("🔍 A Hírszerző elemzi a hiányzókat és a bírót...")
                    # We extract injuries and h2h inside analyze_match now, but we pass referee/venue
                    injuries = match_details.get('injuries', [])
                    h2h = match_details.get('h2h', [])
                    match_date = match['fixture']['date'].split('T')[0]
                    scout_report = ai_committee.run_scout(home_name, away_name, injuries, h2h, referee, venue, match_date)
                    time.sleep(2) # Delay to avoid rate limits
                    
                    # Tactician
                    st.write("♟️ A Taktikus vizsgálja a stílusokat...")
                    tactician_report = ai_committee.run_tactician(home_name, away_name)
                    time.sleep(2) # Delay to avoid rate limits
                    
                    # Prophet
                    st.write("🔮 A Próféta megírja a forgatókönyvet...")
                    prophet_report = ai_committee.run_prophet(stat_report, scout_report, tactician_report, match_details)
                    time.sleep(2) # Delay to avoid rate limits
                    
                    # Boss
                    st.write("👔 A Főnök meghozza a végső döntést...")
                    boss_report = ai_committee.run_boss(stat_report, scout_report, tactician_report, match_details, lessons, prophet_report)
                    
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
            except Exception as e:
                st.error(f"❌ Hiba történt az elemzés során: {str(e)}")
                print(f"ERROR DETAILS: {e}")

        # Display Results
        if 'analysis_results' in st.session_state:
            results = st.session_state['analysis_results']
            
            st.markdown("---")
            
            # Extract Tips (Support for both Dictionary and Legacy String)
            boss_data = results['boss']
            
            if isinstance(boss_data, dict):
                # New GPT-4o JSON format
                score_tip = boss_data.get("score_prediction", "Nincs adat")
                main_tip = boss_data.get("main_tip", "Nincs adat")
                value_tip = boss_data.get("value_tip", "Nincs adat")
            else:
                # Legacy String format with Regex
                boss_text = str(boss_data)
                score_match = re.search(r'\*\*PONTOS VÉGEREDMÉNY TIPP\*\*:\s*(.*)', boss_text, re.IGNORECASE)
                main_match = re.search(r'\*\*FŐ TIPP\*\*:\s*(.*)', boss_text, re.IGNORECASE)
                value_match = re.search(r'\*\*VALUE TIPP\*\*:\s*(.*)', boss_text, re.IGNORECASE)
                
                score_tip = score_match.group(1).strip() if score_match else "Nincs adat"
                main_tip = main_match.group(1).strip() if main_match else "Nincs adat"
                value_tip = value_match.group(1).strip() if value_match else "Nincs adat"
            
            # Display Big Metrics
            st.markdown("<h2 style='text-align: center;'>🏆 A Bizottság Döntése</h2>", unsafe_allow_html=True)
            
            m_col1, m_col2, m_col3 = st.columns(3)
            
            with m_col1:
                st.markdown(f"""
                <div style="background: rgba(0, 210, 255, 0.1); padding: 15px; border-radius: 15px; border: 1px solid rgba(0, 210, 255, 0.3); text-align: center; height: 100%;">
                    <h4 style="margin:0; color: #00d2ff;">PONTOS EREDMÉNY</h4>
                    <h2 style="margin:10px 0;">{score_tip}</h2>
                </div>
                """, unsafe_allow_html=True)

            with m_col2:
                st.markdown(f"""
                <div style="background: rgba(255, 215, 0, 0.1); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 215, 0, 0.3); text-align: center; height: 100%;">
                    <h4 style="margin:0; color: #FFD700;">FŐ TIPP (BIZTONSÁGI)</h4>
                    <h2 style="margin:10px 0;">{main_tip}</h2>
                </div>
                """, unsafe_allow_html=True)

            with m_col3:
                st.markdown(f"""
                <div style="background: rgba(255, 0, 100, 0.1); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 0, 100, 0.3); text-align: center; height: 100%;">
                    <h4 style="margin:0; color: #ff0064;">VALUE TIPP</h4>
                    <h2 style="margin:10px 0;">{value_tip}</h2>
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
                         
                         # Helper to clean percent string (Fixed for decimals)
                         def clean_pct(val):
                             if not val or val == 'N/A': return 0
                             # Extract number including decimals
                             match = re.search(r'(\d+(\.\d+)?)', str(val))
                             if match:
                                 return float(match.group(1))
                             return 0

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
                        
                with st.expander("🕵️ HÍRSZERZŐ JELENTÉSE (Tavily Nyers Adat)", expanded=False):
                    st.markdown("""
                    <style>
                    .scout-report {
                        background-color: #262730;
                        padding: 15px;
                        border-radius: 5px;
                        border-left: 4px solid #ff4b4b;
                        font-size: 0.85rem;
                        white-space: pre-wrap;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    st.markdown(f'<div class="scout-report">{results["scout"]}</div>', unsafe_allow_html=True)
            with col2:
                with st.expander("🧠 TAKTIKUS JELENTÉSE (Groq)", expanded=True):
                    st.write(results['tactician'])
                
                with st.expander("🔮 A PRÓFÉTA JÖVENDÖLÉSE (GPT-4o)", expanded=True):
                    prophet_res = results.get('prophet', {})
                    if isinstance(prophet_res, dict):
                        # Structured Display
                        p_col1, p_col2 = st.columns(2)
                        with p_col1:
                            st.metric("🔮 Ajánlás", prophet_res.get('recommendation', 'N/A'))
                        with p_col2:
                            st.metric("📊 Odds", prophet_res.get('estimated_odds', 'N/A'), delta=prophet_res.get('confidence', ''))
                        
                        st.markdown("##### 📜 Indoklás")
                        st.info(prophet_res.get('analysis', 'Nincs elemzés.'))
                    else:
                        st.write(prophet_res)

                with st.expander("👔 A FŐNÖK DÖNTÉSE (GPT-4o)", expanded=True):
                    boss_res = results['boss']
                    if isinstance(boss_res, dict):
                        # Structured Display
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            st.metric("🎯 Fő Tipp", boss_res.get('main_tip', 'N/A'), delta=boss_res.get('main_tip_confidence', ''))
                        with b_col2:
                            st.metric("⚽ Pontos Eredmény", boss_res.get('score_prediction', 'N/A'))
                        
                        st.markdown("##### 💎 Value Tipp")
                        st.write(f"**{boss_res.get('value_tip', 'N/A')}** (@ {boss_res.get('value_tip_odds', 'N/A')})")
                        
                        st.markdown("##### 📝 Elemzés")
                        st.info(boss_res.get('analysis', 'Nincs szöveges elemzés.'))
                        
                        # Extra stats if available
                        extra_stats = []
                        if 'btts_percent' in boss_res: extra_stats.append(f"BTTS: {boss_res['btts_percent']}")
                        if 'over_2_5_percent' in boss_res: extra_stats.append(f"Over 2.5: {boss_res['over_2_5_percent']}")
                        if extra_stats:
                            st.caption(" | ".join(extra_stats))
                    else:
                        # Fallback for old string format
                        st.markdown(boss_res)
            
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
    st.header("📚 Archívum és Tanulságok")
    
    predictions = db_manager.get_all_predictions()
    if predictions:
        df = pd.DataFrame(predictions)
        
        # --- Custom Table Header ---
        h1, h2, h3, h4, h5, h6, h7 = st.columns([0.5, 1.5, 3, 2, 1, 1, 1])
        h1.markdown("**ID**")
        h2.markdown("**Dátum**")
        h3.markdown("**Meccs**")
        h4.markdown("**Tipp**")
        h5.markdown("**Eredmény**")
        h6.markdown("**Status**")
        h7.markdown("**Nézet**")
        st.markdown("---")

        for index, row in df.iterrows():
            c1, c2, c3, c4, c5, c6, c7 = st.columns([0.5, 1.5, 3, 2, 1, 1, 1])
            
            # ID
            c1.write(f"#{row['id']}")
            
            # Date
            c2.write(row['date'])
            
            # Match
            c3.write(f"{row['home_team']} - {row['away_team']}")
            
            # Tip Extraction (Simplified for display)
            tip_text = "Megnyitás..."
            pred_res = row['predicted_result']
            if pred_res:
                try:
                    # Try parsing as JSON first (for new format)
                    if isinstance(pred_res, str) and (pred_res.strip().startswith('{') or pred_res.strip().startswith('"')):
                         pred_json = json.loads(pred_res)
                         if isinstance(pred_json, dict):
                            tip_text = pred_json.get("score_prediction", "Nincs adat")
                         else:
                            tip_text = str(pred_json)[:20]
                    else:
                         raise ValueError("Not JSON")
                except:
                    # Fallback to Regex
                    score_match = re.search(r'\*\*PONTOS VÉGEREDMÉNY TIPP\*\*:\s*(.*)', str(pred_res), re.IGNORECASE)
                    if score_match:
                        tip_text = score_match.group(1).strip()
                    else:
                        tip_text = str(pred_res)[:20] + "..."
            
            c4.write(tip_text)
            
            # Actual Result
            c5.write(row['actual_result'] if row['actual_result'] else "-")
            
            # Status (Color coded)
            is_correct = row['is_correct']
            if is_correct == 1:
                status_html = "<span style='color:#00FF00; font-weight:bold;'>✅ NYERT</span>"
            elif is_correct == 0:
                status_html = "<span style='color:#FF0000; font-weight:bold;'>❌ VESZTETT</span>"
            else:
                status_html = "<span style='color:grey;'>❓ FÜGGŐBEN</span>"
            c6.markdown(status_html, unsafe_allow_html=True)
            
            # Magnifying Glass Button
            if c7.button("📄", key=f"btn_arch_{row['id']}"):
                st.session_state['selected_archive_id'] = row['id']
                st.rerun()
            
            st.markdown("<hr style='margin: 5px 0; opacity: 0.2;'>", unsafe_allow_html=True)

        # --- Detailed View Section ---
        if 'selected_archive_id' in st.session_state:
            sel_id = st.session_state['selected_archive_id']
            # Find the row in current dataframe
            selected_row = df[df['id'] == sel_id]
            
            if not selected_row.empty:
                row = selected_row.iloc[0]
                
                st.markdown("---")
                st.subheader(f"🔍 Elemzés Részletei (ID: {sel_id})")
                
                # Auto-expand the details
                with st.expander(f"📄 {row['home_team']} vs {row['away_team']} - Részletes Jegyzőkönyv", expanded=True):
                    
                    # 1. Parse full analysis JSON
                    full_analysis = {}
                    try:
                        if row['full_analysis']:
                            full_analysis = json.loads(row['full_analysis'])
                    except Exception as e:
                        st.error(f"Hiba a JSON betöltésekor: {e}")
                    
                    # 2. Display Tabs
                    at1, at2, at3, at4 = st.tabs(["📊 Statisztikus", "🕵️ Hírszerző", "🧠 Taktikus & Próféta", "👔 Főnök"])
                    
                    with at1:
                        st.markdown(full_analysis.get('statistician', 'Nincs adat'))
                    with at2:
                        st.markdown(full_analysis.get('scout', 'Nincs adat'))
                    with at3:
                        st.markdown("### Taktikus")
                        st.markdown(full_analysis.get('tactician', 'Nincs adat'))
                        st.markdown("---")
                        st.markdown("### Próféta")
                        
                        prophet_res = full_analysis.get('prophet', 'Nincs adat')
                        if isinstance(prophet_res, dict):
                             # Structured Display for Archive
                             ap_col1, ap_col2 = st.columns(2)
                             with ap_col1:
                                 st.metric("🔮 Ajánlás", prophet_res.get('recommendation', 'N/A'))
                             with ap_col2:
                                 st.metric("📊 Odds", prophet_res.get('estimated_odds', 'N/A'), delta=prophet_res.get('confidence', ''))
                             
                             st.markdown("**Indoklás:**")
                             st.info(prophet_res.get('analysis', 'Nincs elemzés.'))
                        else:
                             st.markdown(prophet_res)
                    with at4:
                        boss_content = full_analysis.get('boss', 'Nincs adat')
                        if isinstance(boss_content, dict):
                            st.json(boss_content)
                            if 'analysis' in boss_content:
                                st.markdown("### 📝 Szöveges Elemzés")
                                st.write(boss_content['analysis'])
                        else:
                            st.markdown(boss_content)

                # 3. Edit/Update Section
                st.markdown("### ✍️ Eredmény Adminisztráció")
                
                # Use a form to avoid instant rerun issues during editing
                with st.form(key=f"edit_form_{sel_id}"):
                    c_edit1, c_edit2 = st.columns(2)
                    with c_edit1:
                        new_res = st.text_input("Végeredmény:", value=row['actual_result'] if row['actual_result'] else "")
                        is_corr = st.checkbox("Helyes volt a tipp?", value=bool(row['is_correct']))
                        less = st.text_area("Tanulság (ha tévedett):", value=row['lesson_learned'] if row['lesson_learned'] else "")
                    
                    with c_edit2:
                        st.info("Itt tudod utólag rögzíteni az eredményt, hogy az AI tanulhasson belőle.")
                    
                    col_save, col_del = st.columns([1, 1])
                    with col_save:
                        submit_save = st.form_submit_button("💾 Mentés és Tanulás")
                    with col_del:
                        # Delete is risky, maybe keep it outside form or use a separate button?
                        # Inside form is fine, but needs logic check.
                        pass
                
                if submit_save:
                    db_manager.update_result(int(sel_id), new_res, is_corr, less)
                    st.success("Sikeresen frissítve!")
                    st.rerun()

                # Separate Delete Button (Safety)
                st.markdown("---")
                if st.button("🗑️ Bejegyzés Törlése", key=f"del_{sel_id}", type="primary"):
                     db_manager.delete_prediction(int(sel_id))
                     del st.session_state['selected_archive_id']
                     st.warning("Törölve.")
                     st.rerun()

    else:
        st.info("Még nincs mentett elemzés az adatbázisban.")
