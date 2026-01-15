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
        
        # 2. Last 5 matches (Form) - usually available in standings or separate fixtures call
        # We will extract form from standings if available, or fetch last fixtures
        
        # 3. Goal Stats
        home_stats = self._get_team_stats(home_team_id, league_id, season)
        away_stats = self._get_team_stats(away_team_id, league_id, season)
        
        return {
            "fixture_id": fixture_id,
            "league_id": league_id,
            "home_team": home_stats,
            "away_team": away_stats,
            "standings": standings
        }

    def _get_standings(self, league_id, season):
        url = f"{self.base_url}/standings"
        querystring = {"league": league_id, "season": season}
        try:
            response = requests.get(url, headers=self._get_headers(), params=querystring)
            data = response.json()
            if data.get("response"):
                return data["response"][0]["league"]["standings"]
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
