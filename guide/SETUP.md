# Setup

About 10 minutes, one time. When you're done, the agent runs by itself twice a day for free on GitHub, with your Mac fetching the prices (step 8), and the dashboard updates automatically.

## 1. Prerequisites

- A **GitHub account** (free). Public repositories get GitHub Actions and Pages for free.
- A **data.gov.in API key** (free, recommended).
- Optional: **Telegram** for alerts, an **Anthropic API key** for the AI briefing, and a **Mac** (macOS 13+) for the menu-bar app.

## 2. Get your own copy

Open https://github.com/Sravankumartangudu/wheatwise and click **Fork**. If you own the repository already, skip this step.

## 3. Get a data.gov.in key

1. Sign up at https://data.gov.in (top right → *Login / Register*).
2. Open *My Account → API Keys* and copy the key.
3. In your repository: *Settings → Secrets and variables → Actions → New repository secret*.
   - Name: `DATA_GOV_IN_KEY`
   - Value: the key

Without your own key, WheatWise uses the public sample key, which returns only 10 rows per call. Today's prices still work, but the first history download can take hours.

## 4. Telegram alerts (optional)

1. In Telegram, message **@BotFather**, send `/newbot`, and follow the questions. Copy the **token** it gives you.
2. Save it as the secret `TELEGRAM_BOT_TOKEN`.
3. Send any message ("hi") to your new bot.
4. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser (put your token in place of `<TOKEN>`). Find `"chat":{"id":123456789` and copy the number.
5. Save it as the secret `TELEGRAM_CHAT_ID`.

**Family or partner group:** add the bot to the group, send a message in the group, and use the group's chat id (a negative number like `-100…`).

You get an alert when:
- the call changes (for example BUY → HOLD);
- the benchmark price moves 2.5% or more in a day;
- every Monday, as a weekly summary.

## 5. AI briefing (optional)

Create a key at https://console.anthropic.com and save it as the secret `ANTHROPIC_API_KEY`. Claude then writes the daily note in English and Telugu, using only the numbers from the analysis. It can't invent prices. Without the key, a rule-based note is written instead. It costs a few cents a day.

## 6. Turn on the dashboard (GitHub Pages)

*Settings → Pages → Build and deployment*:
- **Source:** Deploy from a branch
- **Branch:** `main`, folder `/docs`

After a minute, your dashboard is at `https://<your-github-name>.github.io/wheatwise/`.

## 7. First run

*Actions → WheatWise monitor → Run workflow*. **Tick "Re-seed price history first"** for the first run and press *Run workflow*.

- With your own key, the history download takes a few minutes. With the sample key it can hit the 2½-hour limit. That's fine: whatever it downloaded is saved, and the next run continues from there.
- After that, the agent runs by itself at **12:30 and 19:30 IST**. You don't need to tick bootstrap again. For new prices, also do step 8.
- If GitHub shows *"Workflows aren't being run on this forked repository"*, click **I understand, enable them**.

## 8. Fetch prices from your Mac (important)

data.gov.in refuses requests from GitHub's servers, which are outside India. A GitHub run then shows ✅ but logs `Today's feed failed … using saved data`, and the prices stop at the last day they arrived. The fix is to fetch from a computer in India, and let GitHub publish:

```bash
cd ~/WheatWise                       # your clone of the repository
scripts/mac-schedule.sh install      # fetch + publish at 12:00 and 19:00 every day
scripts/mac-schedule.sh run          # do one now
scripts/mac-schedule.sh status       # installed? last lines of the log
```

- Each run takes 2-3 minutes. It pulls, runs `agent/run.py`, and pushes `data/` and `docs/data/` to GitHub. The dashboard and the Mac app pick that up a minute later.
- If the Mac is asleep at 12:00 or 19:00, the job runs when it wakes.
- The push uses your normal git login. Push once by hand first, so macOS keeps the password in the Keychain.
- To fetch once without the schedule: `scripts/mac-refresh.sh`. To stop: `scripts/mac-schedule.sh uninstall`.
- The log is `~/Library/Logs/WheatWise/refresh.log`.

The GitHub runs keep going as before, and log why data.gov.in refused them. If they ever start getting prices, the Mac job does no harm.

## 9. Put in your real costs

Open `config.json` on GitHub (pencil icon to edit) and change the freight, mandi fee, interest and godown numbers to what you really pay. Every field is explained in [CONFIG.md](CONFIG.md). The next run uses them.

## 10. The Mac app (optional)

See [MAC_APP.md](MAC_APP.md). If you use your own fork, set *Settings → Data Source…* in the app to your own dashboard's `data/latest.json`.

## Run on your own computer instead (optional)

You need Python 3.9 or newer. Nothing else is required; `pip install anthropic` adds the AI briefing.

```bash
git clone https://github.com/<you>/wheatwise && cd wheatwise
export DATA_GOV_IN_KEY=...          # optional but recommended
python3 agent/bootstrap.py          # one time: download history
python3 agent/run.py                # fetch, analyse, alert, write docs/data/latest.json
python3 -m http.server -d docs      # dashboard at http://localhost:8000
```

`python3 agent/run.py --offline` re-analyses saved data without downloading, which is handy after editing `config.json`.
