import requests
import os
import json

def get_rapid_stats(home_team, away_team):
    """
    RapidAPI adatok + FULL STATISZTIKAI SZÁMÍTÁS (1X2 + Gólok + Szöglet/Lap).
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key: return json.dumps({"error": "Nincs RAPIDAPI_KEY", "btts_percent": "0%", "over_2_5_percent": "0%"})

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

    if not id_home or not id_away: return json.dumps({"analysis": f"Nem található ID: {home_team} vagy {away_team}"})

    # 2. Adatok lekérése
    def get_fixtures(team_id):
        url = f"{base_url}/fixtures?team={team_id}&last=5&status=FT"
        return requests.get(url, headers=headers).json()

    home_data = get_fixtures(id_home)
    away_data = get_fixtures(id_away)

    # H2H
    h2h_url = f"{base_url}/fixtures/headtohead?h2h={id_home}-{id_away}&last=5"
    h2h_data = requests.get(h2h_url, headers=headers).json()

    # 3. MATEMATIKA: Minden statisztika kiszámítása
    def calculate_stats(data_response, team_id):
        if 'response' not in data_response: return 0, 0, 0, 0, 0, 0, 0, "Nincs adat", 0
        
        matches = data_response['response']
        count = len(matches)
        if count == 0: return 0, 0, 0, 0, 0, 0, 0, "Nincs adat", 0
        
        btts_count = 0
        over25_count = 0
        goals_scored = 0
        goals_conceded = 0
        total_match_goals = 0
        
        win_c = 0
        draw_c = 0
        loss_c = 0
        
        form_str = ""
        for m in matches:
            s = m['goals']
            is_home = (m['teams']['home']['id'] == team_id)
            gf = s['home'] if is_home else s['away']
            ga = s['away'] if is_home else s['home']
            
            if gf is None: gf = 0
            if ga is None: ga = 0
            
            # Gól statok
            if gf > 0 and ga > 0: btts_count += 1
            if (gf + ga) > 2.5: over25_count += 1
            
            goals_scored += gf
            goals_conceded += ga
            total_match_goals += (gf + ga)
            
            # Eredmény statok (W/D/L)
            if gf > ga:
                res = "W"
                win_c += 1
            elif gf < ga:
                res = "L"
                loss_c += 1
            else:
                res = "D"
                draw_c += 1
                
            form_str += f"[{res} {gf}-{ga}] "
            
        # Átlag gól / meccs
        avg_goals = total_match_goals / count
        
        # Százalékok (0-100)
        win_pct = (win_c / count) * 100
        draw_pct = (draw_c / count) * 100
        loss_pct = (loss_c / count) * 100
        
        return (btts_count / count) * 100, (over25_count / count) * 100, goals_scored, goals_conceded, win_pct, draw_pct, loss_pct, form_str, avg_goals

    # Adatok feldolgozása
    # h_w = hazai győzelmi %, h_d = hazai döntetlen %, h_l = hazai vereség %
    h_btts, h_over, h_gf, h_ga, h_w, h_d, h_l, h_form, h_avg_g = calculate_stats(home_data, id_home)
    # a_w = vendég győzelmi %, ...
    a_btts, a_over, a_gf, a_ga, a_w, a_d, a_l, a_form, a_avg_g = calculate_stats(away_data, id_away)

    # --- 1. GÓL STATISZTIKÁK ---
    avg_btts = round((h_btts + a_btts) / 2, 1)
    avg_over = round((h_over + a_over) / 2, 1)

    # --- 2. GYŐZELMI VALÓSZÍNŰSÉGEK (1X2) ---
    # Hazai esély = (Hazai nyerési hajlandóság + Vendég vesztési hajlandóság) / 2
    prob_home = (h_w + a_l) / 2
    # Vendég esély = (Vendég nyerési hajlandóság + Hazai vesztési hajlandóság) / 2
    prob_away = (a_w + h_l) / 2
    # Döntetlen esély = (Hazai X hajlandóság + Vendég X hajlandóság) / 2
    prob_draw = (h_d + a_d) / 2

    # Normalizálás 100%-ra (hogy a kördiagram szép legyen)
    total_prob = prob_home + prob_away + prob_draw
    if total_prob > 0:
        final_home = round((prob_home / total_prob) * 100, 1)
        final_away = round((prob_away / total_prob) * 100, 1)
        final_draw = round((prob_draw / total_prob) * 100, 1)
    else:
        # Ha nincs adat, 33-33-33%
        final_home, final_away, final_draw = 33.3, 33.3, 33.3

    # --- 3. PROJEKCIÓ (Szöglet & Lap) ---
    combined_avg_goals = (h_avg_g + a_avg_g) / 2

    # Szöglet
    est_corners = 8.5 + (combined_avg_goals - 2.5) * 1.5
    est_corners = max(6.5, min(13.5, est_corners))
    corner_text = f"Over {round(est_corners, 1)} (Est)"

    # Lap
    est_cards = 3.5
    if avg_btts > 60: est_cards += 1.0
    if combined_avg_goals < 2.0: est_cards += 0.5 # Küzdelmes meccs
    # Extra: Ha derby vagy szoros (Draw esély magas)
    if final_draw > 30: est_cards += 0.5
    card_text = f"Over {round(est_cards, 1)} (Est)"

    # --- JELENTÉS ---
    text_report = f"""
    OFFICIAL DATA (RAPIDAPI):
    HOME: {h_form} (W:{h_w}% D:{h_d}% L:{h_l}%)
    AWAY: {a_form} (W:{a_w}% D:{a_d}% L:{a_l}%)
    STATS ENGINE:
    
    Win Probability: Home {final_home}% | Draw {final_draw}% | Away {final_away}%
    
    BTTS: {avg_btts}% | Over 2.5: {avg_over}%
    """

    if 'response' in h2h_data:
        text_report += "\nH2H (Last 5):\n"
        for item in h2h_data['response']:
            d = item['fixture']['date'][:10]
            s = item['goals']
            text_report += f"- {d}: {s['home']}-{s['away']}\n"

    # 4. VÉGLEGES JSON
    final_json = {
        "btts_percent": f"{avg_btts}%",
        "over_2_5_percent": f"{avg_over}%",
        "home_win_percent": f"{final_home}%",  # VÉGRE VAN ADAT!
        "draw_percent": f"{final_draw}%",      # VÉGRE VAN ADAT!
        "away_win_percent": f"{final_away}%",  # VÉGRE VAN ADAT!
        "expected_corners": corner_text,
        "expected_cards": card_text,
        "analysis": text_report
    }

    return json.dumps(final_json)
