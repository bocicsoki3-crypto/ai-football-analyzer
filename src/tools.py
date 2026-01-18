import requests
import os
import json

def get_rapid_stats(home_team, away_team):
    """
    RapidAPI adatok lekérése + MATEMATIKAI SZÁMÍTÁS a UI számára.
    Visszatérési érték: JSON string (nem csak szöveg).
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key: return json.dumps({"error": "Nincs RAPIDAPI_KEY"})

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
    }
    base_url = "https://api-football-v1.p.rapidapi.com/v3"

    # 1. ID Keresés
    def get_team_id(name):
        url = f"{base_url}/teams?search={name}"
        try:
            resp = requests.get(url, headers=headers).json()
            if resp['results'] > 0:
                return resp['response'][0]['team']['id']
        except:
            return None
        return None

    id_home = get_team_id(home_team)
    id_away = get_team_id(away_team)

    if not id_home or not id_away: return json.dumps({"error": f"Nem található ID: {home_team} vagy {away_team}"})

    # 2. Adatok lekérése (Forma)
    def get_fixtures(team_id):
        url = f"{base_url}/fixtures?team={team_id}&last=5&status=FT"
        return requests.get(url, headers=headers).json()

    home_data = get_fixtures(id_home)
    away_data = get_fixtures(id_away)

    # H2H
    h2h_url = f"{base_url}/fixtures/headtohead?h2h={id_home}-{id_away}&last=5"
    h2h_data = requests.get(h2h_url, headers=headers).json()

    # 3. MATEMATIKA: Számoljuk ki a %-okat!
    def calculate_stats(data_response, team_id):
        if 'response' not in data_response: return 0, 0, 0, 0, "Nincs adat"
        
        matches = data_response['response']
        count = len(matches)
        if count == 0: return 0, 0, 0, 0, "Nincs adat"
        
        btts_count = 0
        over25_count = 0
        goals_scored = 0
        goals_conceded = 0
        form_str = ""
        
        for m in matches:
            s = m['goals']
            # Hazai vagy vendég volt a vizsgált csapat?
            is_home = (m['teams']['home']['id'] == team_id)
            gf = s['home'] if is_home else s['away']
            ga = s['away'] if is_home else s['home']
            
            if gf is None: gf = 0
            if ga is None: ga = 0
            
            # BTTS
            if gf > 0 and ga > 0: btts_count += 1
            
            # Over 2.5
            if (gf + ga) > 2.5: over25_count += 1
            
            goals_scored += gf
            goals_conceded += ga
            
            res = "W" if gf > ga else ("L" if gf < ga else "D")
            form_str += f"[{res} {gf}-{ga}] "
            
        return (btts_count / count) * 100, (over25_count / count) * 100, goals_scored, goals_conceded, form_str

    # Számítások futtatása
    h_btts, h_over, h_gf, h_ga, h_form = calculate_stats(home_data, id_home)
    a_btts, a_over, a_gf, a_ga, a_form = calculate_stats(away_data, id_away)

    # Átlagolás a két csapatra
    avg_btts = round((h_btts + a_btts) / 2, 1)
    avg_over = round((h_over + a_over) / 2, 1)

    # Jelentés szövege (A Főnöknek)
    text_report = f"""
    OFFICIAL DATA (RAPIDAPI):
    HOME FORM: {h_form} (Scored: {h_gf}, Conceded: {h_ga})
    AWAY FORM: {a_form} (Scored: {a_gf}, Conceded: {a_ga})
    STATS CALCULATION:
    Home BTTS: {h_btts}% | Away BTTS: {a_btts}%
    Home Over 2.5: {h_over}% | Away Over 2.5: {a_over}%
    """

    # H2H hozzáadása a jelentéshez
    if 'response' in h2h_data:
        text_report += "\nH2H (Last 5):\n"
        for item in h2h_data['response']:
            d = item['fixture']['date'][:10]
            s = item['goals']
            text_report += f"- {d}: {s['home']}-{s['away']}\n"

    # 4. JSON ÖSSZEÁLLÍTÁSA (A Weboldalnak + A Főnöknek)
    # Megjegyzés: A szöglet/lap adatokat az API basic verziója nem adja vissza listában,
    # így oda becsült szöveget írunk, hogy ne legyen hiba.
    final_json = {
        "btts_percent": f"{avg_btts}%",
        "over_2_5_percent": f"{avg_over}%",
        "home_win_percent": "N/A (See Boss)", # Ezt a Boss dönti el
        "draw_percent": "N/A",
        "away_win_percent": "N/A",
        "expected_corners": "Nincs API adat (Premium kell)",
        "expected_cards": "Nincs API adat (Premium kell)",
        "analysis": text_report # ITT VAN A LÉNYEG A BOSSNAK
    }

    return json.dumps(final_json)
