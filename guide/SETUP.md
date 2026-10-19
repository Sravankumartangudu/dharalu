# Setup

About 10 minutes, one time. When you're done, your Mac checks wheat, gold, silver and platinum every 5 minutes and publishes to GitHub Pages (step 8), GitHub runs a backup twice a day for free, and the dashboard updates automatically.

## 1. Prerequisites

- A **GitHub account** (free). Public repositories get GitHub Actions and Pages for free.
- A **data.gov.in API key** (free, recommended).
- Optional: **Telegram** for alerts, an **Anthropic API key** for the AI briefing, and a **Mac** (macOS 13+) for the menu-bar app.

## 2. Get your own copy

Open https://github.com/Sravankumartangudu/dharalu and click **Fork**. If you own the repository already, skip this step.

## 3. Get a data.gov.in key

1. Sign up at https://data.gov.in (top right → *Login / Register*).
2. Open *My Account → API Keys* and copy the key.
3. In your repository: *Settings → Secrets and variables → Actions → New repository secret*.
   - Name: `DATA_GOV_IN_KEY`
   - Value: the key

Without your own key, Dharalu uses the public sample key, which returns only 10 rows per call. Today's prices still work, but the first history download can take hours.

## 4. Telegram alerts (optional)

1. In Telegram, message **@BotFather**, send `/newbot`, and follow the questions. Copy the **token** it gives you.
2. Save it as the secret `TELEGRAM_BOT_TOKEN`.
3. Send any message ("hi") to your new bot.
4. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser (put your token in place of `<TOKEN>`). Find `"chat":{"id":123456789` and copy the number.
5. Save it as the secret `TELEGRAM_CHAT_ID`.

**Family or partner group:** add the bot to the group, send a message in the group, and use the group's chat id (a negative number like `-100…`).

You get an alert, for each of wheat, gold, silver and platinum, when:
- the call changes (for example BUY → HOLD). For metals the new call must hold for two checks in a row, so a price wobbling on a threshold doesn't spam you;
- the price moves a lot in a day: wheat 2.5%, gold 2%, silver and platinum 3%;
- every Monday, as a weekly summary.

## 5. AI briefing (optional)

Create a key at https://console.anthropic.com and save it as the secret `ANTHROPIC_API_KEY`. Claude then writes the daily note in English and Telugu, using only the numbers from the analysis. It can't invent prices. Without the key, a rule-based note is written instead. It costs a few cents a day.

## 6. Turn on the dashboard (GitHub Pages)

*Settings → Pages → Build and deployment*:
- **Source:** Deploy from a branch
- **Branch:** `main`, folder `/docs`

After a minute, your dashboard is at `https://<your-github-name>.github.io/dharalu/`.

## 7. First run

*Actions → Dharalu monitor → Run workflow*. **Tick "Re-seed price history first"** for the first run and press *Run workflow*. Metal history (10 years from Yahoo Finance) downloads by itself on the first run; no key is needed.

- With your own key, the history download takes a few minutes. With the sample key it can hit the 2½-hour limit. That's fine: whatever it downloaded is saved, and the next run continues from there.
- After that, GitHub runs a backup at **12:30 and 19:30 IST**, and skips it when your Mac published in the last 3 hours. You don't need to tick bootstrap again. For wheat prices and 5-minute checks, do step 8.
- If GitHub shows *"Workflows aren't being run on this forked repository"*, click **I understand, enable them**.

## 8. Run the agent from your Mac (important)

data.gov.in refuses requests from GitHub's servers, which are outside India. A GitHub run then shows ✅ but logs `Today's feed failed … using saved data`, and wheat prices stop at the last day they arrived. So the agent runs on a computer in India, and GitHub only publishes:

```bash
cd ~/Dharalu                         # your clone of the repository
scripts/mac-schedule.sh install      # check every 5 minutes and publish
scripts/mac-schedule.sh run          # do one full run now
scripts/mac-schedule.sh status       # installed? last lines of the log
```

Every 5 minutes the job runs `agent/run.py --quick`:
- **Gold, silver, platinum:** fetched and re-analysed every time.
- **Wheat:** one quick call to data.gov.in, to one benchmark mandi (they take turns). The full fetch runs only when there are new prices, or every 6 hours. If data.gov.in says *too many requests* (429), wheat pauses for 30 minutes. Mandis report once a day, so nothing is missed.
- **Publishing** (commit + push to GitHub): within 10 minutes of something that matters (a new day of prices, a call change, new mandi rows), otherwise once an hour. GitHub Pages allows about 10 site builds an hour, and the dashboard and the Mac app fetch live metal prices themselves in between.

Notes:
- **Your keys on the Mac:** the job doesn't see GitHub's secrets. Put them in `.env` in the repository folder (it is git-ignored, so never committed), one per line:
  ```bash
  DATA_GOV_IN_KEY=your-key
  TELEGRAM_BOT_TOKEN=...      # optional
  TELEGRAM_CHAT_ID=...        # optional
  ANTHROPIC_API_KEY=...       # optional
  ```
  Without `DATA_GOV_IN_KEY`, wheat uses the shared public sample key, which is often busy (429), so new mandi prices can arrive late.
- If the Mac is asleep, the job runs when it wakes. If GitHub can't be reached, the run commits locally and a later run pushes it.
- The push uses your normal git login. Push once by hand first, so macOS keeps the password in the Keychain.
- To run once without the schedule: `scripts/mac-refresh.sh --full`. To stop: `scripts/mac-schedule.sh uninstall`.
- The log is `~/Library/Logs/Dharalu/refresh.log`.
- Coming from WheatWise 1.x? `install` also removes the old twice-a-day job.

The GitHub runs keep going as a backup, and log why data.gov.in refused them.

## 9. Put in your real costs

Open `config.json` on GitHub (pencil icon to edit) and change the freight, mandi fee, interest and godown numbers to what you really pay. For metals, check the import duty, GST and bank interest. Every field is explained in [CONFIG.md](CONFIG.md). The next run uses them.

## 10. The Mac app (optional)

See [MAC_APP.md](MAC_APP.md). If you use your own fork, set *Settings → Data Source…* in the app to your own dashboard's `data/summary.json`.

## Run on your own computer instead (optional)

You need Python 3.9 or newer. Nothing else is required; `pip install anthropic` adds the AI briefing.

```bash
git clone https://github.com/<you>/dharalu && cd dharalu
export DATA_GOV_IN_KEY=...          # optional but recommended
python3 agent/bootstrap.py          # one time: download wheat history
python3 agent/run.py                # fetch all four, analyse, alert, write docs/data/*.json
python3 -m http.server -d docs      # dashboard at http://localhost:8000
```

`python3 agent/run.py --offline` re-analyses saved data without downloading, which is handy after editing `config.json`.
