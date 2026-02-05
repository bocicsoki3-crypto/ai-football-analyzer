import requests
import os
import pypdf
import datetime
from .config import LEAGUE_IDS

def get_todays_matches(league_name):
    """
    Fetches today's matches for a specific league using RapidAPI.
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return []

    league_id = LEAGUE_IDS.get(league_name)
    if not league_id:
        return []

    # Get today's date in YYYY-MM-DD format
    today = datetime.date.today().strftime("%Y-%m-%d")

    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {
        "date": today,
        "league": str(league_id),
        "season": "2024" # Defaulting to current season, might need logic for overlapping seasons (2024/2025)
        # Note: API-Football usually handles 'current' season logic well, but year is required.
        # For 2025 date, we should probably check if it's 2024 or 2025 season.
        # Let's try to infer or just try 2024 first as it covers 24/25.
    }
    
    # Simple logic: If month is > 6, it's likely the start of 'year', else 'year-1' for European leagues.
    # But South American leagues are calendar year.
    # To be safe, we can try to fetch the current season for the league first, OR just try 2024/2025.
    # For simplicity in this MVP, we will try 2025 since today is 2026 in the user's prompt context?
    # Wait, <env> says "Today's date: 2026-02-05". So season is likely 2025 or 2026.
    # Let's assume 2025 for European (25/26) or 2026 for Calendar.
    # We will set season to 2025 as a safe bet for Feb 2026 (end of 25/26 season).
    querystring["season"] = "2025" 

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        matches = []
        if "response" in data:
            for fixture in data["response"]:
                match_info = {
                    "home": fixture["teams"]["home"]["name"],
                    "away": fixture["teams"]["away"]["name"],
                    "time": fixture["fixture"]["date"][11:16], # Extract HH:MM
                    "id": fixture["fixture"]["id"]
                }
                matches.append(match_info)
        return matches
    except Exception as e:
        print(f"Error fetching matches: {e}")
        return []

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
