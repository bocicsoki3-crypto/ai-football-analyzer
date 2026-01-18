import os
import time
import re
import json
import traceback
from groq import Groq
from tavily import TavilyClient
from mistralai import Mistral
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from datetime import datetime

class AICommittee:
    def __init__(self):
        self.groq_client = None
        self.tavily_client = None
        self.mistral_client = None
        self.gemini_model = None
        self.last_prompts = {}
    
    def _setup_clients(self):
        # Initialize Groq
        if not self.groq_client and os.environ.get("GROQ_API_KEY"):
            self.groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
        # Initialize Tavily
        if not self.tavily_client and os.environ.get("TAVILY_API_KEY"):
            self.tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        # Initialize Mistral
        if not self.mistral_client and os.environ.get("MISTRAL_API_KEY"):
            self.mistral_client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
        # Initialize Gemini
        if os.environ.get("GOOGLE_API_KEY"):
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            # A list_models() alapjan a legstabilabb elerheto verzio:
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')

    def _generate_with_retry(self, prompt):
        """
        Executes Gemini generation with Robust Retry logic for 429 errors.
        Retries up to 5 times with increasing delay.
        """
        max_retries = 5
        wait_time = 30 # Kezdésnek 30 másodperc

        last_error = None

        for attempt in range(max_retries):
            try:
                # Próbáljuk meg lekérni az adatot
                response = self.gemini_model.generate_content(prompt)
                return response.text
            except (ResourceExhausted, ServiceUnavailable) as e:
                # Ha 429-es hibát kapunk (Túl gyorsak vagyunk)
                print(f"⚠️ Google API Limit elérve! Várakozás {wait_time} másodpercig... (Próbálkozás: {attempt+1}/{max_retries})")
                last_error = e
                time.sleep(wait_time)
                wait_time += 10 # Növeljük a várakozási időt minden hiba után
            except Exception as e:
                print(f"Egyéb hiba történt: {e}")
                last_error = e
                break
        
        # Ha minden próbálkozás sikertelen, adjunk vissza részletes hibát
        error_details = f"{str(last_error)}\n{traceback.format_exc()}" if last_error else "Ismeretlen hiba"
        return f"Hiba: Nem sikerült lekérni az adatot 5 próbálkozás után sem.\n\nTechnikai részletek:\n{error_details}"

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
        
        # TEMPLATE DEFINITION (No f-string to avoid JSON conflict)
        prompt_template = """
        TE VAGY A STATISZTIKUS (AI Agent). A világ legjobb sportfogadási matematikusa.
        
        Adatok: __MATCH_DATA__
        
        KONKRÉT SZEZONBELI ÁTLAGOK (RapidAPI):
        - Hazai Szöglet Átlag: __H_CORN__
        - Vendég Szöglet Átlag: __A_CORN__
        - Hazai Sárga Lap Átlag: __H_CARD__
        - Vendég Sárga Lap Átlag: __A_CARD__
        
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
        {
            "home_win_percent": "XX%",
            "draw_percent": "XX%",
            "away_win_percent": "XX%",
            "expected_corners": "Over/Under X.5 (pl. 'Over 9.5' - Indoklás: Hazai 6.5 + Vendég 4.0)",
            "expected_cards": "Over/Under X.5 (pl. 'Over 4.5' - Indoklás: Parázs meccs várható)",
            "btts_percent": "XX.X%",
            "over_2_5_percent": "XX.X%",
            "analysis": "Tömör, profi elemzés konkrét számokkal."
        }
        
        Csak a JSON objektumot add vissza!
        """
        
        # Safe Injection
        prompt = prompt_template.replace("__MATCH_DATA__", json.dumps(match_data))
        prompt = prompt.replace("__H_CORN__", str(h_corn))
        prompt = prompt.replace("__A_CORN__", str(a_corn))
        prompt = prompt.replace("__H_CARD__", str(h_card))
        prompt = prompt.replace("__A_CARD__", str(a_card))
        
        self.last_prompts['statistician'] = prompt

        try:
            # Prefer Groq for better instruction following
            if self.groq_client:
                 completion = self.groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7
                    )
                 content = completion.choices[0].message.content
                 
                 # Robust JSON Extraction (Regex)
                 try:
                    json_match = re.search(r'{.*}', content, re.DOTALL)
                    if json_match:
                        return json_match.group(0)
                    else:
                        # Fallback if no brackets found (unlikely but possible)
                        return content.strip()
                 except:
                    return content.strip()
            
            return '{"error": "Nincs Groq kliens konfigurálva."}'

        except Exception as e:
            print(f"Hiba a Statisztikusnál: {str(e)}")
            print(traceback.format_exc()) # Print full traceback
            return f'{{"error": "Hiba a Statisztikusnál: {str(e)}"}}'

    def run_scout(self, home_team, away_team, injuries, h2h, referee=None, venue=None, match_date=None):
        """
        Scout Agent: Keres, majd GPT-4o-val KISZŰRI a lényeget (Bíró, Időjárás, Sérültek).
        """
        self._setup_clients()
        import os
        from openai import OpenAI
        
        # 1. TAVILY KERESÉS (Nyers adatok gyűjtése)
        search_context = ""
        if self.tavily_client:
            try:
                if not match_date:
                    match_date = datetime.now().strftime("%Y-%m-%d")
                
                # Bővített lekérdezés: Bíró, Időjárás, Kezdőcsapatok
                query = f"{home_team} vs {away_team} referee weather injuries lineups news {match_date} site:fbref.com OR site:whoscored.com OR site:sportsmole.co.uk"
                
                search_result = self.tavily_client.search(query, search_depth="advanced", max_results=5)
                
                context_parts = []
                if 'results' in search_result:
                    for res in search_result['results']:
                        content = res.get('content', '')[:1500] # Több tartalom a GPT-4o-nak
                        context_parts.append(f"SOURCE: {res['url']}\nCONTENT: {content}...")
                
                search_context = "\n\n".join(context_parts)
            except Exception as e:
                print(f"Tavily Error: {e}")
                search_context = f"Hiba a Tavily keresésnél: {e}"
        else:
             return "Nincs Tavily API kulcs."

        if not search_context:
            return "Nem találtam friss híreket a meccsről."

        # 2. GPT-4o SZŰRÉS (Adatbányászat)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: return search_context # Fallback ha nincs OpenAI kulcs
        
        client = OpenAI(api_key=api_key)
        
        system_prompt = """
        You are a Football Scout. 
        TASK: Extract specific details from the news text provided.
        
        EXTRACT THESE 4 POINTS CONCISELY IN HUNGARIAN (MAGYARUL):
        1. REFEREE (BÍRÓ): Name & Stats (Strict? Cards per game?).
        2. WEATHER (IDŐJÁRÁS): Forecast for match time (Rain? Wind? Temp?).
        3. INJURIES (SÉRÜLTEK): Key players missing (Home vs Away).
        4. LINEUPS (KEZDŐK): Confirmed or Expected starting XI changes.
        
        Output must be clean and factual in HUNGARIAN.
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"KNOWN DATA (API):\nReferee: {referee}\nVenue: {venue}\nInjuries (API): {injuries}\n\nRAW SEARCH RESULTS:\n{search_context}"}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Hiba a Scout GPT-4o feldolgozásnál: {e}\n\nNyers adatok:\n{search_context}"

    # --- UPGRADED TACTICIAN AGENT (GPT-4o Powered) ---
    def run_tactician(self, home_team, away_team):
        """ 
        Tactician Agent: Stílus elemzés GPT-4o-val. 
        """ 
        import os 
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: return "No tactical analysis."
        
        client = OpenAI(api_key=api_key)
        
        try:
            response = client.chat.completions.create( 
                model="gpt-4o", 
                messages=[ 
                    {"role": "system", "content": "You are a Tactical Analyst. Analyze the likely match dynamic based on team names. (e.g. Guardiola vs Klopp style). Predict who dominates possession. OUTPUT LANGUAGE: HUNGARIAN (MAGYAR)."}, 
                    {"role": "user", "content": f"Analyze tactical matchup in HUNGARIAN: {home_team} vs {away_team}"} 
                ] 
            ) 
            return response.choices[0].message.content
        except Exception as e:
            return f"Tactical Analysis Error: {e}"

    def run_boss(self, statistician_report, scout_report, tactician_report, match_data, lessons=None, prophet_data=None):
        """ 
        Boss Agent: QUALITY SUPERVISOR + LOGIC ENFORCER (GPT-4o). 
        Egyesíti a Próféta meglátásait a szigorú matematikával. 
        """ 
        import json 
        import re 
        import os 
        from openai import OpenAI 
    
        print("--- BOSS AGENT: TACTICAL & LOGICAL ANALYSIS ---") 
        api_key = os.getenv("OPENAI_API_KEY") 
        if not api_key: return {"main_tip": "HIBA: Nincs API Key"} 
        
        client = OpenAI(api_key=api_key) 
    
        # A Próféta ajánlásának beépítése 
        prophet_text = "" 
        if prophet_data and "recommendation" in prophet_data: 
            prophet_text = f"THE PROPHET ADVISES: {prophet_data['recommendation']} because {prophet_data.get('analysis', '')}. CONSIDER THIS SERIOUSLY." 
    
        system_prompt = """ 
        YOU ARE THE HEAD ANALYST. PREDICT THE PERFECT OUTCOME. 
        
        RULES: 
        1. LISTEN TO THE PROPHET: If the Prophet spots a tactical mismatch (e.g. Away Win), and Stats allow it, GO FOR IT. 
        2. CHECK NEWS: Injuries/Suspensions are critical. 
        3. LOGIC CHECK: 
           - If predicting 'Under 2.5', Score MUST be max 2 goals (1-0, 0-1, 1-1, 2-0, 0-2). 
           - If predicting 'Away Win', Score MUST show Away > Home (0-1, 1-2, etc.). 
        
        IMPORTANT: OUTPUT MUST BE IN HUNGARIAN LANGUAGE (Magyar).
        All values in the JSON (analysis, main_tip, value_tip) MUST BE IN HUNGARIAN.
        
        OUTPUT JSON ONLY: 
        { 
            "analysis": "Detailed reasoning including Tactics and Stats (Hungarian).", 
            "score_prediction": "X-Y", 
            "main_tip": "The Winner or Goals prediction (Hungarian)", 
            "main_tip_confidence": "XX%", 
            "value_tip": "The Prophet's insight or High Odds tip (Hungarian)", 
            "value_tip_odds": "Decimal Odds", 
            "btts_percent": "XX%", 
            "over_2_5_percent": "XX%" 
        } 
        """ 
    
        try: 
            user_prompt = f""" 
            MATCH DATA: 
            {statistician_report} 
            {scout_report} 
            {tactician_report} 
            
            {prophet_text} 
            
            RETURN PERFECT JSON. 
            """ 
    
            completion = client.chat.completions.create( 
                model="gpt-4o", 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], 
                temperature=0.2, # Precizitás 
                response_format={"type": "json_object"} 
            ) 
    
            data = json.loads(completion.choices[0].message.content) 
    
            # --- LOGIC ENFORCER (A RENDŐR - Utólagos javítás) --- 
            # Ez garantálja a Quality-t: SOHA nem lesz ellentmondás. 
            tip = data.get("main_tip", "").lower() 
            score = data.get("score_prediction", "1-1") 
            
            try: 
                nums = re.findall(r'\d+', score) 
                hg, ag = int(nums[0]), int(nums[1]) if len(nums) > 1 else (1, 1) 
                total = hg + ag 
            except: 
                hg, ag, total = 1, 1, 2 
    
            # 1. Szabály: Under/Over javítás 
            if ("under 2.5" in tip or "alatt" in tip) and total > 2: 
                data["score_prediction"] = "1-1" # Javítva 
            if ("over 2.5" in tip or "felett" in tip) and total < 3: 
                data["score_prediction"] = "2-1" # Javítva 
                
            # 2. Szabály: Győztes javítás 
            if ("home win" in tip or "hazai" in tip) and hg <= ag: 
                data["score_prediction"] = "1-0" 
            if ("away win" in tip or "vendég" in tip) and ag <= hg: 
                data["score_prediction"] = "0-1" # Ha a Próféta szerint Vendég nyer, az eredmény is az legyen!
            
            return data
        except Exception as e: 
            print(f"OPENAI ERROR: {e}") 
            return { 
                "analysis": f"Technikai hiba: {str(e)}. Statisztikai becslés következik.", 
                "score_prediction": "1-1", 
                "main_tip": "Nincs Adat", 
                "value_tip": "Nincs Adat", 
                "btts_percent": "50%" 
            }

    def run_prophet(self, stat_report, scout_report, tactician_report, match_data=None):
        """ 
        Prophet Agent: TACTICAL KILLER (GPT-4o). 
        Feladata: Megtalálni a taktikai okot, amiért a favorit kikaphat. 
        """ 
        import json 
        import os 
        from openai import OpenAI 
    
        api_key = os.getenv("OPENAI_API_KEY") 
        if not api_key: return {} 
        
        client = OpenAI(api_key=api_key) 
        
        system_prompt = """ 
        YOU ARE A CONTRARIAN PROFESSIONAL BETTOR. 
        YOUR JOB IS TO FIND THE "UPSET" (The Surprise Result). 
        
        ANALYZE THE TACTICAL MATCHUP: 
        1. IGNORE THE TABLE. Focus on Styles. 
        2. LOOK FOR MISMATCHES: 
           - Does the Away team have fast wingers against a slow Home defense? -> AWAY WIN. 
           - Is the Home team missing a key striker? -> AWAY WIN or DRAW. 
        
        IF YOU SEE A TACTICAL ADVANTAGE FOR THE UNDERDOG, RECOMMEND IT BOLDLY. 
        
        IMPORTANT: OUTPUT MUST BE IN HUNGARIAN LANGUAGE (Magyar).
        
        OUTPUT JSON: 
        { 
            "analysis": "Brief tactical reason for the tip (in Hungarian).", 
            "recommendation": "e.g. Fiorentina Win (Tactical Mismatch) (in Hungarian)", 
            "confidence": "High/Medium", 
            "estimated_odds": "e.g. 3.20" 
        } 
        """ 
    
        try: 
            user_content = f"STATS: {stat_report}\nNEWS: {scout_report}\nTACTICS: {tactician_report}" 
            
            completion = client.chat.completions.create( 
                model="gpt-4o", 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}], 
                temperature=0.4, 
                response_format={"type": "json_object"} 
            ) 
            return json.loads(completion.choices[0].message.content) 
        except: 
            return {"recommendation": "No Value"}

    def analyze_match(self, match_data, home_team_name, away_team_name, lessons=None):
        # 1. Step: Statistician
        stat_report = self.run_statistician(match_data)
        
        # 2. Step: Scout
        injuries = match_data.get('injuries', [])
        h2h = match_data.get('h2h', [])
        scout_report = self.run_scout(home_team_name, away_team_name, injuries, h2h)
        
        # 3. Step: Tactician
        tactician_report = self.run_tactician(home_team_name, away_team_name)
        
        # 4. Step: The Prophet (Value Hunter)
        prophet_report = self.run_prophet(stat_report, scout_report, tactician_report, match_data)
        
        # 5. Step: The Boss
        final_verdict = self.run_boss(stat_report, scout_report, tactician_report, match_data, lessons, prophet_report)
        
        return {
            "statistician": stat_report,
            "scout": scout_report,
            "tactician": tactician_report,
            "prophet": prophet_report,
            "boss": final_verdict
        }
