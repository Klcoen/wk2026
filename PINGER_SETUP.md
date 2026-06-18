# Live-dashboard automatisch laten verversen (cron-job.org)

GitHub's eigen `schedule`-cron vuurt voor deze repo niet (0 runs). Daarom verversen
we via een **externe cron-job** die elke 15 min de GitHub-workflow aanroept. Volledig
cloud; je pc hoeft niet aan. Eénmalig instellen (~5 min), twee stappen.

---

## Stap 1 — GitHub-token (fine-grained PAT)

1. Ga naar **https://github.com/settings/personal-access-tokens/new**
2. Vul in:
   - **Token name:** `wk2026-pinger`
   - **Expiration:** tot na het WK (bv. 31 juli 2026)
   - **Repository access:** *Only select repositories* → **Klcoen/wk2026**
   - **Permissions** → *Repository permissions* → **Actions: Read and write**
     (verder niets)
3. **Generate token** → **kopieer** de token (`github_pat_...`). Je ziet 'm één keer.

> De token mag alleen Actions starten op deze ene repo — minimaal risico.

---

## Stap 2 — Cron-job op cron-job.org

1. Gratis account op **https://cron-job.org** → inloggen.
2. **Create cronjob**:

   | Veld | Waarde |
   |---|---|
   | **Title** | `WK2026 update` |
   | **URL** | `https://api.github.com/repos/Klcoen/wk2026/actions/workflows/update.yml/dispatches` |
   | **Schedule** | Every 15 minutes |
   | **Request method** | `POST` |

3. Tabblad **Advanced / Headers** → voeg toe:

   ```
   Accept: application/vnd.github+json
   Authorization: Bearer github_pat_PLAK_HIER_JE_TOKEN
   X-GitHub-Api-Version: 2022-11-28
   User-Agent: wk2026-pinger
   ```

4. **Request body** (Custom body):

   ```json
   {"ref":"main"}
   ```

5. **Save**.

---

## Controleren
- cron-job.org toont per run **HTTP 204** = gelukt.
- GitHub → **Actions**-tab: elke ~15 min een run met trigger *workflow_dispatch*.
- Op **https://klcoen.github.io/wk2026/** loopt de tijd bij "Stand van" mee.

## Token verlopen? 
Maak een nieuwe (stap 1) en vervang de `Authorization`-header in de cron-job.
