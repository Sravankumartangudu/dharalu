# ⚖️ Dharalu · ధరలు - buy / hold / sell calls for wheat, gold, silver and platinum

Dharalu ("prices" in Telugu) watches four prices for a trader and family in Srikakulam, Andhra Pradesh:

| | What it watches | Price shown |
|---|---|---|
| 🌾 **Wheat** | The mandis that supply Srikakulam (Agmarknet) | ₹ per quintal, landed at Srikakulam |
| 🥇 **Gold** | World spot price × ₹ rate + import duty | ₹ per 10 g, 24 carat (GST shown on top) |
| 🥈 **Silver** | The same | ₹ per kg, 999 fine |
| 💠 **Platinum** | The same | ₹ per 10 g, 999.5 fine |

For each one it tells you **when to buy, when to hold and when to sell**, and shows the **proof** behind every call: the real number behind each rule, where it came from, and how often the same call worked in the past. A **timeline** puts the past, today's live price and the forecast on one chart, together with the calls the agent would have made.

- **Live dashboard:** https://sravankumartangudu.github.io/dharalu/ (works on phone and computer)
- **Mac menu-bar app:** [download the latest DMG](https://github.com/Sravankumartangudu/dharalu/releases/latest) - see [guide/MAC_APP.md](guide/MAC_APP.md)
- **Prices are checked every 5 minutes.** Gold, silver and platinum are live; wheat updates when the mandis report.
- **Alerts:** Telegram and Mac notifications when a call changes or a price jumps, plus once a week

> Formerly **WheatWise** (1.x, wheat only). The old address `…github.io/wheatwise/` no longer updates - use the new one above.

| Stage | What you get |
|---|---|
| **Overview** | All four on one page: today's call, live price, 1-year sparkline with the 30-day forecast, and a "100 = a year ago" chart to compare them |
| **Timeline** | Past prices → today → forecast with its likely range, the call on every day (a coloured strip), and what each past 30-day forecast said vs what happened |
| **Prediction** | A 45-day forecast with a likely range, tested against past data so you can see how accurate it really is |
| **Why the forecast** | 🔮 The expected move split into recent trend + season + last few days' average at 7/14/30 days, how far to trust it, and what it can't see |
| **Pre-analysis** (before a trade) | Wheat: landed cost, money needed, holding cost, break-even. Metals: GST + making charge, the bank interest you give up, the buy-back cut, break-even. Both: bad / likely / good cases and a go/no-go checklist |
| **Post-analysis** (after trades) | Your profit and loss (first-in-first-out, after holding costs), a timing score for each trade, whether you followed the agent's call that day, and lessons - per commodity |
| **Monitoring** | A job on the Mac every 5 minutes; Telegram + Mac notifications on call changes and big moves |
| **Sharing** | One link (Share button → WhatsApp). The briefing is in English and తెలుగు |

## The calls

| Call | Score | If you are buying | If you are holding |
|---|---|---|---|
| 🟢 **STRONG BUY** | +3 or more | Good time to buy - in 2-3 parts | Hold - prices likely to rise |
| 🟢 **BUY** | +1 up to +3 | Buy gradually, in parts | Hold - don't rush to sell |
| 🟠 **HOLD** | between −1 and +1, outlook up | Don't add at today's price | **Keep it** - the outlook beats your holding cost |
| ⚪ **WAIT** | between −1 and +1 | Buy only what you need now | No clear edge - sell only if you need cash |
| 🔴 **SELL** | −1 down to −3 | Avoid stocking - wait for a dip | Sell gradually / book part profit |
| 🔴 **STRONG SELL** | −3 or less | Do not buy now | Sell / book profit now |

**HOLD vs WAIT:** both have a score between −1 and +1. It is HOLD when the two forward-looking rules (the 30-day forecast and the season) still point up: today's price is no bargain, but it should rise from here, so keep what you have.

Since 2.2 the score can be fractional (e.g. +1.5), because each rule's points are multiplied by a weight it earned (below).

**Every call comes with:**
- **📍 Where the price is from**, next to every price:
  - wheat is the **wholesale mandi price at Jabalpur, Indore & Kota** (Madhya Pradesh, Rajasthan), plus the cheapest *landed at Srikakulam* cost;
  - gold, silver and platinum are the **all-India import price** (world spot × ₹ rate + import duty, before GST), not a Srikakulam jeweller's rate.
- **One plain line**: why, in English and తెలుగు, e.g. *"Mainly because the 30-day forecast doesn't beat the holding cost and prices have been falling for weeks."*
- **What would change it**: the prices at which the call would turn, e.g. *"Turns WAIT if the price falls to ₹1,17,670 (−11.8%)."*
- **Its record**: how often past days with this call were right, next to how often *any* day was, e.g. *"Past SELL days (1047 since 2017): lower 30 days later on 44% vs 38% of all days → edge +5 points."*
- **Confidence** that this record can cap: a call whose past days barely beat any day can't be High.
- **What changed** since the previous prices day: which rules moved, and whether the call changed.
- For gold, silver and platinum, a **Saving for years** view (ADD / STEADY / GO SLOW) for money you'll keep for a year or more.
- A four-line **briefing**: the call and advice, why, what would change it, how sure.

**Holding cost** is what holding costs you for 30 days. For wheat that's interest, godown rent and losses. For metals it's the bank interest the money would have earned.

## How a call is made - and proved

Each rule gives points. The dashboard shows each rule's **actual number, source and threshold**, so you can check it yourself.

| Rule | Wheat | Gold / silver / platinum |
|---|---|---|
| 30-day forecast vs **holding cost** | ±1 at ±1%, ±2 at ±3% (only ±1 if the forecast hasn't beaten "no change" in its backtest) | same |
| **Season**: are prices usually higher 60 days from now? | ±1 at ±3% | ±1 at ±1.5% |
| **Trend** (weeks): 7-day vs 30-day average, plus the 30-day change | ±1 | ±1 |
| **Long trend** (months): price and 50-day average vs the 200-day | - | ±1 |
| **Price level** vs the last 12 months | +1 if in the cheapest 25%, −1 if in the dearest 15% | same |
| **Momentum** (RSI-14) | +1 if oversold (<30), −1 if overbought (>70) | same |
| **Rupee**: US$/₹ over 30 days (a weaker rupee makes metal dearer) | - | ±1 at ±1% |
| **Gold/silver ratio** (silver only): ounces of silver one ounce of gold buys | - | +1 at ≥ 85 (silver cheap), −1 at ≤ 65 |
| **MSP floor**: price within 4% of MSP | +1 | - |
| **FCI OMSS ceiling**: price at or above the reserve price | −1 | - |

**Weights (since 2.2).** A rule's points are multiplied by a weight from its own record: on every past day it said "up" or "down", was it right more often than the usual rate?
- Edge of 10+ points over the usual rate (with 120+ votes) counts double (×2).
- Edge of 3+ points counts ×1, 0 to 3 points counts ×½, and a rule that did worse than guessing counts ×0.
- Fewer than 60 votes: ×1, since that's too few to judge.

The weights are learned walk-forward: each day only uses past days whose 30-day result was already known. So the replay below is still a fair test.

**Trend cap.** The forecast, the trend and the long trend all read the same recent direction, so together they count at most ±2. Without the cap, one trend got counted two or three times.

**Hold for two checks.** Live metal prices move every few minutes. A new metal call is shown only once it has held for two checks in a row; until then the old call stays, with a ⏳ note.

**Proof it works:**

- **Replay.** Every past day is re-run using only the data known on that day. The track record shows what the price did 30 days after each kind of call: last year, and the whole history (wheat since 2016, metals about 10 years).
- **Weighted vs equal.** The *Agent track record* tab replays the history twice, with learned weights and with every rule counting the same, so you can see which did better for each commodity.
- **Live record.** Every real call is saved in `data/signals_log.csv` (wheat) or `data/signals_<metal>.csv`, and graded automatically 30 days later.

How it all works in detail: [guide/HOW_IT_WORKS.md](guide/HOW_IT_WORKS.md).

## Prerequisites

| For | You need |
|---|---|
| The dashboard | Any browser. Nothing to install |
| The agent | A Mac (or any computer) in India that's on most days - it checks every 5 minutes and publishes to GitHub Pages. GitHub Actions is a twice-a-day backup |
| Wheat prices | A free [data.gov.in](https://data.gov.in) API key (recommended). data.gov.in refuses GitHub's servers, so wheat comes from the Mac |
| Metal prices | Nothing - Yahoo Finance and gold-api.com are free and need no key |
| Telegram alerts (optional) | A Telegram account |
| AI briefing (optional) | An Anthropic API key |
| The Mac app (optional) | macOS 13 Ventura or newer, Apple Silicon or Intel |
| Running the agent | Python 3.9+ (standard library only; `pip install anthropic` for the AI briefing) |
| Building the Mac app yourself (optional) | Xcode Command Line Tools (`xcode-select --install`) |

## Install

This repository is already set up and running. To run your own copy, follow **[guide/SETUP.md](guide/SETUP.md)** (about 10 minutes). In short:

1. **Fork** this repository on GitHub (or use it as-is).
2. Add the secrets under *Settings → Secrets and variables → Actions*:

   | Secret | Required? | What |
   |---|---|---|
   | `DATA_GOV_IN_KEY` | Recommended | Your data.gov.in key. Without it the public sample key is used (10 rows per call, very slow) |
   | `TELEGRAM_BOT_TOKEN` | Optional | From @BotFather |
   | `TELEGRAM_CHAT_ID` | Optional | Your chat id or a family group's chat id |
   | `ANTHROPIC_API_KEY` | Optional | Claude writes the daily note; without it a rule-based note is used |

3. *Settings → Pages*: deploy from the `main` branch, `/docs` folder.
4. *Actions → Dharalu monitor → Run workflow* (tick **bootstrap** the first time to download wheat history).
5. **Run the agent from your Mac:** `scripts/mac-schedule.sh install` (checks every 5 minutes). See [guide/SETUP.md](guide/SETUP.md#8-run-the-agent-from-your-mac-important).
6. **Edit `config.json`** with your real wheat costs and the metal duty / GST / bank interest: [guide/CONFIG.md](guide/CONFIG.md).

**Mac app:** download `Dharalu-<version>.dmg` from [Releases](https://github.com/Sravankumartangudu/dharalu/releases/latest), drag it to Applications, then on first open use *System Settings → Privacy & Security → Open Anyway*. Details: [guide/MAC_APP.md](guide/MAC_APP.md).

## Use

Read **[guide/USER_GUIDE.md](guide/USER_GUIDE.md)** for every tab and a daily routine. The 2-minute version:

1. **Every morning:** open the dashboard (or click ⚖️ in the Mac menu bar). The overview shows all four calls; click one for its advice (buying or holding).
2. **Before a big buy:** open *Before you trade* and check the break-even price and the go/no-go checklist.
3. **After every trade:** enter it in *My trades*. You will see your real profit after holding costs, and whether your timing was good.
4. **Once a week:** look at *Timeline* and *Agent track record* to see whether the calls are still working, and *What to watch* for the outside things that move each price.

### Run on your own computer

```bash
python3 agent/bootstrap.py        # one time: download wheat history (slow without your own key)
python3 agent/run.py              # fetch all prices, analyse, write docs/data/*.json
python3 agent/run.py --quick      # the 5-minute check: metals every time, wheat when the mandis have news
python3 agent/run.py --offline    # re-analyse saved data without downloading
python3 -m http.server -d docs    # open http://localhost:8000
```

## Wheat: landed cost, not a "Srikakulam price"

Andhra Pradesh has reported no wheat mandi prices since 2017, because the state buys its wheat from other states. So Dharalu works out what the wheat costs at your door:

```
landed = mandi price + mandi fee (1.7%) + freight (km × ₹0.30/qtl/km) + handling ₹25 + bags ₹15 + brokerage ₹10
```

**These are starting estimates - change them to your real costs in `config.json`.** Enter your local selling rate in the dashboard's *Mandis* tab to see your margin.

The **benchmark price** comes from Jabalpur, Indore and Kota, the mandis with the longest unbroken history. Each is chain-linked to a common level, so a day when one mandi doesn't report doesn't make the price jump. Sixteen source mandis are compared for landed cost.

## Metals: the India price

```
India price = world price (US$ per troy ounce) × ₹ per US$ ÷ 31.1035 g × grams × (1 + import duty)
```

- Import duty is 6% for gold and silver and 6.4% for platinum (customs + AIDC since the July 2024 Budget). 3% GST is shown on top.
- Your jeweller's rate will differ a little (local premium, purity, making charge). The *Before you trade* tab lets you add making charge and the buy-back cut.
- History is COMEX futures closes (Yahoo Finance), lined up with today's spot price.

## What to watch (also in the dashboard)

- **Wheat:**
  - MSP: ₹2,585 for RMS 2026-27 and ₹2,610 for RMS 2027-28.
  - FCI procurement and **OMSS e-auctions**, central pool stocks, trader stock limits, trade policy.
  - Sowing and weather.
  - The calendar: usually **buy in Apr–May** and **sell in parts Oct–Feb**.
- **Gold / silver / platinum:**
  - The world price and the rupee.
  - US interest rates and the dollar; central-bank buying.
  - Wars and market falls, which push gold up as a safe haven.
  - Silver: industrial demand (solar, electronics, EVs) and the gold/silver ratio. Platinum: car catalysts, South African mine supply, and how hard it is to sell back.
  - Import duty in the Union Budget.
  - Dhanteras, Akshaya Tritiya and wedding seasons.

## Files

| Path | What |
|---|---|
| `agent/fetch.py` | data.gov.in (Agmarknet) client: today's all-India feed and the history archive |
| `agent/analyze.py` | Wheat benchmark, indicators, seasonality, forecast + backtest, the scored call with proof, landed cost, track record |
| `agent/metals.py` | Gold, silver, platinum: Yahoo + gold-api.com, the India price, and the same analysis |
| `agent/briefing.py` | English + Telugu briefing (rules, or Claude when a key is set) |
| `agent/notify.py` | Telegram alerts, per commodity |
| `agent/run.py` | The pipeline (`--quick` every 5 minutes, full, `--offline`) |
| `agent/bootstrap.py` | One-time wheat history download |
| `config.json` | **Your costs**, source mandis and distances, MSP, OMSS, metal duty / GST / interest |
| `data/prices.csv`, `data/metals/` | Price history (grows every run) |
| `data/signals_*.csv` | Every call the agent has made (for live grading) |
| `docs/` | The dashboard (GitHub Pages). `docs/data/summary.json` is the one file the Mac app reads |
| `mac/` | The Mac menu-bar app (Swift): `build.sh`, `package.sh` |
| `scripts/mac-refresh.sh`, `scripts/mac-schedule.sh` | Run the agent on your Mac and publish, by hand or every 5 minutes |
| `.github/workflows/monitor.yml` | The twice-a-day backup run (skipped when the Mac published recently) |
| `guide/` | Setup, user guide, how it works, config, Mac app, FAQ |

## Privacy

This repository and dashboard are public, but **your trades never leave your phone or computer**. They are stored in the browser (or in the Mac app). Use *Export CSV* to back them up.

## Disclaimer

Dharalu is a decision-support tool built on public data and simple, open rules. It is not financial advice. Prices can be late or wrong. Always check with your brokers, local market or jeweller before you trade.

Licence: MIT. Changes: [CHANGELOG.md](CHANGELOG.md).
