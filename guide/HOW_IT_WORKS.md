# How it works

Everything is plain Python in `agent/`, using only the standard library. Every number on the dashboard can be traced to a rule here.

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

**Confidence** starts from the size of the score: ±0-1 is Low, ±2-3 Medium, ±4 or more High. It drops one level when there's less than 120 days of history, or when the 30-day direction hit-rate is below 55%.

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

**Score → call:**
| Score | Call |
|---|---|
| ≥ +3 | STRONG BUY |
| +1 / +2 | BUY |
| 0, and the forecast + season rules add up to more than 0 | **HOLD** |
| 0, otherwise | WAIT |
| −1 / −2 | SELL |
| ≤ −3 | STRONG SELL |

**Why HOLD is split from WAIT:** a 0 can mean "nothing is happening". It can also mean "the price is high today (the price-level and trend rules are negative) but the outlook is still up (forecast and season are positive)". For someone holding stock those are different situations.

In the replay since 2016, HOLD days (38 of them) averaged a +1.0% move in 30 days and beat the holding cost 42% of the time. WAIT days averaged +0.4% (36%) and SELL days −0.5% (33%).

## 7. Track record - no peeking

The replay re-runs the rules on every past day using **only what was known on that day**:
- prices up to that day;
- a seasonal pattern rebuilt from data before that month;
- the MSP that applied then (`msp.history`);
- OMSS only after it started.

It then checks the price 30 days later. Results are shown for the last year and for the whole history.

**Live record:** every real call is appended to `data/signals_log.csv`. It is graded on the first real price 30-37 days later (mandis skip holidays):
- BUY and HOLD are right if the price rose;
- SELL is right if it fell;
- WAIT is right if it moved less than 3%.

## 8. Landed cost

```
landed = mandi price + mandi fee % + km × freight rate (or freight_override) + handling + bags + brokerage
```

This is worked out for each of the 16 source mandis, using its latest report from the last 7 days. The cheapest source is highlighted.

## 9. Briefing and alerts

- **Briefing** (`briefing.py`):
  - A rule-based English + Telugu note is always made.
  - With `ANTHROPIC_API_KEY`, Claude (`claude-opus-5-5`) also writes a trader's note from the same JSON. It is told to use only those numbers. If it fails, the rule-based note is used.
- **Alerts** (`notify.py`): Telegram is sent on a call change, a daily move of 2.5% or more, the weekly summary, and the first run. The alert state is only saved once a message is really sent, so a failed send is retried on the next run.

## 10. Schedule

`.github/workflows/monitor.yml` runs at 07:00 and 14:00 UTC (12:30 and 19:30 IST):
1. Fetch today's feed.
2. Merge it into `data/prices.csv`.
3. Analyse, and write `docs/data/latest.json`.
4. Alert.
5. Commit, via `.github/save.sh`, which pulls and retries if two runs overlap.

The save step runs even if the analysis fails, so fetched prices are never lost.
