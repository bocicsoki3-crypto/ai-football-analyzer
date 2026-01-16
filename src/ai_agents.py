import os
from groq import Groq
import json
import ollama
from tavily import TavilyClient

class AICommittee:
    def __init__(self):
        self.groq_client = None
        self.tavily_client = None
        self.last_prompts = {}
    
    def _setup_clients(self):
        # Initialize Groq
        if not self.groq_client and os.environ.get("GROQ_API_KEY"):
            self.groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
        # Initialize Tavily
        if not self.tavily_client and os.environ.get("TAVILY_API_KEY"):
            self.tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

    def get_last_prompts(self):
        return self.last_prompts

    def run_statistician(self, match_data):
        self._setup_clients()
        
        # Extract computed stats if available
        comp_stats = match_data.get('computed_stats', {})
        h_corn = comp_stats.get('home_team_corners', 'Nincs adat')
        a_corn = comp_stats.get('away_team_corners', 'Nincs adat')
        h_card = comp_stats.get('home_team_yellow_cards', 'Nincs adat')
        a_card = comp_stats.get('away_team_yellow_cards', 'Nincs adat')
        
        # Use Ollama (qwen2.5:7b) or Groq
        prompt = f"""
        TE VAGY A STATISZTIKUS (AI Agent). A világ legjobb sportfogadási matematikusa.
        
        Adatok: {json.dumps(match_data)}
        
        KONKRÉT SZEZONBELI ÁTLAGOK (RapidAPI):
        - Hazai Szöglet Átlag: {h_corn}
        - Vendég Szöglet Átlag: {a_corn}
        - Hazai Sárga Lap Átlag: {h_card}
        - Vendég Sárga Lap Átlag: {a_card}
        
        SZIGORÚ UTASÍTÁS:
        1. KERÜLD az általánosításokat (pl. "szoros meccs várható").
        2. SZÁMSZERŰSÍTS: Minden állítást támassz alá konkrét számokkal (pl. "A hazai csapat xG mutatója az utolsó 3 meccsen 2.1, míg a vendégeké csak 0.8").
        3. SÚLYOZOTT ELEMZÉS: A sérülteket és az eltiltottakat ne csak felsorold, hanem határozd meg a hiányuk számszerű hatását a csapat erejére.
        4. TILOS ISMÉTLÉS: Tilos ugyanazt a százalékot adnod, mint egy sablon! Minden számot (BTTS, Over 2.5, Szögletek) a fenti KONKRÉT adatokból számolj ki újra!
        
        FELADAT:
        Végezz mély statisztikai elemzést. Ne csak átlagolj, hanem súlyozz!
        1. FORMÁK: A legutóbbi 5 meccs eredménye fontosabb, mint az egész szezon.
        2. HAZAI/VENDÉG TELJESÍTMÉNY: Külön kezeld a Hazai csapat otthoni és a Vendég idegenbeli mutatóit.
        3. POISSON ELOSZLÁS: Becsüld meg a várható gólokat (xG) a védelmi és támadási erők alapján.
        
        KÖTELEZŐ SZÁMÍTÁSOK (Valós adatokból):
        - Szögletek: Ha az adatok szerint kevés a szöglet (pl. átlagok összege < 8), írj keveset! Ne hasalj be 9-et, ha a statisztika 4-et mutat!
        - Lapok: (Hazai lap átlag + Vendég lap átlag + Bíró szigora ha van).
        - BTTS (Mindkét csapat lő gólt): Konkrét képlet alapján! (Hazai otthoni gólszerzési % + Vendég idegenbeli gólszerzési %) / 2. NE HASALJ (pl. 58% helyett 58.4%)!
        - Over 2.5: A várható gólok (xG) összegéből számolj Poisson eloszlással pontos %-ot!
        
        KIMENETI FORMÁTUM (Kizárólag érvényes JSON):
        {{
            "home_win_percent": "XX%",
            "draw_percent": "XX%",
            "away_win_percent": "XX%",
            "expected_corners": "Over/Under X.5 (pl. 'Over 9.5' - Indoklás: Hazai 6.5 + Vendég 4.0)",
            "expected_cards": "Over/Under X.5 (pl. 'Over 4.5' - Indoklás: Parázs meccs várható)",
            "btts_percent": "XX.X%",
            "over_2_5_percent": "XX.X%",
            "analysis": "Tömör, profi elemzés konkrét számokkal."
        }}
        
        Csak a JSON objektumot add vissza!
        """
        
        self.last_prompts['statistician'] = prompt

        try:
            # Prefer Groq for better instruction following if available, otherwise Ollama
            if self.groq_client:
                 completion = self.groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7
                    )
                 content = completion.choices[0].message.content
                 # Clean up potential markdown code blocks
                 if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                 elif "```" in content:
                        content = content.split("```")[1]
                 return content.strip()
            
            # Fallback to Ollama
            response = ollama.chat(model='qwen2.5:7b', messages=[
                {'role': 'user', 'content': prompt},
            ])
            content = response['message']['content']
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]
            return content.strip()

        except Exception as e:
            return f'{{"error": "Hiba a Statisztikusnál: {str(e)}"}}'

    def run_scout(self, home_team, away_team, injuries, h2h, referee=None, venue=None):
        self._setup_clients()
        
        search_context = ""
        sources_used = []
        
        # Tavily Search Integration
        if self.tavily_client:
            try:
                # Kiterjesztett keresés: xG, xGA, PPG, hiányzók, MOTIVÁCIÓ, BÍRÓ, IDŐJÁRÁS, ODDS
                query = f"""
                site:fbref.com OR site:footystats.org OR site:transfermarkt.com OR site:whoscored.com OR site:flashscore.com 
                {home_team} vs {away_team} head to head results last 5 matches injuries lineups referee stats weather forecast betting odds 
                relegation battle cup rotation motivation
                """
                # Clean up query string
                query = " ".join(query.split())
                
                search_result = self.tavily_client.search(query, search_depth="advanced", max_results=7)
                
                context_parts = []
                if 'results' in search_result:
                    for res in search_result['results']:
                        context_parts.append(f"Forrás: {res['url']}\nTartalom: {res['content']}")
                        sources_used.append(res['url'])
                
                search_context = "\n\n".join(context_parts)
            except Exception as e:
                search_context = f"Hiba a Tavily keresésnél: {str(e)}"

        if not self.groq_client:
            return f"Groq API Key hiányzik. (Tavily infó: {len(sources_used)} forrás)"
            
        prompt = f"""
        TE VAGY A HÍRSZERZŐ (Groq - Llama 3.3 70B). Egy oknyomozó sportújságíró.
        
        Meccs: {home_team} vs {away_team}
        Bíró (adatbázisból): {referee if referee else "Ismeretlen"}
        Helyszín: {venue if venue else "Ismeretlen"}
        
        FRISS INTERNETES KERESÉSI ADATOK (Tavily):
        {search_context}
        
        FELADAT:
        Ne csak felsorold a híreket, hanem keress specifikus ANOMÁLIÁKAT!
        
        KÖVETELMÉNYEK:
        1. MOTIVÁCIÓS FAKTOR: Van-e tétje a meccsnek? Kiesés elleni harc, kupaszereplés miatti pihentetés? Írd le!
        2. BÍRÓI STATISZTIKA: Ha találsz adatot a bíróról (sárga/piros lap átlag, büntetők), írd le!
        3. EGYMÁS ELLENI (H2H): Ha a keresésben találtál friss H2H eredményeket (Fbref/Footystats), sorold fel a legutóbbi 3-at!
        4. PÁLYAÁLLAPOT/IDŐJÁRÁS: Befolyásolja az időjárás (eső, hó, szél) a játékot?
        5. ODDSOK: Ha találsz fogadási oddsokat a szövegben, jegyezd fel őket az "Érték" számításhoz!
        6. HIÁNYZÓK HATÁSA: Konkrétan nevezd meg a kulcshianyozókat.
        
        Kimeneted legyen tömör, lényegretörő, mint egy titkos jelentés az edzőnek. Említsd meg a forrást.
        """
        
        self.last_prompts['scout'] = prompt
        
        try:
            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Hiba a Hírszerzőnél: {str(e)}"

    def run_tactician(self, match_data):
        self._setup_clients()
        if not self.groq_client:
            return "Groq API Key hiányzik."
            
        prompt = f"""
        TE VAGY A TAKTIKUS (Groq). Egy labdarúgó edző.
        
        Adatok: {json.dumps(match_data)}
        
        FELADAT:
        Vizualizáld a mérkőzést a számok alapján!
        1. LABDABIRTOKLÁS: Ki fogja dominálni a játékot? (Pl. Hazai passzpontosság 88% -> Dominancia várható).
        2. KONTRAJÁTÉK: A vendégcsapat veszélyes kontrákból?
        3. VÉDEKEZÉS: Magasan védekeznek vagy buszt tolnak a kapu elé?
        
        Írj le egy forgatókönyvet arról, hogyan fog kinézni a játék képe a pályán!
        """
        
        self.last_prompts['tactician'] = prompt
        
        try:
            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile", # Or mix models
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
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
        TE VAGY A FŐNÖK (Groq - Llama 3.3 70B). A "Keresztapa" a sportfogadásban.
        
        KORÁBBI HIBÁK ÉS TANULSÁGOK (VISSZACSATOLÁS):
        {lessons_text}
        
        UTASÍTÁS: KÖTELEZŐEN olvasd el a fenti tanulságokat! Ha egy korábbi tipp nem jött be hasonló szituációban, most dönts máshogy!
        
        BEMENETEK:
        1. STATISZTIKUS JELENTÉSE (Matek & Valószínűségek): {statistician_report}
        2. HÍRSZERZŐ JELENTÉSE (Hírek, Motiváció, Oddsok): {scout_report}
        3. TAKTIKUS JELENTÉSE (Játék képe): {tactician_report}
        4. MECCS ADATOK: {json.dumps(match_data)}
        
        FELADAT:
        Hozz megkérdőjelezhetetlen döntést és keress "VALUE"-t (Értéket).
        
        VALUE SZÁMÍTÁS (KÖTELEZŐ):
        - Vesd össze a saját valószínűségszámításodat (vagy a Statisztikusét) a Hírszerző által talált (vagy becsült) piaci oddsokkal.
        - Csak akkor ajánlj 'Value Tippet', ha az általad számolt esély legalább 5-10%-kal magasabb, mint amit az odds sugall.
        - Képlet: (Saját % / 100) > (1 / Odds) + 0.05
        - Ha nem találsz oddsot, becsüld meg, mennyi lenne a reális, és írd oda, hogy "becsült odds alapján".
        
        DÖNTÉSI STRATÉGIA:
        - Ha a Statisztikus HAZAIT mond, de a Hírszerző szerint a fél csapat sérült -> Fogadj ELLENE vagy hagyd ki!
        - Légy szigorú! Csak akkor adj tippet, ha 70% feletti a biztonság.
        
        KIMENETI FORMÁTUM (Szigorúan ezt kövesd):
        
        **RÖVID ELEMZÉS**: [3-4 mondat. Indokold meg, miért döntöttél így, és említsd meg, hogyan használtad fel a korábbi tanulságokat!]
        
        **PONTOS VÉGEREDMÉNY TIPP**: [CSAK A SZÁM! pl. 2-1. Reális eredmény legyen!]
        
        **VALUE TIPP**: [CSAK A TIPP TÖMÖREN! pl. "Hazai győzelem @ 2.10 (Value: 8%)". Ha nincs value, írd: "Nincs Value".]
        """
        
        self.last_prompts['boss'] = prompt
        
        try:
            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Hiba a Főnöknél: {str(e)}"

    def run_prophet(self, match_data, home_team, away_team):
        # Use Ollama (qwen2.5:7b)
        prompt = f"""
        TE VAGY A PRÓFÉTA (AI Agent). Jövőbelátó.
        
        Meccs: {home_team} vs {away_team}
        Adatok: {json.dumps(match_data)}
        
        SZIGORÚ UTASÍTÁS:
        1. KERÜLD az általánosításokat.
        2. SZCENÁRIÓ-ELEMZÉS: A timeline tartalmazzon különböző forgatókönyveket (pl. mi van, ha korai gól esik?).
        
        FELADAT:
        Készíts egy VALÓSZERŰ meccs-timeline-t 3 különböző forgatókönyv alapján:
        1. Korai gól forgatókönyve.
        2. "Szenvedős" 0-0 félidő forgatókönyve.
        3. Késői dráma (70. perc után).
        
        Válassz ki EGYET ezek közül, ami a legvalószínűbb a statisztikák alapján, és bontsd le negyedórákra.
        
        KIMENETI FORMÁTUM (JSON ARRAY):
        [
            {{"period": "0-15'", "event": "Korai nyomás, Hazai kapufa (Forgatókönyv: Dominancia)", "score_after": "0-0"}},
            {{"period": "16-30'", "event": "Vendég kontra, GÓL! (Forgatókönyv: Kontrajáték)", "score_after": "0-1"}},
            ...
        ]
        
        Csak a JSON tömböt add vissza, semmi mást!
        """
        
        self.last_prompts['prophet'] = prompt
        
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
                        temperature=0.7
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
