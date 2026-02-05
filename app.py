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

# Custom CSS for dark mode and styling
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #2E86C1;
        color: white;
    }
    .stButton>button:hover {
        background-color: #1B4F72;
    }
    .league-header {
        font-size: 18px;
        font-weight: bold;
        margin-top: 10px;
        cursor: pointer;
    }
    .match-card {
        padding: 10px;
        border: 1px solid #444;
        border-radius: 5px;
        margin-bottom: 5px;
        background-color: #222;
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
                
                # 2. Get Official Stats (RapidAPI)
                # Ensure we have IDs (backward compatibility check)
                h_id = match.get('home_id')
                a_id = match.get('away_id')
                
                if h_id and a_id:
                    rapid_stats = get_detailed_stats(h_id, a_id)
                else:
                    rapid_stats = "Official Stats Unavailable (Missing Team IDs)"

                # 3. Analyze with AI
                match_name = f"{match['home']} vs {match['away']}"
                analysis_result = analyze_match_with_gpt4(pdf_text, match_name, rapid_stats)
                
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
