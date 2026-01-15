# ☁️ Ingyenes Weboldal Publikálása (Deployment)

Mivel a rendszer készen áll, most feltöltjük egy ingyenes, bárhonnan elérhető tárhelyre. Ehhez két lépés szükséges: **GitHub** (kód tárolása) és **Streamlit Cloud** (futtatás).

## 1. LÉPÉS: GitHub Repository Létrehozása

1.  Menj fel a [GitHub.com](https://github.com/) oldalra és jelentkezz be (vagy regisztrálj).
2.  Kattints a **New** (vagy `+`) gombra bal felül egy új repository létrehozásához.
3.  **Repository name**: Legyen mondjuk `ai-football-analyzer`.
4.  Válaszd ki: **Public** (vagy Private, de akkor a Streamlit Cloud-nak engedélyt kell adni).
5.  Ne pipálj be semmit (se README, se .gitignore), mert ezeket már létrehoztuk!
6.  Kattints a **Create repository** gombra.
7.  A megjelenő oldalon másold ki a HTTPS linket (pl. `https://github.com/FELHASZNALONEV/ai-football-analyzer.git`).

## 2. LÉPÉS: Kód Feltöltése (Ezt a gépeden kell futtatni)

Már előkészítettem a git repository-t a gépeden. Nyiss egy terminált a mappában, és futtasd le ezeket a parancsokat (a saját GitHub linkeddel!):

```bash
git remote add origin https://github.com/TE_NEVED/ai-football-analyzer.git
git branch -M main
git push -u origin main
```

*(Ha kéri a GitHub jelszót, és nem fogadja el, használnod kell egy Personal Access Token-t vagy a GitHub Desktop alkalmazást).*

## 3. LÉPÉS: Streamlit Cloud Beállítása (Az ingyenes weboldal)

1.  Nyisd meg: [share.streamlit.io](https://share.streamlit.io/)
2.  Jelentkezz be a GitHub fiókoddal ("Continue with GitHub").
3.  Kattints a **New app** gombra.
4.  Válaszd ki a **Use existing repo** opciót.
5.  Válaszd ki a repository-t: `TE_NEVED/ai-football-analyzer`.
6.  **Main file path**: `app.py`.
7.  Kattints a **Deploy!** gombra.

## 4. LÉPÉS: Kulcsok Megadása (FONTOS!)

A weboldal elindítása után hibát fog dobni ("App needs secrets"), mert a felhőben még nincsenek meg az API kulcsok.

1.  A Streamlit Cloud felületén (jobb alsó sarok) kattints a `Manage app` gombra, vagy a `Settings` menüben a `Secrets` pontra.
2.  Másold be az alábbi tartalmat a szerkesztőbe:

```toml
RAPIDAPI_KEY = "IDE_ÍRD_A_RAPIDAPI_KULCSODAT"
GROQ_API_KEY = "IDE_ÍRD_A_GROQ_KULCSODAT"
APP_PASSWORD = "admin123"
```

3.  Kattints a **Save** gombra.
4.  Az alkalmazás automatikusan újraindul, és innentől kezdve bárhonnan (mobilról is) elérhető lesz a generált linken! 🚀
