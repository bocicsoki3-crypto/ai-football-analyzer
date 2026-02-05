import streamlit as st
import os
import datetime
import random
from dotenv import load_dotenv
from src.config import LEAGUE_IDS, LEAGUE_EMOJIS
from src.utils import get_active_leagues_and_matches, extract_text_from_pdf, get_detailed_stats
from src.analyzer import analyze_match_with_gpt4
from src.storage import save_tip, load_tips, update_tip_status, delete_tip

# Load environment variables
load_dotenv()

# Page Config
st.set_page_config(page_title="AI Football Analyst", page_icon="⚽", layout="wide")

# --- FIREFLY ANIMATION GENERATOR ---
firefly_html = ""
for i in range(30):
    left = random.randint(0, 100)
    top = random.randint(0, 100)
    delay = random.uniform(0, 20)
    duration = random.uniform(10, 20)
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
    def password_entered():
        if st.session_state["password"] == os.getenv("SITE_PASSWORD", "admin123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Kérlek add meg a jelszót:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Kérlek add meg a jelszót:", type="password", on_change=password_entered, key="password")
        st.error("😕 Helytelen jelszó")
        return False
    else:
        return True

if not check_password():
    st.stop()

# Custom CSS
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    html, body, [class*="css"] {{ font-family: 'Poppins', sans-serif; }}
    .stApp {{ background: linear-gradient(to bottom, #0f0c29, #302b63, #24243e); color: #fff; }}
    .firefly {{
        position: fixed; width: 6px; height: 6px; background: rgba(255, 255, 255, 0.5);
        border-radius: 50%; box-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 0 0 20px rgba(255, 255, 255, 0.4);
        pointer-events: none; z-index: 0; animation: float-firefly 15s infinite alternate ease-in-out;
    }}
    @keyframes float-firefly {{
        0% {{ transform: translate(0, 0); opacity: 0.2; }}
        50% {{ opacity: 1; }}
        100% {{ transform: translate(var(--move-x, 30px), var(--move-y, -30px)); opacity: 0.2; }}
    }}
    .stButton>button {{
        width: 100%; border-radius: 8px; min-height: 50px;
        background: linear-gradient(90deg, #2E86C1 0%, #1B4F72 100%); color: white; border: none;
    }}
    .prediction-card {{
        background: rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;
        margin-bottom: 16px; border-left: 5px solid #3a7bd5; backdrop-filter: blur(10px);
    }}
    </style>
    {firefly_html}
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("📱 Menü")
page = st.sidebar.radio("Válassz oldalt:", ["Elemző", "Tipptörténet"])

# --- PAGE: ELEMZŐ ---
if page == "Elemző":
    st.sidebar.title("📌 Bajnokságok")
    if 'selected_match' not in st.session_state:
        st.session_state.selected_match = None

    selected_date = st.sidebar.date_input("Dátum választás", datetime.date.today())
    date_str = selected_date.strftime("%Y-%m-%d")

    with st.spinner("Meccsek betöltése..."):
        organized_matches = get_active_leagues_and_matches(date_str)

    if organized_matches:
        active_leagues = sorted(list(organized_matches.keys()))
        selected_league = st.sidebar.selectbox("Válassz bajnokságot:", active_leagues)
        
        if selected_league:
            st.sidebar.markdown(f"**{LEAGUE_EMOJIS.get(selected_league, '⚽')} {selected_league}**")
            for match in organized_matches[selected_league]:
                btn_label = f"{match['home']} vs {match['away']}\n({match['date']} {match['time']})"
                if st.sidebar.button(btn_label, key=match['id'], use_container_width=True):
                    st.session_state.selected_match = match
                    st.session_state.analysis_result = None # Reset analysis on new match
    else:
        st.sidebar.info("Nincs meccs a követett ligákban.")

    st.title("🤖 GPT-4o Foci Elemző v3.0 (MENTÉS AKTÍV) ✅")

    if st.session_state.selected_match:
        match = st.session_state.selected_match
        st.header(f"Mérkőzés: {match['home']} vs {match['away']}")
        
        # Analysis Form
        with st.form("analysis_form"):
            uploaded_files = st.file_uploader("Statisztikák Feltöltése (PDF)", type="pdf", accept_multiple_files=True)
            submitted = st.form_submit_button("Elemzés Indítása 🚀")
        
        if submitted and uploaded_files:
            with st.spinner("Adatok kinyerése és elemzés..."):
                pdf_text = ""
                for uploaded_file in uploaded_files:
                    text = extract_text_from_pdf(uploaded_file)
                    pdf_text += f"\n--- FILE: {uploaded_file.name} ---\n{text}\n"
                
                match_name = f"{match['home']} vs {match['away']}"
                st.session_state.analysis_result = analyze_match_with_gpt4(pdf_text, match_name)
        elif submitted and not uploaded_files:
            st.warning("⚠️ Tölts fel legalább egy PDF-et!")

        # Display Results & Save Interface
        if st.session_state.get('analysis_result'):
            res = st.session_state.analysis_result
            if "error" in res:
                st.error(res["error"])
            else:
                st.success("Elemzés kész! 📊")
                
                # Display Summary
                summary = res.get("summary", "Nincs elérhető összefoglaló.")
                st.info(f"**📝 Elemzés Összefoglaló:**\n\n{summary}")
                
                predictions = res.get("predictions", [])
                
                # We wrap the checkboxes in a form to allow batch saving
                st.subheader("🏆 AI Tippek (Válaszd ki a mentendőket):")
                with st.form("save_tips_form"):
                    
                    selected_tips = []
                    for idx, pred in enumerate(predictions):
                        confidence = pred.get("confidence", 0)
                        market = pred.get("market", "N/A")
                        pick = pred.get("prediction", "N/A")
                        reasoning = pred.get("reasoning", "")
                        
                        # Color logic
                        color = "#4CAF50" if confidence >= 80 else "#FFC107" if confidence >= 60 else "#FF5722"
                        
                        # Custom HTML Card
                        st.markdown(f"""
                        <div class="prediction-card" style="border-left: 5px solid {color};">
                            <h3 style="margin:0; color: white;">{market}: <span style="color:{color}">{pick}</span></h3>
                            <p style="color: #ccc; font-size: 0.9em;">Magabiztosság: {confidence}%</p>
                            <p style="font-style: italic; font-size: 0.9em;">{reasoning}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Checkbox for selection
                        if st.checkbox(f"Mentés: {market} - {pick}", key=f"check_{idx}"):
                            # Construct tip object to save
                            tip_to_save = {
                                "match": f"{match['home']} vs {match['away']}",
                                "date": match['date'],
                                "market": market,
                                "prediction": pick,
                                "confidence": confidence,
                                "reasoning": reasoning,
                                "summary": summary # Save the general analysis summary
                            }
                            selected_tips.append(tip_to_save)
                    
                    save_submitted = st.form_submit_button("💾 Kijelölt Tippek Mentése")
                    
                    if save_submitted:
                        if selected_tips:
                            save_tip(selected_tips)
                            st.success(f"{len(selected_tips)} tipp sikeresen mentve a Tipptörténetbe! ✅")
                        else:
                            st.warning("Nem jelöltél ki egy tippet sem.")

    else:
        st.info("👈 Válassz meccset a menüből!")

# --- PAGE: TIPPTÖRTÉNET ---
elif page == "Tipptörténet":
    st.title("📜 Tipptörténet és Tanulás")
    
    tips = load_tips()
    
    if not tips:
        st.info("Még nincsenek mentett tippek.")
    else:
        # Sort by status (Pending first) then date
        tips.sort(key=lambda x: (x.get("status") != "pending", x.get("date"), x.get("match")))
        
        for tip in tips:
            # Card style
            status = tip.get("status", "pending")
            status_color = "#3a7bd5" # Default Blue
            if status == "won": status_color = "#4CAF50" # Green
            if status == "lost": status_color = "#FF5722" # Red
            
            with st.container():
                st.markdown(f"""
                <div class="prediction-card" style="border-left: 5px solid {status_color};">
                    <div style="display:flex; justify-content:space-between;">
                        <h3>{tip['match']} <span style="font-size:0.6em; color:#aaa;">({tip['date']})</span></h3>
                        <span style="background:{status_color}; padding: 2px 8px; border-radius:4px; font-size:0.8em;">{status.upper()}</span>
                    </div>
                    <h4>{tip['market']}: <span style="color:{status_color}">{tip['prediction']}</span></h4>
                    <p><i>{tip['reasoning']}</i></p>
                </div>
                """, unsafe_allow_html=True)
                
                # Show summary if available
                if "summary" in tip and tip["summary"]:
                    with st.expander("📄 Részletes Meccselemzés (Historikus Adat)"):
                         st.write(tip["summary"])
                
                # Action Buttons (only if pending)
                if status == "pending":
                    c1, c2, c3 = st.columns([1, 1, 4])
                    with c1:
                        if st.button("✅ Nyert", key=f"won_{tip['id']}"):
                            update_tip_status(tip['id'], "won")
                            st.rerun()
                    with c2:
                        if st.button("❌ Vesztett", key=f"lost_{tip['id']}"):
                            update_tip_status(tip['id'], "lost")
                            # Future: Trigger Learning here
                            st.rerun()
                elif status != "pending":
                    if st.button("🗑️ Törlés", key=f"del_{tip['id']}"):
                         delete_tip(tip['id'])
                         st.rerun()
