import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("Nincs GOOGLE_API_KEY a .env fájlban!")
    exit()

genai.configure(api_key=api_key)

print("Elérhető Gemini modellek:")
try:
    for m in genai.list_models():
        if 'gemini' in m.name:
            print(f"- {m.name}")
except Exception as e:
    print(f"Hiba a modellek listázásakor: {e}")
