# 🌾 WheatWise - a wheat buy/hold/sell agent for Srikakulam

WheatWise watches wheat prices twice a day in the mandis that supply Srikakulam, Andhra Pradesh. It tells you **when to buy, when to hold and when to sell**, and shows the **proof** behind every call: the real number behind each rule, where it came from, and how often the same call worked in the past.

- **Live dashboard:** https://sravankumartangudu.github.io/wheatwise/ (works on phone and computer)
- **Mac menu-bar app:** [download the latest DMG](https://github.com/Sravankumartangudu/wheatwise/releases/latest) - see [guide/MAC_APP.md](guide/MAC_APP.md)
- **Alerts:** Telegram, when the call changes, the price jumps, and once a week

| Stage | What you get |
|---|---|
| **Prediction** | A 45-day price forecast with a likely range, tested against past data so you can see how accurate it really is |
| **Pre-analysis** (before a trade) | Landed cost at Srikakulam, total money needed, holding cost, the break-even sell price, profit in bad / likely / good cases, and a go/no-go checklist |
| **Post-analysis** (after trades) | Your profit and loss (first-in-first-out, after holding costs), a timing score for each trade, whether you followed the agent's call that day, and lessons |
| **Monitoring** | Runs by itself at 12:30 and 19:30 IST. Telegram + Mac notifications when the call changes or the price jumps |
| **Sharing** | One link (Share button → WhatsApp). The briefing is in English and తెలుగు |

## The calls

| Call | Score | If you are buying | If you are holding stock |
|---|---|---|---|
| 🟢 **STRONG BUY** | +3 or more | Good time to buy and stock up | Hold - prices likely to rise |
| 🟢 **BUY** | +1 / +2 | Buy gradually (2-3 lots) | Hold - don't rush to sell |
| 🟠 **HOLD** | 0, outlook up | Don't add stock at today's price | **Keep your stock** - the outlook beats your holding cost |
| ⚪ **WAIT** | 0 | Buy only what you need now | No clear edge - sell in parts only if you need cash |
| 🔴 **SELL** | −1 / −2 | Avoid stocking - buy hand-to-mouth | Sell gradually - prices may soften |
| 🔴 **STRONG SELL** | −3 or less | Do not stock now | Sell / clear stock now |

**HOLD vs WAIT:** both have a total score of 0. It is HOLD when the two forward-looking rules (the 30-day forecast and the season) still point up. That usually means today's price is too high to buy, but prices should rise from here, so keep what you have. In the replay since 2016, HOLD days beat the holding cost 42% of the time, against 36% for WAIT and 33% for SELL.

## How a call is made - and proved

Each rule looks at real Agmarknet prices and adds or removes points. The dashboard shows each rule's **actual number, source and threshold**, so you can check it yourself.

| Rule | Points |
|---|---|
| 30-day forecast vs **cost of holding stock** (interest + godown + losses) | ±1 at ±1%, ±2 at ±3% (only ±1 if the forecast hasn't beaten "no change" in its backtest) |
| **Season**: are prices usually higher 60 days from now? | ±1 at ±3% |
| **Trend**: 7-day average vs 30-day average, plus the 30-day change | ±1 |
| **Price level** vs the last 12 months | +1 if in the cheapest 25%, −1 if in the dearest 15% |
| **Momentum** (RSI-14) | +1 if oversold (<30), −1 if overbought (>70) |
| **MSP floor**: price within 4% of MSP | +1 |
| **FCI OMSS ceiling**: price at or above the OMSS reserve price | −1 |

**Proof it works:**

- **Replay.** Every past day is re-run using only the data known on that day: prices, seasonal pattern, and the MSP of that time. The track record shows what the price did 30 days after BUY, HOLD, WAIT and SELL days. It covers both the last year and the whole history since 2016.
- **Live record.** Every real call is saved in `data/signals_log.csv` and graded automatically 30 days later.

How it all works in detail: [guide/HOW_IT_WORKS.md](guide/HOW_IT_WORKS.md).

## Prerequisites

| For | You need |
|---|---|
| The dashboard | Any browser. Nothing to install |
| The automatic agent | A free GitHub account (it runs on GitHub Actions, free for public repos) and a free [data.gov.in](https://data.gov.in) API key (recommended) |
| Fresh prices | A Mac (or any computer) in India that's on most days: data.gov.in refuses GitHub's servers, so the Mac fetches the prices and GitHub publishes them |
| Telegram alerts (optional) | A Telegram account |
| AI briefing (optional) | An Anthropic API key |
| The Mac app (optional) | macOS 13 Ventura or newer, Apple Silicon or Intel |
| Running it on your own computer (optional) | Python 3.9+ (standard library only; `pip install anthropic` for the AI briefing) |
| Building the Mac app yourself (optional) | Xcode Command Line Tools (`xcode-select --install`) |

## Install

This repository is already set up and running. To run your own copy (for example for another town), follow **[guide/SETUP.md](guide/SETUP.md)**, which takes about 10 minutes. In short:

1. **Fork** this repository on GitHub (or use it as-is).
2. Add the secrets under *Settings → Secrets and variables → Actions*:

   | Secret | Required? | What |
   |---|---|---|
   | `DATA_GOV_IN_KEY` | Recommended | Your data.gov.in key. Without it the public sample key is used (10 rows per call, very slow) |
   | `TELEGRAM_BOT_TOKEN` | Optional | From @BotFather |
   | `TELEGRAM_CHAT_ID` | Optional | Your chat id or a family group's chat id |
   | `ANTHROPIC_API_KEY` | Optional | Claude writes the daily note; without it a rule-based note is used |

3. *Settings → Pages*: deploy from the `main` branch, `/docs` folder.
4. *Actions → WheatWise monitor → Run workflow* (tick **bootstrap** the first time to download price history).
5. **Fetch prices from your Mac:** `scripts/mac-schedule.sh install` (fetches and publishes at 12:00 and 19:00). See [guide/SETUP.md](guide/SETUP.md#8-fetch-prices-from-your-mac-important).
6. **Edit `config.json`** with your real freight rate, mandi fee, interest and godown costs: [guide/CONFIG.md](guide/CONFIG.md).

**Mac app:** download `WheatWise-<version>.dmg` from [Releases](https://github.com/Sravankumartangudu/wheatwise/releases/latest), drag it to Applications, then on first open use *System Settings → Privacy & Security → Open Anyway*. Details: [guide/MAC_APP.md](guide/MAC_APP.md).

## Use

Read **[guide/USER_GUIDE.md](guide/USER_GUIDE.md)** for every tab and a daily routine. The 2-minute version:

1. **Every morning:** open the dashboard (or click 🌾 in the Mac menu bar). Read the call and the advice for your case (buying or holding stock).
2. **Before a big buy:** open *Before you trade*, pick the mandi, and check the break-even price and the go/no-go checklist.
3. **After every trade:** enter it in *My trades*. You will see your real profit after holding costs, and whether your timing was good.
4. **Once a week:** look at *Agent track record* to see whether the calls are still working, and *What to watch* for government moves (MSP, OMSS sales, stock limits).

### Run on your own computer

```bash
python3 agent/bootstrap.py        # one time: download price history (slow without your own key)
python3 agent/run.py              # fetch today's prices, analyse, write docs/data/latest.json
python3 agent/run.py --offline    # re-analyse saved data without downloading
python3 -m http.server -d docs    # open http://localhost:8000
```

## Why landed cost, not a "Srikakulam price"

Andhra Pradesh has reported no wheat mandi prices since 2017, because the state buys its wheat from other states. So WheatWise works out what the wheat costs at your door:

```
landed = mandi price + mandi fee (1.7%) + freight (km × ₹0.30/qtl/km) + handling ₹25 + bags ₹15 + brokerage ₹10
```

**These are starting estimates - change them to your real costs in `config.json`.** Enter your local selling rate in the dashboard's *Mandis* tab to see your margin.

The **benchmark price** comes from Jabalpur, Indore and Kota, the mandis with the longest unbroken history. Each is chain-linked to a common level, so a day when one mandi doesn't report doesn't make the price jump. Sixteen source mandis are compared for landed cost.

## What to watch (also in the dashboard)

- **Prices:** MP and Rajasthan mandi prices, landed cost vs your local rate, diesel and freight.
- **Government:**
  - MSP: ₹2,585 for RMS 2026-27 and ₹2,610 for RMS 2027-28.
  - FCI procurement (Apr–Jun).
  - **FCI OMSS e-auctions**, which cap prices in the lean season.
  - Central pool stocks vs buffer norms.
  - Trader **stock limits**.
  - The export ban and import duty.
- **Crop and weather:** rabi sowing area (Oct–Dec), heatwaves in Feb–Mar (IMD), harvest arrivals (Mar–May).
- **Demand:** Sankranti, Dussehra/Diwali, wedding seasons, flour mills, PDS.
- **Calendar:** usually **buy in Apr–May** (harvest) and **sell in parts Oct–Feb** (lean season). Only hold stock if the expected rise beats your holding cost.

## Files

| Path | What |
|---|---|
| `agent/fetch.py` | data.gov.in (Agmarknet) client: today's all-India feed and the history archive |
| `agent/analyze.py` | Benchmark, indicators, seasonality, forecast + backtest, the scored call with proof, landed cost, track record |
| `agent/briefing.py` | English + Telugu briefing (rules, or Claude when a key is set) |
| `agent/notify.py` | Telegram alerts |
| `agent/run.py` | The daily pipeline |
| `agent/bootstrap.py` | One-time history download |
| `config.json` | **Your costs**, source mandis and distances, MSP, OMSS |
| `data/prices.csv` | Price history (grows every run) |
| `data/signals_log.csv` | Every call the agent has made (for live grading) |
| `docs/` | The dashboard (GitHub Pages) |
| `mac/` | The Mac menu-bar app (Swift): `build.sh`, `package.sh` |
| `.github/workflows/monitor.yml` | The twice-daily schedule |
| `.github/save.sh` | Commits new data, retrying if two runs overlap |
| `scripts/mac-refresh.sh`, `scripts/mac-schedule.sh` | Fetch prices from your Mac and publish them, by hand or twice a day |
| `guide/` | Setup, user guide, how it works, config, Mac app, FAQ |

## Privacy

This repository and dashboard are public, but **your trades never leave your phone or computer**. They are stored in the browser (or in the Mac app). Use *Export CSV* to back them up.

## Disclaimer

WheatWise is a decision-support tool built on public government data and simple, open rules. It is not financial advice. Mandi data can be late or wrong. Always check with your brokers and local market before you trade.

Licence: MIT. Changes: [CHANGELOG.md](CHANGELOG.md).
