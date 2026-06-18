# WK 2026 — Wie gaat door? (live dashboard)

Live dashboard van het WK 2026: groepsstanden, wie doorgaat naar de laatste 32
(nrs 1 & 2 + 8 beste nummers 3), wedstrijdtijden (NL-tijd) en een knock-outschema
waarvan de Laatste 32 op basis van de huidige stand wordt ingevuld.

**Live link:** zie de GitHub Pages-URL onder *Settings → Pages* (verschijnt na de
eerste workflow-run), bijv. `https://klcoen.github.io/wk2026/`.

## Hoe het werkt
- `wk_update_v7.py` haalt standen + wedstrijden op bij football-data.org en
  genereert `wk_dashboard.html` (alleen Python-standaardbibliotheek, geen pip).
- Een GitHub Actions-workflow (`.github/workflows/update.yml`) draait **1x per uur**
  in de cloud, genereert het dashboard opnieuw en publiceert het via GitHub Pages.
  Een wedstrijd duurt ~2 uur, dus de stand staat binnen een uur na het eindsignaal bij.
  (Geen live-bijhouden; dat is bewust simpel gehouden.)
- Het API-token zit **niet** in de repo, maar als versleuteld repo-secret
  `FOOTBALL_DATA_TOKEN` (Settings → Secrets and variables → Actions).
- De pagina ververst zichzelf elke 2 minuten in de browser.

## Zelf draaien (lokaal)
Zet je football-data.org-token in `wk_config.txt` of in de omgevingsvariabele
`FOOTBALL_DATA_TOKEN` en draai `python wk_update_v7.py`.
