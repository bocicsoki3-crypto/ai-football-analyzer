import os
import json
from openai import OpenAI

def analyze_match_with_gpt4(pdf_text, match_name, rapid_stats=None):
    """
    Sends PDF text and RapidAPI stats to GPT-4o for analysis.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "Missing OpenAI API Key"}

    client = OpenAI(api_key=api_key)

    system_prompt = """
    You are an elite sports betting analyst using GPT-4o. 
    Your task is to analyze the provided match statistics (Official Data + PDF Context) and generate high-accuracy predictions.
    
    DATA SOURCES:
    1. OFFICIAL RAPIDAPI STATS (Form, H2H, Probabilities) - High Reliability
    2. PDF DOCUMENT (Scout Report / News) - Contextual Info
    
    If RapidAPI stats contradict the PDF, trust the RapidAPI stats for raw numbers (goals, results).
    
    MATCH CONTEXT:
    - Analyze the raw stats provided.
    - Focus on: xG, H2H, recent form, goals scored/conceded.
    
    REQUIRED OUTPUT FORMAT (JSON ONLY):
    You must return a JSON object with a list of predictions sorted by 'confidence' (descending).
    
    Keys required for each prediction type:
    - "market": The betting market (e.g., "Over 1.5 Goals", "BTTS Yes", "Asian Handicap -0.5").
    - "prediction": The specific outcome (e.g., "Over", "Yes", "Home -0.5").
    - "probability": Estimated probability percentage (0-100).
    - "confidence": Your confidence score (0-100) based on data strength.
    - "reasoning": A short, sharp explanation (max 1 sentence).
    
    MANDATORY MARKETS TO ANALYZE:
    1. Over/Under 1.5 Goals
    2. Over/Under 2.5 Goals
    3. Asian Handicap (Choose the most likely line)
    4. BTTS (Both Teams to Score) - Yes/No
    5. Draw No Bet (DNB)
    6. Double Chance (1X, X2, 12)
    
    Output strictly valid JSON. No markdown formatting.
    """

    user_prompt = f"""
    MATCH: {match_name}
    
    OFFICIAL DATA (RAPIDAPI):
    {rapid_stats if rapid_stats else "No Official Data Available"}
    
    ADDITIONAL CONTEXT (PDF):
    {pdf_text[:10000]}  # Limit text length to avoid token limits if PDF is huge
    
    Analyze this data and provide the JSON output sorted by confidence.
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
