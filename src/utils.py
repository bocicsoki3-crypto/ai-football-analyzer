import requests
import datetime
import os
import streamlit as st
import pypdf

@st.cache_data(ttl=3600) # Cache for 1 hour
def get_matches_by_date(league_name, date_str):
    """
    Fetches matches for a specific league and date using RapidAPI.
    Cached for 1 hour to prevent API quota exhaustion.
    """
    from src.config import LEAGUE_IDS # Import here to avoid circular dependency if any

    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return []

    league_id = LEAGUE_IDS.get(league_name)
    if not league_id:
        return []

    # Parse year from date string (YYYY-MM-DD)
    current_year = int(date_str[:4])

    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
    }

    # Try seasons: current year and previous year (to cover fall-spring seasons like 2024/2025)
    # If the match is in 2026, we check 2026 and 2025.
    seasons_to_check = [current_year, current_year - 1]
    
    all_matches = []
    
    for season in seasons_to_check:
        querystring = {
            "date": date_str,
            "league": str(league_id),
            "season": str(season)
        }

        try:
            response = requests.get(url, headers=headers, params=querystring)
            data = response.json()
            
            if "response" in data:
                for fixture in data["response"]:
                    match_info = {
                        "home": fixture["teams"]["home"]["name"],
                        "away": fixture["teams"]["away"]["name"],
                        "time": fixture["fixture"]["date"][11:16], # Extract HH:MM
                        "id": fixture["fixture"]["id"]
                    }
                    all_matches.append(match_info)
            
            # If we found matches in this season, we can likely stop (optimization)
            if all_matches:
                break
                
        except Exception as e:
            print(f"Error fetching matches for season {season}: {e}")
            continue

    return all_matches

def extract_text_from_pdf(uploaded_file):
    """
    Extracts text from a PDF file uploaded via Streamlit.
    """
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
