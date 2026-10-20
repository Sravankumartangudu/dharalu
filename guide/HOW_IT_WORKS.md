# How it works

Everything is plain Python in `agent/`, using only the standard library. Every number on the dashboard can be traced to a rule here. Sections 1-8 describe wheat; [section 9](#9-gold-silver-platinum) covers what is different for gold, silver and platinum.

## 1. Data

- **Source:** Agmarknet, via data.gov.in:
  - the current daily feed, all India (`9ef84268-…`);
  - the history archive, for the watched mandis (`35985678-…`).
- **Stored:** `data/prices.csv`. Watched mandis are kept for ever; the rest of India is kept for 120 days, for the state table.
- **Market names:** Agmarknet renamed most markets in Nov 2025 ("Indore" → "Indore APMC"). History under the old name is stored under the new one, so each mandi is one series.
- **Bad days:** a mandi's price more than 15% away from the median of its ±7 neighbouring days is dropped as a typo.

## 2. The benchmark price

Andhra Pradesh has no wheat mandi data, so the benchmark is built from **Jabalpur, Indore and Kota**, the mandis with the longest history.

The three mandis trade at different levels, and some days a mandi doesn't report. A plain median would jump whenever the mix changes, so the benchmark is **chain-linked**:
1. The reference is the mandi with the most days.
2. Each other mandi is scaled by its median price ratio to the reference (it needs 15 or more shared days).
3. Each day's benchmark is the median of the scaled prices, multiplied back to a typical mandi's level.

## 3. Indicators

- 7- and 30-day averages, and the 1/7/30-day changes.
- 52-week low, high and percentile.
- RSI-14.

All are computed on the benchmark.

## 4. Seasonality

1. For each year with 10 or more months of data, divide each month's average price by that year's average.
2. Take the median of those ratios across years. This gives a 12-month index.
3. Blend in a typical Indian wheat pattern (cheap at harvest Apr-May, dear Dec-Feb). Your data gets weight years ÷ (years + 2): one-third with 1 year, 82% with 9 years.
4. Days between months are interpolated between the 15th of each month.

## 5. Forecast

The forecast works on the price with the season taken out:
1. Fit the trend of the last 30 days.
2. Carry it forward with damping, so it fades.
3. Put the seasonal shape back in.

**Backtest:** every 3rd day of the last two years, the forecast is re-made using only the data and seasonal pattern known that day. It is compared with what happened at 7, 14 and 30 days. The results:
- the average error (MAPE), next to the "price stays the same" guess;
- the direction hit-rate;
- the 10th-90th percentile of errors.

That percentile range becomes the **likely range** on the dashboard, widened for longer horizons. If the 30-day forecast doesn't beat the "no change" guess, the forecast rule is capped at ±1 point.

**Why the forecast says this** (`forecast_reason` in the data). In log terms the forecast is *starting level + trend × fade + season*, so its move from today's price splits exactly into three parts, shown for 7, 14 and 30 days:

| Part | What it is |
|---|---|
| **Recent trend** | The last 30 days' direction with the season taken out, carried forward but fading every day (about 65% of a month's trend is kept over the next 30 days) |
| **Season** | How much dearer or cheaper the seasonal pattern usually makes the target day than today |
| **Last few days' average** | The forecast starts from today's price averaged with the last 5 days, so a one-day jump or dip counts only half |

The parts add up to the expected move (in log terms, so the % may differ by a rounding hair). The biggest part is named as the main reason. Next to it the agent shows how far to trust the forecast (backtest error vs "no change", direction hit-rate), how many points it gives in today's call, and what it can't see: for wheat a new MSP, OMSS sales, the harvest size or export/stock rules; for metals US rates, war or crisis news, central-bank buying or a Budget duty change.

**Confidence** is set in three steps:
1. **Size of the score:** below ±1.5 is Low, below ±3.5 Medium, otherwise High.
2. **One level down** when there's less than 120 days of history, or when the forecast's 30-day direction hit-rate is below 55%.
3. **Capped by the call's own record:** past days with this call (buy, hold, wait or sell) must have been right clearly more often than any day.
   - An edge of 10+ points allows High.
   - 3 to 10 points allows at most Medium.
   - Under 3 points, or fewer than 30 such days, means Low.

The dashboard lists the reasons under *Why … confidence*.

## 6. The score

| Rule | Points |
|---|---|
| 30-day forecast edge = expected change − holding cost | +2 at ≥ +3%, +1 at ≥ +1%, −1 at ≤ −1%, −2 at ≤ −3% (capped at ±1 if the forecast is weak) |
| Season: next-60-day seasonal change | +1 at ≥ +3%, −1 at ≤ −3% |
| Trend: 7-day average vs 30-day average, and the 30-day change | +1 both up, −1 both down |
| 52-week percentile | +1 at ≤ 25, −1 at ≥ 85 |
| RSI-14 | +1 below 30, −1 above 70 |
| MSP: price within 4% of the MSP that applied that day | +1 |
| OMSS: price at or above the reserve price (only while sales run) | −1 |

**Holding cost** for 30 days = interest + godown rent + storage loss (from `config.json`), as a % of the price.

**Weights (since 2.2).** The points above are multiplied by a weight from each rule's own record. Counted points = points × weight, and the score is the sum of the counted points.
- **The record:** on every past day the rule said "up" or "down", was the price higher or lower 30 days later?
- **The usual rate:** how often a blind guess in that direction would have been right on all known days.
- **The weight**, from the edge (right % minus the usual rate):

| Rule's record | Weight |
|---|---|
| fewer than 60 votes | ×1 (too few to judge) |
| edge ≥ 10 points, with ≥ 120 votes | ×2 |
| edge ≥ 3 points | ×1 |
| edge 0 to 3 points | ×½ |
| edge below 0 (worse than guessing) | ×0, not counted |

The weights are **walk-forward**: on each replayed day only the past days whose 30-day result was already known are used (`RuleBook` in `analyze.py`). Each commodity learns its own weights.

**Trend cap.** "30-day forecast vs holding cost", "Trend", "Trend (weeks)" and "Long trend (months)" all read the recent direction. Together they count at most ±2 (`TREND_CAP`), scaled down evenly. Without the cap, one trend was counted two or three times.

**Score → call:**
| Score | Call |
|---|---|
| ≥ +3 | STRONG BUY |
| +1 up to +3 | BUY |
| between −1 and +1, and the forecast + season rules add up to more than 0 | **HOLD** |
| between −1 and +1, otherwise | WAIT |
| −1 down to −3 | SELL |
| ≤ −3 | STRONG SELL |

**Why HOLD is split from WAIT:** a score near 0 can mean "nothing is happening". It can also mean "the price is high today (the price-level and trend rules are negative) but the outlook is still up (forecast and season are positive)". For someone holding stock those are different situations.

**With each call** (`decide()` in `analyze.py`):
- **Plain reason:** the one or two rules that counted most for the call, plus the strongest one against it, in English and తెలుగు.
- **What would change it:** the agent re-scores the day with the price moved up and down in 0.25% steps (up to 15%), re-making the forecast each time. The first price where the call changes is the trigger. "Stays SELL even if it rises 15%" means no trigger was found.
- **Its record:** past days with this call, right % vs the usual rate for any day (the edge), and the average move.
- **What changed:** the rules whose counted points moved since the previous prices day's final call, and whether the call changed.
- **Equal-weights call:** what the call would be if every rule counted the same, for comparison.

**Hold for two checks (metals).** The live price wiggles every 5 minutes, so near a boundary the call could flip back and forth. A new call is shown only when it has held for 2 checks in a row (`HOLD_CHECKS` in `run.py`). Until then the old call stays, with a ⏳ note saying what the score says now.

## 7. Track record - no peeking

The replay re-runs the rules on every past day using **only what was known on that day**:
- prices up to that day;
- a seasonal pattern rebuilt from data before that month;
- the MSP that applied then (`msp.history`);
- OMSS only after it started.

It then checks the price 30 days later. Results are shown for the last year and for the whole history.

The replay runs twice, with learned weights and with every rule counting the same, and the *Agent track record* tab shows both side by side. Results since the start of each history (edge = points better than any day):

| | Weighted BUY | Equal BUY | Weighted HOLD | Equal HOLD | Weighted SELL | Equal SELL |
|---|---|---|---|---|---|---|
| Wheat | +8.1 (1412 days) | +5.5 | +10.9 (192) | −1.7 (37) | +11.2 (985) | +7.3 |
| Gold | **−3.3** (438) | +2.4 | +17.3 (323) | +11.4 (33) | +5.3 (1047) | +3.6 |
| Silver | +11.3 (935) | +0.3 | −31.8 (13) | −18.9 (50) | +14.2 (761) | +0.7 |
| Platinum | +16.7 (540) | −2.5 | −16.3 (71) | +8.6 (83) | +7.4 (850) | 0 |

Weights helped most calls. They made two things worse: **gold BUY** (gold rose on most days anyway, so a BUY call barely beat any day) and **platinum HOLD**. Silver HOLD is rare and has always been weak. Read the tab, not just the call.

The same replay also records each day's 30-day forecast. The *Timeline* tab draws it as the "predicted 30 days earlier" line next to the real price, up to today.

**Live record:** every real call is appended to `data/signals_log.csv` (metals: `data/signals_<metal>.csv`). It is graded on the first real price 30-37 days later (mandis skip holidays):
- BUY and HOLD are right if the price rose;
- SELL is right if it fell;
- WAIT is right if it moved less than 3%.

## 8. Landed cost

```
landed = mandi price + mandi fee % + km × freight rate (or freight_override) + handling + bags + brokerage
```

This is worked out for each of the 16 source mandis, using its latest report from the last 7 days. The cheapest source is highlighted.

## 9. Gold, silver, platinum

`agent/metals.py` runs the same analysis (indicators, forecast + backtest, seasonality, scored call with proof, replay) on a different price.

**Data** (free, no key):
- **History:** COMEX futures daily closes from Yahoo Finance (`GC=F`, `SI=F`, `PL=F`, US$ per troy ounce, 10 years) and the US$/₹ rate (`INR=X`). Stored in `data/metals/`, topped up with the last 5 days each run.
- **Live:** the spot price from gold-api.com (`XAU`, `XAG`, `XPT`).
- **Basis:** futures trade a little above spot (interest until delivery). The history is scaled by today's spot ÷ futures ratio (only if it is within ±10%), so it lines up with today's price, and today's point *is* the spot price.

**India price:**
```
India price = US$ per oz × ₹ per US$ ÷ 31.1035 g × grams × (1 + import duty)
```
Gold per 10 g, silver per kg, platinum per 10 g. GST is shown separately ("with GST"), because it is paid on top when you buy.

**Season:** metals have no harvest. The seasonal index starts from "no season" (flat) and learns from the price with the long trend taken out, weighted the same way as wheat: one-third with 1 year of data, 82% with 9.

**Holding cost:** the bank interest the money would have earned (`interest_pct_per_month`, 0.6% = about 7.2% a year).

**The score** (max ±8; silver ±9):
| Rule | Points |
|---|---|
| 30-day forecast edge = expected change − holding cost | as wheat: ±2 at ±3%, ±1 at ±1% (capped at ±1 if the forecast is weak) |
| Season: next-60-day seasonal change | +1 at ≥ +1.5%, −1 at ≤ −1.5% |
| Trend (weeks): 7-day vs 30-day average, and the 30-day change | +1 both up, −1 both down |
| Long trend (months): price and the 50-day average vs the 200-day average | +1 both above, −1 both below |
| Price level: 52-week percentile | +1 at ≤ 25, −1 at ≥ 85 |
| RSI-14 (trading days only) | +1 below 30, −1 above 70 |
| Rupee: US$/₹ change over 30 days | +1 at ≥ +1% (rupee weaker), −1 at ≤ −1% |
| Silver only: gold/silver ratio | +1 at ≥ 85 (silver cheap vs gold), −1 at ≤ 65 |

The weights, the trend cap and the score → call table are the same as wheat's, including HOLD.

**Saving for years (1 year or more).** Gold, silver and platinum also get a long-term view (`long_view()` in `metals.py`), graded on the price **1 year later**:

| Rule | Points |
|---|---|
| Price vs its 3-year average | +1 at or below the average, −1 at 30%+ above |
| Change over 12 months | +1 after a 10%+ fall, −1 after a 30%+ rise |
| Long trend (200 days) | +1 above, −1 below |

A rule only counts if its own record agrees: on days it said +1 (or −1), the next year must have been better (or worse) than for any day, with at least 100 such days. Otherwise it shows as "Not counted (its record disagrees)".

For gold, for example, "far above the 3-year average" was followed by +32% a year later, against +24% on any day. So that rule is shown but not counted.

The total gives **ADD** (≥ +1: a good time to add to long-term savings), **STEADY** (keep the regular buys) or **GO SLOW** (≤ −1: keep the small regular buys, avoid one big purchase). It also shows the past record of each view and the 5- and 10-year growth per year.

This record covers only about 6 years of 1-year results, which overlap, and the rules were switched on or off using the same years. Treat it as a guide, not proof.

**Live prices between runs:** the dashboard and the Mac app fetch gold-api.com themselves every 5 minutes, and convert with the agent's own factor (₹ rate × duty ÷ ounce). A live price more than 15% away from the agent's price is ignored as a bad tick. Only the agent changes the call.

## 10. Briefing and alerts


- **Briefing** (`briefing.py`), one per commodity:
  - A rule-based English + Telugu note is always made. It opens with four lines: the call and advice, *Why*, *What would change it*, *How sure*. Then come the price, the cheapest source (wheat) or *Saving for years* (metals), and the season.
  - With `ANTHROPIC_API_KEY`, Claude (`claude-opus-5-5`) also writes a trader's note from the same JSON. It is told to use only those numbers. If it fails, the rule-based note is used.
- **Alerts** (`notify.py`), per commodity: Telegram is sent on a call change, a big daily move (wheat 2.5%, gold 2%, silver and platinum 3%), the weekly summary, and the first run. A metal's new call must hold for two checks in a row before it alerts. The alert state is only saved once a message is really sent, so a failed send is retried on the next run.

## 11. Schedule

**On the Mac, every 5 minutes** (`scripts/mac-refresh.sh` via launchd, set up by `scripts/mac-schedule.sh install`). data.gov.in refuses GitHub's servers, which are outside India, so this is where wheat prices come from. Each run is `agent/run.py --quick`:
1. Metals: top up the closes, fetch the live spot, re-analyse.
2. Wheat: one quick call (newest 10 rows of one benchmark mandi, a different one each time, so 288 calls a day). After a 429 *too many requests*, wheat pauses for 30 minutes. The full fetch + analysis runs only when there's a new day of prices, or every 6 hours. Otherwise the published wheat analysis is kept as it is.
3. Compare with the last published `docs/data/summary.json`, and print `MATERIAL: …` when something matters (a new prices day, a call change, new mandi rows).
4. Publish (commit + push) within 10 minutes of a material change, otherwise once an hour. GitHub Pages allows about 10 site builds an hour.

**GitHub Actions backup** (`.github/workflows/monitor.yml`) at 07:00 and 14:00 UTC (12:30 and 19:30 IST). It runs `agent/run.py --if-stale 3`, which does nothing when the Mac published in the last 3 hours. Otherwise it fetches, analyses, alerts and commits via `.github/save.sh`, which pulls and retries if two runs overlap. The save step runs even if the analysis fails, so fetched prices are never lost. When a request fails, the log line says why (for example the HTTP error).

**Output:** `docs/data/latest.json` (wheat, as in 1.x), `docs/data/<metal>.json` (+ `<metal>-history.json`, the long price history and day-by-day replay, loaded only when a tab needs it), and `docs/data/summary.json`, the small file with all four calls that the Mac app reads.
