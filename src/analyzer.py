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
    You are an elite sports betting analyst using GPT-4o. 
    Your task is to DEEPLY ANALYZE the provided match statistics (from PDF context) and generate high-accuracy predictions.
    
    CRITICAL INSTRUCTION:
    - Do NOT just extract data. You must SYNTHESIZE it.
    - Look for correlations (e.g., "High pressing team vs. team susceptible to counters").
    - Weight factors: Recent form > H2H > Motivation > Missing Players.
    - If data is missing in the PDF, make a reasonable inference based on the context provided or state "Insufficient Data" for that specific market, but try to provide a prediction if possible.
    
    MATCH CONTEXT:
    - Analyze the raw stats provided in the PDF text.
    - Focus on: xG, H2H, recent form, goals scored/conceded, injuries, tactical matchups.
    
    REQUIRED OUTPUT FORMAT (JSON ONLY):
    You must return a JSON object with a list of predictions sorted by 'confidence' (descending).
    
    Keys required for each prediction type:
    - "market": The betting market (e.g., "Over 1.5 Goals", "BTTS Yes", "Asian Handicap -0.5").
    - "prediction": The specific outcome (e.g., "Over", "Yes", "Home -0.5").
    - "probability": Estimated probability percentage (0-100).
    - "confidence": Your confidence score (0-100) based on data strength and analysis depth.
    - "reasoning": A sharp, analytical explanation (1-2 sentences) citing specific evidence from the PDF (e.g., "Home team averages 2.5 xG at home, while Away team is missing key defender X").
    
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
