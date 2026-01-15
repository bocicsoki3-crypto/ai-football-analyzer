# AI Committee Football Analyzer Pro ⚽

Professzionális futball-elemző szoftver, amely AI ügynökök (Groq, Gemini) segítségével, adatvezérelt módon keres Value Betting lehetőségeket.

## 🚀 Telepítés és Futtatás (Lokálisan)

1. **Klónozd a repót:**
   ```bash
   git clone https://github.com/FELHASZNALONEV/ai-football-analyzer.git
   cd ai-football-analyzer
   ```

2. **Telepítsd a függőségeket:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Indítsd el az alkalmazást:**
   ```bash
   streamlit run app.py
   ```

## ☁️ Telepítés Streamlit Cloud-ra (Mobil elérés)

1. **Töltsd fel a kódot GitHub-ra:**
   - Hozz létre egy új repository-t GitHub-on.
   - Töltsd fel a fájlokat (`app.py`, `requirements.txt`, `src/` mappa).

2. **Regisztrálj a Streamlit Cloud-ra:**
   - Menj a [share.streamlit.io](https://share.streamlit.io/) oldalra.
   - Jelentkezz be a GitHub fiókoddal.

3. **Deploy:**
   - Kattints a "New app" gombra.
   - Válaszd ki a GitHub repót.
   - Main file path: `app.py`.
   - Kattints a "Deploy!" gombra.

4. **Titkos kulcsok beállítása (Secrets):**
   - A Streamlit Dashboard-on az app mellett kattints a `...` (Menü) -> `Settings` -> `Secrets` pontra.
   - Másold be a következőket (a saját kulcsaiddal):
     ```toml
     RAPIDAPI_KEY = "ide_írd_a_kulcsot"
     GEMINI_API_KEY = "ide_írd_a_kulcsot"
     GROQ_API_KEY = "ide_írd_a_kulcsot"
     APP_PASSWORD = "saját_jelszó"
     ```

## 🤖 Működés (A Bizottság)

- **Statisztikus (Groq)**: Poisson-eloszlás és matematikai valószínűségek.
- **Hírszerző (Gemini)**: Sérültek és hírek felkutatása.
- **Taktikus (Groq)**: Stíluselemzés.
- **A Főnök (Gemini)**: Végső döntéshozatal és tanulás a korábbi hibákból.

## 📱 Mobil Nézet
Az alkalmazás reszponzív, így mobilböngészőből is tökéletesen használható a generált linken keresztül.
