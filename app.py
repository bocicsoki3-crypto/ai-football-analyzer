import streamlit as st
import os
from dotenv import load_dotenv
from src.config import LEAGUE_IDS, LEAGUE_EMOJIS
from src.utils import get_todays_matches, extract_text_from_pdf
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

# Sidebar - Pinned Leagues
st.sidebar.title("📌 Pinned Leagues")

# Session state to track selected match
if 'selected_match' not in st.session_state:
    st.session_state.selected_match = None

# Sidebar Logic
for league_name in LEAGUE_IDS.keys():
    # Expander for each league (closed by default)
    with st.sidebar.expander(f"{LEAGUE_EMOJIS.get(league_name, '⚽')} {league_name}", expanded=False):
        # Fetch matches only when expanded (lazy loading could be better, but Streamlit reruns on expand)
        # To avoid API spam, we might want to cache this or just load.
        # For this version, we call the function.
        matches = get_todays_matches(league_name)
        
        if matches:
            for match in matches:
                btn_label = f"{match['home']} vs {match['away']} ({match['time']})"
                if st.button(btn_label, key=match['id']):
                    st.session_state.selected_match = match
        else:
            st.write("No matches today.")

# Main Content
st.title("🤖 GPT-4o Football Analyst")

if st.session_state.selected_match:
    match = st.session_state.selected_match
    st.header(f"Match Analysis: {match['home']} vs {match['away']}")
    
    # PDF Upload
    uploaded_file = st.file_uploader("Upload Match Stats (PDF)", type="pdf")
    
    if uploaded_file is not None:
        if st.button("Analyze Match 🚀"):
            with st.spinner("Extracting data and crunching numbers with GPT-4o..."):
                # 1. Extract Text
                pdf_text = extract_text_from_pdf(uploaded_file)
                
                # 2. Analyze with AI
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
