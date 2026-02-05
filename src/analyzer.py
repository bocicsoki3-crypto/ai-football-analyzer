import os
import json
from openai import OpenAI

def analyze_match_with_gpt4(pdf_text, match_name):
    """
    Sends PDF text to GPT-4o for DEEP analysis and returns structured JSON.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "Missing OpenAI API Key"}

    client = OpenAI(api_key=api_key)

    system_prompt = """
    Te egy elit sportfogadási elemző vagy, aki a GPT-4o modellt használja.
    A feladatod a megadott mérkőzésstatisztikák (PDF kontextus és hivatalos adatok) MÉLYREHATÓ ELEMZÉSE és nagy pontosságú előrejelzések generálása.
    
    KRITIKUS UTASÍTÁS (NYELV ÉS STÍLUS):
    - A válaszadás nyelve KIZÁRÓLAG MAGYAR legyen.
    - Légy szakmai, tárgyilagos, de részletes.
    - NE csak adatokat másolj ki. SZINTETIZÁLD őket.
    - Keress összefüggéseket (pl. "Magasan letámadó csapat vs. kontrákra építő csapat").
    - Súlyozd a tényezőket: Jelenlegi forma > Egymás elleni (H2H) > Motiváció > Hiányzók.
    
    ADATFORRÁSOK ÉS PRIORITÁS:
    1. HIVATALOS RAPIDAPI STATISZTIKÁK (Forma, H2H) - Ha elérhető, ez a legpontosabb.
    2. PDF DOKUMENTUM (Scout jelentés / Hírek) - Kontextuális infók (sérültek, nyilatkozatok).
    
    Ha a RapidAPI és a PDF ellentmond, a számadatokban (gólok, eredmények) a RapidAPI-nak higgy.
    
    ELVÁRT KIMENETI FORMÁTUM (CSAK JSON):
    Egy JSON objektumot kell visszaadnod, amely tartalmazza az előrejelzések listáját 'predictions' kulcs alatt, 'confidence' (magabiztosság) szerint csökkenő sorrendben.
    
    Szükséges kulcsok minden előrejelzéshez:
    - "market": A fogadási piac magyarul (pl. "1.5 Gól Felett", "Mindkét Csapat Szerez Gólt", "Ázsiai Hendikep -0.5").
    - "prediction": A konkrét tipp (pl. "Felett", "Igen", "Hazai -0.5").
    - "probability": Becsült valószínűség százalékban (0-100).
    - "confidence": A te magabiztosságod (0-100) az adatok erőssége és az elemzés mélysége alapján.
    - "reasoning": RÉSZLETES, mélyreható elemzés (3-4 mondat). Hivatkozz konkrét adatokra a PDF-ből vagy a statisztikákból (pl. "A Hazai csapat xG átlaga otthon 2.5, míg a Vendég csapat kulcsfontosságú védője, X hiányzik, ami növeli a gólok esélyét."). Térj ki a motivációra és a formára is.
    
    KÖTELEZŐEN ELEMZENDŐ PIACOK:
    1. 1.5 Gól Alatt/Felett (Over/Under 1.5 Goals)
    2. 2.5 Gól Alatt/Felett (Over/Under 2.5 Goals)
    3. Ázsiai Hendikep (Válaszd ki a legvalószínűbb határt)
    4. Mindkét Csapat Szerez Gólt (BTTS) - Igen/Nem
    5. Nincs Fogadás Döntetlenre (DNB - Draw No Bet)
    6. Dupla Esély (1X, X2, 12)
    7. 1X2 (Végeredmény)
    
    Kimenet szigorúan érvényes JSON legyen. Markdown formázás nélkül.
    """

    user_prompt = f"""
    MATCH: {match_name}
    
    FULL MATCH CONTEXT (FROM PDF):
    {pdf_text[:15000]}  # Increased limit for deeper context
    
    Analyze this data deeply and provide the JSON output sorted by confidence.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}
