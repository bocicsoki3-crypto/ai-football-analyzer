import requests
import os
import json
from datetime import datetime

class DataManager:
    def __init__(self):
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            "X-RapidAPI-Key": os.environ.get("RAPIDAPI_KEY", ""),
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }

    def _get_headers(self):
        # Refresh headers in case key changes
        return {
            "X-RapidAPI-Key": os.environ.get("RAPIDAPI_KEY", ""),
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }

    def get_todays_fixtures(self):
        date_str = datetime.now().strftime("%Y-%m-%d")
        url = f"{self.base_url}/fixtures"
        querystring = {"date": date_str}
        
        try:
            response = requests.get(url, headers=self._get_headers(), params=querystring)
            response.raise_for_status()
            data = response.json()
            return data.get("response", [])
        except Exception as e:
            return {"error": str(e)}

    def get_match_details(self, fixture_id, home_team_id, away_team_id, league_id, season):
        # 1. Standings
        standings = self._get_standings(league_id, season)
        
        # 2. Team Stats (Goals, Cards, Formations)
        home_stats = self._get_team_stats(home_team_id, league_id, season)
        away_stats = self._get_team_stats(away_team_id, league_id, season)
        
        # 3. Injuries
        injuries = self._get_injuries(fixture_id)
        
        # 4. Head-to-Head
        h2h = self._get_h2h(home_team_id, away_team_id)
        
        return {
            "fixture_id": fixture_id,
            "league_id": league_id,
            "home_team": home_stats,
            "away_team": away_stats,
            "standings": standings,
            "injuries": injuries,
            "h2h": h2h
        }

    def _get_injuries(self, fixture_id):
        url = f"{self.base_url}/injuries"
        querystring = {"fixture": fixture_id}
        try:
            response = requests.get(url, headers=self._get_headers(), params=querystring)
            data = response.json()
            if data.get("response"):
                # Simplify injury data
                return [f"{i['player']['name']} ({i['team']['name']}) - {i['player']['type']} ({i['player']['reason']})" for i in data["response"]]
            return []
        except:
            return []

    def _get_h2h(self, home_id, away_id):
        url = f"{self.base_url}/fixtures/headtohead"
        querystring = {"h2h": f"{home_id}-{away_id}", "last": 5}
        try:
            response = requests.get(url, headers=self._get_headers(), params=querystring)
            data = response.json()
            if data.get("response"):
                # Simplify H2H data
                results = []
                for f in data["response"]:
                    date = f['fixture']['date'][:10]
                    home = f['teams']['home']['name']
                    away = f['teams']['away']['name']
                    score = f"{f['goals']['home']}-{f['goals']['away']}"
                    results.append(f"{date}: {home} vs {away} ({score})")
                return results
            return []
        except:
            return []

    def _get_standings(self, league_id, season):
        url = f"{self.base_url}/standings"
        querystring = {"league": league_id, "season": season}
        try:
            response = requests.get(url, headers=self._get_headers(), params=querystring)
            data = response.json()
            if data.get("response"):
                # API returns a list of lists (groups). We usually want the first group or flatten all.
                # For most leagues it's just one group [[team1, team2...]]
                raw_standings = data["response"][0]["league"]["standings"]
                
                # Flatten the list if it's nested (some leagues have groups)
                flat_standings = []
                for group in raw_standings:
                    for team_data in group:
                        flat_standings.append({
                            "Helyezés": team_data['rank'],
                            "Csapat": team_data['team']['name'],
                            "M": team_data['all']['played'],
                            "GY": team_data['all']['win'],
                            "D": team_data['all']['draw'],
                            "V": team_data['all']['lose'],
                            "LG": team_data['all']['goals']['for'],
                            "KG": team_data['all']['goals']['against'],
                            "GK": team_data['goalsDiff'],
                            "Pont": team_data['points'],
                            "Forma": team_data['form']
                        })
                return flat_standings
            return []
        except:
            return []

    def _get_team_stats(self, team_id, league_id, season):
        url = f"{self.base_url}/teams/statistics"
        querystring = {"league": league_id, "season": season, "team": team_id}
        try:
            response = requests.get(url, headers=self._get_headers(), params=querystring)
            data = response.json()
            if data.get("response"):
                return data["response"]
            return {}
        except:
            return {}
