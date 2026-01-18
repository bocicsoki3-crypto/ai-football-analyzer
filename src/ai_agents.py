from src.tools import get_rapid_stats
import os
import time
import re
import json
import traceback
from groq import Groq
from tavily import TavilyClient
from datetime import datetime

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

    def run_statistician(self, home_team, away_team):
        """ 
        Statistician Agent: RAPIDAPI VERSION. 
        Közvetlenül az API-ból kéri le a tényeket, nem AI generálja. 
        """ 
        print(f"--- STATISTICIAN: Fetching RapidAPI data for {home_team} vs {away_team} ---") 
        try: 
            # Itt hívjuk meg a Tools-ban lévő függvényt! 
            return get_rapid_stats(home_team, away_team) 
        except Exception as e: 
            return f"Error fetching RapidAPI stats: {str(e)}"

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

    def _load_lessons(self):
        try:
            if os.path.exists("lessons.json"):
                with open("lessons.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except:
            return []

    def run_boss(self, statistician_report, scout_report, tactician_report, match_data, lessons=None, prophet_data=None):
        """ 
        Boss Agent: EVIDENCE BASED EDITION (GPT-4o). 
        Kényszerítjük az AI-t, hogy használja a RapidAPI adatait a döntéshez. 
        """ 
        import json 
        import re 
        import os 
        from openai import OpenAI 
    
        print("--- BOSS AGENT: TACTICAL & LOGICAL ANALYSIS ---") 
        api_key = os.getenv("OPENAI_API_KEY") 
        if not api_key: return {"main_tip": "HIBA: Nincs API Key"} 
        
        client = OpenAI(api_key=api_key) 

        # 1. Leckék betöltése (Ha nincs átadva, betölti a fájlból)
        lessons_list = lessons if lessons else self._load_lessons()
        
        # Leckék formázása szöveggé
        lessons_text = "NO PREVIOUS LESSONS."
        if lessons_list:
            lessons_text = "!!! IMPORTANT LESSONS FROM PAST MISTAKES !!!\n"
            for lesson in lessons_list[-5:]: # Csak az utolsó 5 legfrissebb leckét vesszük figyelembe
                lessons_text += f"- {lesson}\n"
    
        # A Próféta ajánlásának beépítése 
        prophet_text = "" 
        if prophet_data and "recommendation" in prophet_data: 
            prophet_text = f"PROPHET'S ADVICE: {prophet_data['recommendation']} (Reason: {prophet_data.get('analysis','')})" 
    
        system_prompt = f""" 
        YOU ARE A DATA-DRIVEN FOOTBALL ANALYST. NOT A FAN. 
        INPUT DATA SOURCE: OFFICIAL API STATS (TRUST THIS 100%). 
        
        =================================================== 
        YOUR MEMORY (DO NOT REPEAT THESE MISTAKES): 
        {lessons_text} 
        ===================================================

        PROTOCOL BEFORE TIPPING: 
        
        1. COMPARE FORM: Look at the last 5 games in 'stat_report'. Who scored more goals? 
        2. COMPARE H2H: Who won the last 3 meetings? 
        3. CHECK SQUAD: Are key players injured in 'scout_report'? 
        4. APPLY LESSONS: Use the memory above to avoid past errors.

        CRITICAL RULE: 
        
        - If API Data says Team B is in better form (more wins/goals), you CANNOT bet on Team A just because they are "historically" good. 
        - If API Data shows a close match, USE "Double Chance" (1X or X2) instead of strict Win. 
        - NO BET POLICY: If data is missing or confidence < 70%, OUTPUT "NO BET".
        
        IMPORTANT: OUTPUT MUST BE IN HUNGARIAN LANGUAGE (Magyar).
        All values in the JSON (analysis, main_tip, value_tip, evidence) MUST BE IN HUNGARIAN.

        OUTPUT JSON STRUCTURE: 
        {{ 
            "evidence": "WRITE HERE THE EXACT STATS YOU USED (e.g. 'Away team scored 12 goals in last 5 games vs Home team 3 goals') (Hungarian).", 
            "analysis": "Based on the evidence above... (Hungarian)", 
            "score_prediction": "X-Y", 
            "main_tip": "The Tip", 
            "main_tip_confidence": "XX%", 
            "value_tip": "High Odds Tip", 
            "value_tip_odds": "Decimal Odds",
            "btts_percent": "XX%", 
            "over_2_5_percent": "XX%" 
        }} 
        """ 
    
        try: 
            user_prompt = f""" 
            OFFICIAL API STATS: 
            {statistician_report} 
            TEAM NEWS (Injuries/Lineups): {scout_report} 
            
            TACTICAL ANALYSIS: {tactician_report} 
            
            {prophet_text} 
            
            TASK: Analyze the API STATS first. If the stats contradict the favorite, BET ON THE UNDERDOG or DRAW. 
            """ 
    
            completion = client.chat.completions.create( 
                model="gpt-4o", 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], 
                temperature=0.2, # Nagyon alacsony, hogy ragaszkodjon a tényekhez 
                response_format={"type": "json_object"} 
            ) 
    
            data = json.loads(completion.choices[0].message.content) 
    
            # --- LOGIC ENFORCER (A RENDŐR - Utólagos javítás) --- 
            # Ez garantálja a Quality-t: SOHA nem lesz ellentmondás. 
            tip = data.get("main_tip", "").lower() 
            
            # Skip logic enforcement if NO BET
            if "no bet" in tip or "kihagyva" in tip:
                data["score_prediction"] = "SKIP"
                return data

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
            if ("draw" in tip or "döntetlen" in tip) and hg != ag: 
                data["score_prediction"] = "1-1" # Javítva

            return data
        except Exception as e: 
            print(f"OPENAI ERROR: {e}") 
            return { 
                "analysis": f"Technikai hiba: {str(e)}. Statisztikai becslés következik.", 
                "score_prediction": "1-1", 
                "main_tip": "NO BET (Error)", 
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
        
        # 1. Statisztikus (JSON-t kapunk vissza stringként) 
        stat_json_str = self.run_statistician(home_team_name, away_team_name) 
        
        # Kibontjuk a szöveges jelentést a többi ügynöknek 
        try: 
            stat_data = json.loads(stat_json_str) 
            stat_text_report = stat_data.get("analysis", "No Data") 
        except: 
            stat_text_report = stat_json_str # Fallback 

        # 2. Scout 
        injuries = match_data.get('injuries', []) 
        h2h = match_data.get('h2h', []) 
        scout_report = self.run_scout(home_team_name, away_team_name, injuries, h2h) 
        
        # 3. Tactician 
        tactician_report = self.run_tactician(home_team_name, away_team_name) 
        
        # 4. Prophet (A szöveges jelentést kapja!) 
        prophet_report = self.run_prophet(stat_text_report, scout_report, tactician_report, match_data) 
        
        # 5. Boss (A szöveges jelentést kapja!) 
        final_verdict = self.run_boss(stat_text_report, scout_report, tactician_report, match_data, lessons, prophet_report) 
        
        # KÖZÖS VISSZATÉRÉS: 
        # A 'statistician' kulcsba most a JSON STRINGET tesszük, hogy a UI fel tudja dolgozni! 
        return { 
            "statistician": stat_json_str, 
            "scout": scout_report, 
            "tactician": tactician_report, 
            "prophet": prophet_report, 
            "boss": final_verdict 
        }
