import requests
import datetime
import os
import streamlit as st
import pypdf

@st.cache_data(ttl=3600) # Cache for 1 hour
def get_active_leagues_and_matches(date_str):
    """
    Fetches ALL matches for a specific date globally, then filters them
    to keep only the leagues we track (defined in LEAGUE_IDS).
    Returns a dictionary: { "Premier League (ENG)": [match_list], ... }
    """
    from src.config import LEAGUE_IDS # Import here

    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return {}

    # Create a reverse mapping: ID -> Name
    # We use this to quickly identify if a match belongs to a league we care about.
    id_to_league_name = {v: k for k, v in LEAGUE_IDS.items()}

    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
    }
    
    # Fetch ALL matches for this date
    querystring = {"date": date_str, "timezone": "Europe/Budapest"} # Optional: set timezone to local

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        organized_matches = {}

        if "response" in data:
            for fixture in data["response"]:
                league_id = fixture["fixture"]["venue"].get("id") # Warning: venue id is not league id
                # Correct path for league id: fixture['league']['id']
                league_id = fixture["league"]["id"]
                
                # Check if this league is in our tracked list
                if league_id in id_to_league_name:
                    league_name = id_to_league_name[league_id]
                    
                    match_info = {
                        "home": fixture["teams"]["home"]["name"],
                        "away": fixture["teams"]["away"]["name"],
                        "home_id": fixture["teams"]["home"]["id"],
                        "away_id": fixture["teams"]["away"]["id"],
                        "time": fixture["fixture"]["date"][11:16], # Extract HH:MM
                        "date": fixture["fixture"]["date"][:10],   # Extract YYYY-MM-DD
                        "id": fixture["fixture"]["id"]
                    }
                    
                    if league_name not in organized_matches:
                        organized_matches[league_name] = []
                    
                    organized_matches[league_name].append(match_info)
        
        return organized_matches

    except Exception as e:
        print(f"Error fetching global matches: {e}")
        return {}

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

@st.cache_data(ttl=3600)
def get_detailed_stats(home_id, away_id):
    """
    Fetches detailed stats (Form, H2H) and calculates probabilities.
    Returns a text summary for GPT-4o.
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return "No API Key available for RapidAPI stats."
        
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
    }
    base_url = "https://api-football-v1.p.rapidapi.com/v3"
    
    # Helper to fetch last 5 matches
    def get_form(team_id):
        url = f"{base_url}/fixtures?team={team_id}&last=5&status=FT"
        try:
            return requests.get(url, headers=headers).json()
        except:
            return {}

    # Helper to calculate W/D/L %
    def calc_form_stats(data, team_id):
        if 'response' not in data or not data['response']:
            return 0, 0, 0, "No Data"
        
        matches = data['response']
        count = len(matches)
        wins = 0
        draws = 0
        losses = 0
        form_str = ""
        
        for m in matches:
            goals_home = m['goals']['home']
            goals_away = m['goals']['away']
            # Safety check for None
            if goals_home is None: goals_home = 0
            if goals_away is None: goals_away = 0
            
            is_home_team = (m['teams']['home']['id'] == team_id)
            
            my_goals = goals_home if is_home_team else goals_away
            opp_goals = goals_away if is_home_team else goals_home
            
            if my_goals > opp_goals:
                wins += 1
                form_str += "W"
            elif my_goals < opp_goals:
                losses += 1
                form_str += "L"
            else:
                draws += 1
                form_str += "D"
                
        return (wins/count)*100, (draws/count)*100, (losses/count)*100, form_str

    # Fetch Data
    home_data = get_form(home_id)
    away_data = get_form(away_id)
    
    # Calculate
    h_w, h_d, h_l, h_form = calc_form_stats(home_data, home_id)
    a_w, a_d, a_l, a_form = calc_form_stats(away_data, away_id)
    
    # Algorithm: Home Prob = (Home Win + Away Loss) / 2
    prob_home = (h_w + a_l) / 2
    prob_away = (a_w + h_l) / 2
    prob_draw = (h_d + a_d) / 2
    
    total = prob_home + prob_away + prob_draw
    if total > 0:
        p_h = round((prob_home / total) * 100, 1)
        p_a = round((prob_away / total) * 100, 1)
        p_d = round((prob_draw / total) * 100, 1)
    else:
        p_h, p_a, p_d = 33.3, 33.3, 33.3

    # H2H
    h2h_url = f"{base_url}/fixtures/headtohead?h2h={home_id}-{away_id}&last=5"
    try:
        h2h_data = requests.get(h2h_url, headers=headers).json()
        h2h_text = ""
        if 'response' in h2h_data:
            for m in h2h_data['response']:
                d = m['fixture']['date'][:10]
                s = m['score']['fulltime']
                h_goals = s['home'] if s['home'] is not None else 0
                a_goals = s['away'] if s['away'] is not None else 0
                h2h_text += f"- {d}: {m['teams']['home']['name']} {h_goals}-{a_goals} {m['teams']['away']['name']}\n"
    except:
        h2h_text = "No H2H Data"

    return f"""
    OFFICIAL RAPIDAPI STATS:
    HOME FORM (Last 5): {h_form} (Win {h_w}% | Draw {h_d}% | Loss {h_l}%)
    AWAY FORM (Last 5): {a_form} (Win {a_w}% | Draw {a_d}% | Loss {a_l}%)
    
    CALCULATED PROBABILITIES (Based on Form):
    HOME WIN: {p_h}%
    DRAW: {p_d}%
    AWAY WIN: {p_a}%
    
    HEAD-TO-HEAD (Last 5):
    {h2h_text}
    """
