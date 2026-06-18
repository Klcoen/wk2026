# WK 2026 — Wie gaat door? (live dashboard)

Live dashboard van het WK 2026: groepsstanden, wie doorgaat naar de laatste 32
(nrs 1 & 2 + 8 beste nummers 3), wedstrijdtijden (NL-tijd) en een knock-outschema
waarvan de Laatste 32 op basis van de huidige stand wordt ingevuld.

**Live link:** zie de GitHub Pages-URL onder *Settings → Pages* (verschijnt na de
eerste workflow-run), bijv. `https://klcoen.github.io/wk2026/`.

## Hoe het werkt
- `wk_update_v8.py` haalt standen + wedstrijden op bij football-data.org en
  genereert `wk_dashboard.html` (alleen Python-standaardbibliotheek, geen pip).
- Een GitHub Actions-workflow (`.github/workflows/update.yml`) genereert het dashboard
  opnieuw en publiceert het via GitHub Pages. GitHubs eigen `schedule`-cron vuurt voor
  deze repo niet, dus het verversen gebeurt via een **externe cron-job** (cron-job.org)
  die de workflow elke 15 min aanroept — zie **`PINGER_SETUP.md`**. (Geen live-bijhouden;
  bewust simpel gehouden.)
- Het API-token zit **niet** in de repo, maar als versleuteld repo-secret
  `FOOTBALL_DATA_TOKEN` (Settings → Secrets and variables → Actions).
- De pagina ververst zichzelf elke 2 minuten in de browser.

## Zelf draaien (lokaal)
Zet je football-data.org-token in `wk_config.txt` of in de omgevingsvariabele
`FOOTBALL_DATA_TOKEN` en draai `python wk_update_v8.py`.
