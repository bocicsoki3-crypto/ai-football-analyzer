import os
from groq import Groq
import json
import ollama

class AICommittee:
    def __init__(self):
        self.groq_client = None
    
    def _setup_clients(self):
        # Initialize Groq
        if not self.groq_client and os.environ.get("GROQ_API_KEY"):
            self.groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def run_statistician(self, match_data):
        # Use Ollama (qwen2.5:7b)
        prompt = f"""
        TE VAGY A STATISZTIKUS (AI Agent).
        
        Adatok: {json.dumps(match_data)}
        
        FELADAT:
        Számolj és becsülj Poisson-eloszlás és a megadott adatok alapján:
        1. Várható Gólok (xG) mindkét csapatra.
        2. Győzelmi esélyek (Hazai / Döntetlen / Vendég) százalékban.
        3. Várható Szögletek (Corners): Adj meg egy KONKRÉT fogadási határt a legvalószínűbb kimenetelre (pl. "Over 8.5" vagy "Over 9.5" vagy "Under 10.5"). NE adj meg tartományt!
        4. Várható Lapok (Cards): Adj meg egy KONKRÉT fogadási határt a legvalószínűbb kimenetelre (pl. "Over 3.5" vagy "Over 4.5"). NE adj meg tartományt!
        5. BTTS (Both Teams To Score) valószínűsége %.
        6. Over/Under 2.5 Gól valószínűsége %.

        KIMENETI FORMÁTUM (Kizárólag érvényes JSON):
        {{
            "home_win_percent": "XX%",
            "draw_percent": "XX%",
            "away_win_percent": "XX%",
            "expected_corners": "Over/Under X.5",
            "expected_cards": "Over/Under X.5",
            "btts_percent": "XX%",
            "over_2_5_percent": "XX%",
            "analysis": "Rövid szöveges magyarázat (max 2 mondat)..."
        }}
        
        Csak a JSON objektumot add vissza!
        """
        
        try:
            response = ollama.chat(model='qwen2.5:7b', messages=[
                {'role': 'user', 'content': prompt},
            ])
            content = response['message']['content']
            # Clean up potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]
            return content.strip()
        except Exception as e:
            # Fallback to Groq if Ollama fails
            self._setup_clients()
            if self.groq_client:
                try:
                    completion = self.groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1
                    )
                    content = completion.choices[0].message.content
                    # Clean up potential markdown code blocks
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1]
                    return content.strip()
                except Exception as groq_e:
                    return f'{{"error": "Hiba a Statisztikusnál (Ollama & Groq): {str(e)} | {str(groq_e)}"}}'
            return f'{{"error": "Hiba a Statisztikusnál (Ollama): {str(e)}"}}'

    def run_scout(self, home_team, away_team, injuries, h2h, referee=None, venue=None):
        self._setup_clients()
        if not self.groq_client:
            return "Groq API Key hiányzik."
            
        prompt = f"""
        TE VAGY A HÍRSZERZŐ (Groq - Llama 3.3 70B).
        
        Meccs: {home_team} vs {away_team}
        
        FELADAT:
        Mivel nincs közvetlen internetelérésed, elemezd a csapatok általános keretét és a szezon során tapasztalt tipikus hiányzókat vagy gyenge pontokat a rendelkezésre álló tudásod alapján.
        Ha vannak ismert sérülékeny pontjai a védelemnek, emeld ki azokat!
        """
        
        try:
            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Hiba a Hírszerzőnél: {str(e)}"

    def run_tactician(self, match_data):
        self._setup_clients()
        if not self.groq_client:
            return "Groq API Key hiányzik."
            
        prompt = f"""
        TE VAGY A TAKTIKUS (Groq).
        
        Adatok: {json.dumps(match_data)}
        
        FELADAT:
        Elemezd a stílusokat (pl. letámadás vs. kontra) a meccs kontextusában.
        Hogyan illeszkedik a két csapat stílusa egymáshoz?
        """
        
        try:
            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile", # Or mix models
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Hiba a Taktikusnál: {str(e)}"

    def run_boss(self, statistician_report, scout_report, tactician_report, match_data, lessons=None):
        self._setup_clients()
        if not self.groq_client:
            return "Groq API Key hiányzik."
            
        lessons_text = ""
        if lessons:
            lessons_text = "\n".join(lessons)
            
        prompt = f"""
        TE VAGY A FŐNÖK (Groq - Llama 3.3 70B).
        
        KORÁBBI HIBÁK ÉS TANULSÁGOK (MEMÓRIA):
        {lessons_text}
        
        VEDD FIGYELEMBE EZEKET A TANULSÁGOKAT A DÖNTÉSNÉL!
        
        BEMENETEK:
        1. STATISZTIKUS JELENTÉSE: {statistician_report}
        2. HÍRSZERZŐ JELENTÉSE (Sérültek, H2H, Bíró): {scout_report}
        3. TAKTIKUS JELENTÉSE: {tactician_report}
        4. MECCS ADATOK: {json.dumps(match_data)}
        
        FELADAT:
        Vesd össze az adatokat. Keresd a piaci rést (Value Betting)!
        Ha a statisztika hazait mond, de a hírszerző szerint sok a sérült, korrigálj!
        Figyelj az xG (Várható gólok) és a forma tendenciákra az adatokból.
        
        KIMENETI FORMÁTUM (Szigorúan ezt kövesd):
        
        **RÖVID ELEMZÉS**: [2-3 mondat összefoglaló, indoklással]
        
        **PONTOS VÉGEREDMÉNY TIPP**: [CSAK A SZÁM! pl. 2-1. SEMMI MÁS SZÖVEG!]
        
        **VALUE TIPP**: [CSAK A TIPP TÖMÖREN! pl. Hazai győzelem vagy BTTS. SEMMI MAGYARÁZAT!]
        """
        
        try:
            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Hiba a Főnöknél: {str(e)}"

    def run_prophet(self, match_data, home_team, away_team):
        # Use Ollama (qwen2.5:7b) - Already defined above in previous search_replace, 
        # but this block is to replace the OLD run_prophet method in the file
        prompt = f"""
        TE VAGY A PRÓFÉTA (AI Agent).
        
        Meccs: {home_team} vs {away_team}
        Adatok: {json.dumps(match_data)}
        
        FELADAT:
        Készíts egy "Mérkőzés Forgatókönyvet" (Match Scenario).
        Oszd fel a mérkőzést 15 perces szakaszokra.
        Jósolj meg eseményeket (gól, lap, dominancia) minden szakaszra.
        
        KIMENETI FORMÁTUM (JSON ARRAY):
        [
            {{"period": "0-15'", "event": "...", "score_after": "0-0"}},
            {{"period": "16-30'", "event": "...", "score_after": "..."}},
            ...
            {{"period": "76-90'", "event": "...", "score_after": "..."}}
        ]
        
        Csak a JSON tömböt add vissza, semmi mást!
        """
        
        try:
            response = ollama.chat(model='qwen2.5:7b', messages=[
                {'role': 'user', 'content': prompt},
            ])
            content = response['message']['content']
            # Extract JSON if wrapped in code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]
            return content.strip()
        except Exception as e:
            self._setup_clients()
            if self.groq_client:
                try:
                    completion = self.groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2
                    )
                    content = completion.choices[0].message.content
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1]
                    return content.strip()
                except Exception as groq_e:
                    return f"Hiba a Prófétánál (Ollama & Groq): {str(e)} | {str(groq_e)}"
            return f"Hiba a Prófétánál (Ollama): {str(e)}"

    def analyze_match(self, match_data, home_team_name, away_team_name, lessons=None):
        # 1. Step: Statistician
        stat_report = self.run_statistician(match_data)
        
        # 2. Step: Scout
        injuries = match_data.get('injuries', [])
        h2h = match_data.get('h2h', [])
        scout_report = self.run_scout(home_team_name, away_team_name, injuries, h2h)
        
        # 3. Step: Tactician
        tactician_report = self.run_tactician(match_data)
        
        # 4. Step: The Prophet (Timeline)
        prophet_report = self.run_prophet(match_data, home_team_name, away_team_name)
        
        # 5. Step: The Boss
        final_verdict = self.run_boss(stat_report, scout_report, tactician_report, match_data, lessons)
        
        return {
            "statistician": stat_report,
            "scout": scout_report,
            "tactician": tactician_report,
            "prophet": prophet_report,
            "boss": final_verdict
        }
