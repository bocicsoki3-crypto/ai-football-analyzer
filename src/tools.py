# Fájl: src/tools.py 
import requests 
import os 
import json 

def get_rapid_stats(home_team, away_team): 
    """ 
    RAPIDAPI INTEGRÁCIÓ: Hivatalos adatok lekérése. 
    Kikerüli a pontatlan webes keresést és a hallucináló AI-t. 
    """ 
    api_key = os.getenv("RAPIDAPI_KEY") 
    if not api_key: return "ERROR: No RAPIDAPI_KEY found in .env" 

    headers = { 
        "x-rapidapi-key": api_key, 
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com" 
    } 
    # Removed backticks from the URL
    base_url = "https://api-football-v1.p.rapidapi.com/v3" 

    # 1. SEGÉDFÜGGVÉNY: Csapat ID keresése 
    def get_team_id(name): 
        url = f"{base_url}/teams?search={name}" 
        try: 
            resp = requests.get(url, headers=headers).json() 
            if resp['results'] > 0: 
                return resp['response'][0]['team']['id'] 
        except: 
            return None 
        return None 

    # 2. ADATGYŰJTÉS 
    id_home = get_team_id(home_team) 
    id_away = get_team_id(away_team) 
    
    if not id_home or not id_away: 
        return f"API ERROR: Could not find IDs for {home_team} or {away_team}." 

    # H2H (Egymás ellen - Utolsó 5) 
    h2h_url = f"{base_url}/fixtures/headtohead?h2h={id_home}-{id_away}&last=5" 
    h2h_data = requests.get(h2h_url, headers=headers).json() 

    # Forma (Utolsó 5 meccs) 
    def get_form(team_id): 
        url = f"{base_url}/fixtures?team={team_id}&last=5&status=FT" 
        data = requests.get(url, headers=headers).json() 
        form_str = "" 
        goals_for = 0 
        goals_against = 0 
        
        if 'response' not in data: return "No Data", 0, 0 

        for match in data['response']: 
            score = match['goals'] 
            # Hazai vagy vendég volt a csapat? 
            is_home = (match['teams']['home']['id'] == team_id) 
            gf = score['home'] if is_home else score['away'] 
            ga = score['away'] if is_home else score['home'] 
            
            if gf is None: gf = 0 
            if ga is None: ga = 0 
            
            goals_for += gf 
            goals_against += ga 
            result = "W" if gf > ga else ("L" if gf < ga else "D") 
            form_str += f"[{result} {gf}-{ga}] " 
        return form_str, goals_for, goals_against 

    home_form, h_gf, h_ga = get_form(id_home) 
    away_form, a_gf, a_ga = get_form(id_away) 

    # 3. JELENTÉS ÖSSZEÁLLÍTÁSA (Ezt kapja meg a GPT-4o) 
    report = f""" 
    OFFICIAL RAPIDAPI DATA REPORT: 
    ------------------------------------------- 
    MATCH: {home_team} (Home) vs {away_team} (Away) 
    
    HOME FORM (Last 5): {home_form} 
    -> Scored: {h_gf} | Conceded: {h_ga} 
    
    AWAY FORM (Last 5): {away_form} 
    -> Scored: {a_gf} | Conceded: {a_ga} 
    
    HEAD-TO-HEAD (Last 5 Meetings): 
    """ 
    if 'response' in h2h_data: 
        for item in h2h_data['response']: 
            date = item['fixture']['date'][:10] 
            score = item['goals'] 
            report += f"- {date}: {item['teams']['home']['name']} {score['home']} - {score['away']} {item['teams']['away']['name']}\n" 
    else: 
        report += "No H2H data found.\n" 
        
    return report
