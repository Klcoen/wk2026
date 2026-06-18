# Live-dashboard automatisch laten verversen (zonder PC)

GitHub's eigen cron (`schedule`) vuurt voor deze repo niet betrouwbaar — daarom
verversen we het live-dashboard met een **externe pinger** die elke 5 minuten de
GitHub-workflow aanroept. Dit draait volledig in de cloud; je pc hoeft niet aan.

Eénmalig instellen (~5 min). Twee stappen.

---

## Stap 1 — Maak een GitHub-token (fine-grained PAT)

1. Ga naar **https://github.com/settings/personal-access-tokens/new**
2. Vul in:
   - **Token name:** `wk2026-pinger`
   - **Expiration:** bv. 60 dagen (of "tot na het WK", 19 juli 2026)
   - **Repository access:** *Only select repositories* → kies **Klcoen/wk2026**
   - **Permissions** → *Repository permissions* → **Actions: Read and write**
     (verder niets aanvinken)
3. Klik **Generate token** en **kopieer** de token (begint met `github_pat_...`).
   Je ziet 'm maar één keer.

> Deze token mag álleen Actions starten op deze ene repo — minimaal risico.

---

## Stap 2 — Maak een gratis pinger op cron-job.org

1. Maak een gratis account op **https://cron-job.org** en log in.
2. **Create cronjob** en vul in:

   | Veld | Waarde |
   |---|---|
   | **Title** | `WK2026 update` |
   | **URL** | `https://api.github.com/repos/Klcoen/wk2026/actions/workflows/update.yml/dispatches` |
   | **Schedule** | Every 5 minutes (`*/5`) — of "Every 5 minutes" in de UI |
   | **Request method** | `POST` |

3. Open het tabblad **Advanced / Headers** en voeg toe:

   ```
   Accept: application/vnd.github+json
   Authorization: Bearer github_pat_D0UW_HIER_JE_TOKEN
   X-GitHub-Api-Version: 2022-11-28
   User-Agent: wk2026-pinger
   ```

4. Bij **Request body** (of "Custom body"):

   ```json
   {"ref":"main"}
   ```

5. **Save**. Klaar.

---

## Controleren of het werkt

- In cron-job.org: de job moet **HTTP 204** teruggeven (dat is "gelukt, geen inhoud").
- In GitHub: **Actions**-tab → je ziet elke ~5 min een nieuwe run met trigger
  *workflow_dispatch*.
- Op **https://klcoen.github.io/wk2026/** loopt de tijd bij "Stand van" elke ~5 min mee.

## Token verlengd/verlopen?
Maak een nieuwe token (stap 1) en vervang de `Authorization`-header in de cron-job.

## Waarom niet GitHub's eigen cron?
Die staat nog als best-effort backup in `.github/workflows/update.yml`
(`cron: 3-59/5`), maar GitHub knijpt korte crons af en vuurde hier 0 keer in 2 uur.
De pinger is de betrouwbare trigger.
