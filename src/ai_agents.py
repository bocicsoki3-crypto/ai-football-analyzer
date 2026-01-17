import os
import time
from groq import Groq
import json
import ollama
from tavily import TavilyClient
from mistralai import Mistral
import google.generativeai as genai
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
        Executes Gemini generation with Smart Retry logic for 429 errors.
        Retries up to 3 times with 30s delay if Quota Exceeded.
        """
        max_retries = 3
        retry_delay = 30

        for attempt in range(max_retries + 1):
            try:
                return self.gemini_model.generate_content(prompt).text
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Quota" in error_msg or "quota" in error_msg or "Resource has been exhausted" in error_msg:
                    if attempt < max_retries:
                        print(f"⚠️ Túl gyors tempó! (429 Quota Exceeded). Pihenő {retry_delay} másodpercig... ({attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise e # Max retries reached
                else:
                    raise e # Not a quota error

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

    def run_scout(self, home_team, away_team, injuries, h2h, referee=None, venue=None, match_date=None):
        self._setup_clients()
        
        search_context = ""
        sources_used = []
        
        # Tavily Search Integration
        if self.tavily_client:
            try:
                # Use current date if not provided
                if not match_date:
                    match_date = datetime.now().strftime("%Y-%m-%d")

                # Kiterjesztett keresés: Angol nyelven a jobb találatokért
                query = f"{home_team} vs {away_team} preview injuries lineup news {match_date} site:fbref.com OR site:whoscored.com"
                
                search_result = self.tavily_client.search(query, search_depth="advanced", max_results=7)
                
                context_parts = []
                if 'results' in search_result:
                    for res in search_result['results']:
                        context_parts.append(f"Forrás: {res['url']}\nTartalom: {res['content']}")
                        sources_used.append(res['url'])
                
                search_context = "\n\n".join(context_parts)
            except Exception as e:
                search_context = f"Hiba a Tavily keresésnél: {str(e)}"

        if not self.gemini_model and not self.groq_client:
            return f"API Key hiányzik (Google vagy Groq). (Tavily infó: {len(sources_used)} forrás)"
            
        prompt = f"""
        TE VAGY A HÍRSZERZŐ (Gemini 2.0 Flash). Egy oknyomozó sportújságíró.
        
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
            # Priority: Gemini 2.0 Flash
            if self.gemini_model:
                return self._generate_with_retry(prompt)
                
            # Fallback: Groq
            if self.groq_client:
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
        
        # Check if we have at least one capable client
        if not self.gemini_model and not self.mistral_client and not self.groq_client:
            return "Hiányzó API kulcsok (GOOGLE_API_KEY, MISTRAL_API_KEY vagy GROQ_API_KEY)."
            
        lessons_text = ""
        if lessons:
            lessons_text = "\n".join(lessons)
            
        h2h_data = match_data.get('h2h', [])
        standings_data = match_data.get('standings', [])
        injuries_data = match_data.get('injuries', [])
        home_stats = match_data.get('home_team', {})
        away_stats = match_data.get('away_team', {})
        computed_stats = match_data.get('computed_stats', {})

        prompt = f"""
        TE VAGY A FŐNÖK (Gemini 2.0 Flash). A "Keresztapa" a sportfogadásban.
        
        KORÁBBI HIBÁK ÉS TANULSÁGOK (VISSZACSATOLÁS):
        {lessons_text}
        
        UTASÍTÁS: KÖTELEZŐEN olvasd el a fenti tanulságokat! Ha egy korábbi tipp nem jött be hasonló szituációban, most dönts máshogy!
        
        LOGIKAI LÁNC (KÖTELEZŐ):
        A döntésed alapja egy szintézis legyen:
        1. VIZSGÁLD MEG a Hírszerző jelentését (Tavily által gyűjtött friss hírek: Fbref, Footystats, sérülések, motiváció).
        2. VESD ÖSSZE ezt a Statisztikus jelentésével (Llama 3.3 által számolt matematikai valószínűségek).
        3. Ha a hírek (pl. kulcsjátékos hiánya) ellentmondanak a mateknak, a hírek döntsenek!
        4. KÖTELEZŐEN vedd figyelembe a h2h_data változó tartalmát is a döntésnél!
        5. KÖTELEZŐEN vizsgáld meg a TABELLA (standings) helyezéseket és a motivációt!
        6. KÖTELEZŐEN nézd át a SÉRÜLTEK (injuries) listáját és súlyozd a hiányzók fontosságát!
        7. KÖTELEZŐEN elemezd a CSAPAT STATISZTIKÁKAT (home/away_stats) és a SPECIFIKUS ÁTLAGOKAT (computed_stats)!
        
        BEMENETEK:
        1. STATISZTIKUS JELENTÉSE (Matek & Valószínűségek): {statistician_report}
        2. HÍRSZERZŐ JELENTÉSE (Hírek, Motiváció, Oddsok): {scout_report}
        3. TAKTIKUS JELENTÉSE (Játék képe): {tactician_report}
        4. MECCS ADATOK (Teljes nyers adat): {json.dumps(match_data)}
        5. H2H ADATOK (h2h_data): {json.dumps(h2h_data)}
        6. TABELLA (standings_data): {json.dumps(standings_data)}
        7. SÉRÜLTEK (injuries_data): {json.dumps(injuries_data)}
        8. HAZAI CSAPAT STATOK (home_stats): {json.dumps(home_stats)}
        9. VENDÉG CSAPAT STATOK (away_stats): {json.dumps(away_stats)}
        10. SPECIFIKUS ÁTLAGOK (computed_stats): {json.dumps(computed_stats)}
        
        FELADAT:
        Ne csak 1X2-ben gondolkodj! Értékeld ki a BTTS (Mindkét csapat lő gólt) és az Over/Under 2.5 piacokat is!
        
        LÉPÉSEK:
        1. Határozd meg a saját belső valószínűségedet (%) mindhárom fő piacra:
           - 1X2 (Hazai / Döntetlen / Vendég)
           - BTTS (Igen / Nem)
           - Over/Under 2.5 (Alatta / Felette)
        2. Vesd össze a Hírszerző által talált (vagy általad becsült) piaci oddsokkal.
        3. Válassz FŐ TIPPET és VALUE TIPPET.
        
        TIPP KATEGÓRIÁK:
        - FŐ TIPP: Az a kimenetel, aminek a legmagasabb a bekövetkezési valószínűsége (pl. "Over 2.5" ha 75%-ra teszed). Ez a "Biztonsági Tipp".
        - VALUE TIPP: Az a piac, ahol a te valószínűséged szignifikánsan (min. 5-10%) magasabb, mint amit az odds sugall. (Képlet: Te% > (1/Odds) + 0.05). Ha nincs ilyen, írd: "Nincs kiemelkedő value".
        
        KIMENETI FORMÁTUM (Szigorúan ezt kövesd):
        
        **RÖVID ELEMZÉS**: [3-4 mondat. Indokold meg a választást a számok és a hírek alapján!]
        
        **PONTOS VÉGEREDMÉNY TIPP**: [CSAK A SZÁM! pl. 2-1]
        
        **FŐ TIPP**: [Piac és Kimenetel] (Esély: XX%)
        
        **VALUE TIPP**: [Piac és Kimenetel] @ [Odds] (Value: XX%) [VAGY "Nincs kiemelkedő value"]
        """
        
        self.last_prompts['boss'] = prompt
        
        try:
            # Priority 1: Gemini 2.0 Flash
            if self.gemini_model:
                return self._generate_with_retry(prompt)
                
            # Priority 2: Mistral Large 2
            elif self.mistral_client:
                completion = self.mistral_client.chat.complete(
                    model="mistral-large-latest",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                return completion.choices[0].message.content
                
            # Fallback: Groq (Llama 3 - Versatile)
            elif self.groq_client:
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
