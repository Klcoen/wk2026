# WK Speelschema 2026 — voor de echte voetballiefhebber (live dashboard)

Live dashboard van het WK 2026, verdeeld over drie tabbladen:
- **Wedstrijden** — de laatste 4 gespeelde en de 4 eerstvolgende wedstrijden, met
  lopende duels (uitslag/tussenstand) ertussen.
- **Groepen** — de groepsstanden + wie doorgaat naar de laatste 32 (nrs 1 & 2 +
  8 beste nummers 3).
- **Knockout fase** — een volledig **knock-outschema t/m de finale**. De Laatste 32
  (M73–M88) wordt op basis van de huidige stand ingevuld; vanaf de achtste finale
  (M89–M104) staat het bracket met match-nummers, de doorstroming ("Winnaar M74")
  en per feeder de **mogelijke landen**.

Alle tijden in NL-tijd en landnamen in het Nederlands.

**Live link:** https://klcoen.github.io/wk2026/

## Hoe het werkt
- `wk_update_v15.py` haalt standen + wedstrijden op bij football-data.org en
  genereert `wk_dashboard.html` (alleen Python-standaardbibliotheek, geen pip).
- Een GitHub Actions-workflow (`.github/workflows/update.yml`) genereert het dashboard
  opnieuw en publiceert het via GitHub Pages. GitHubs eigen `schedule`-cron vuurt voor
  deze repo niet, dus het verversen gebeurt via een **externe cron-job** (cron-job.org)
  die de workflow elke ~2 min aanroept — zie **`PINGER_SETUP.md`**.
- Het API-token zit **niet** in de repo, maar als versleuteld repo-secret
  `FOOTBALL_DATA_TOKEN` (Settings → Secrets and variables → Actions).
- De pagina ververst zichzelf elke 90 seconden in de browser, zodat de stand
  bijna live meeloopt.

## Zelf draaien (lokaal)
Zet je football-data.org-token in `wk_config.txt` of in de omgevingsvariabele
`FOOTBALL_DATA_TOKEN` en draai `python wk_update_v15.py`.
