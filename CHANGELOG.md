# Changelog

## 2.3.0 - 20 Oct 2026

**📍 Every price now says where it is from.**
- **Wheat**: *Wholesale mandi price · Jabalpur, Indore & Kota (Madhya Pradesh, Rajasthan)*, with the cheapest *landed at Srikakulam* cost under it. Andhra Pradesh publishes no wheat mandi prices, so it says that this is not a Srikakulam rate.
- **Gold, silver, platinum**: *All-India import price · world spot + 6% duty, before GST* (6.4% for platinum). It says that this is not a Srikakulam jeweller's rate.
- **Where it shows:**
  - the dashboard header on every tab;
  - the Today card, with the full detail;
  - the key-number tiles;
  - each overview card, and a short note on the All page;
  - the Mac app menu (hover for the detail).
- The agent writes it as `where` in each commodity's data and in `summary.json`.

## 2.2.0 - 20 Oct 2026

**Easier to read, and the rules now earn their say.** All ten suggestions from the review.

**Reading a call**
- **One plain line** under the call, in English and తెలుగు: why, mainly, plus the strongest reason against it.
- **🎯 What would change it:** the prices where the call would turn. The agent re-scores the day with the price moved in 0.25% steps up to 15%, re-making the forecast each time. Example: *Turns WAIT if the price falls to ₹1,17,670 (−11.8%)*.
- **📊 Its record:** past days with this call vs any day. Example: *Past SELL days (1047 since 2017): lower 30 days later on 44% vs 38% of all days → edge +5 points*.
- **🔄 What changed since <date>:** on a new prices day, the rules that moved and whether the call changed.
- **Four-line briefing:** the call and advice, *Why*, *What would change it*, *How sure*. Then the details. The Claude briefing is asked for the same four lines, and never to give a ×0 rule as a reason.
- **📅 Saving for years** (gold, silver, platinum): ADD / STEADY / GO SLOW for money kept 1 year or more. It uses three long-run rules graded on the price 1 year later; a rule only counts if its own record agrees. It shows its record and the 5- and 10-year growth. Today all three metals say GO SLOW. Gold's "far above the 3-year average" rule is shown but not counted, because a year later such days were *higher* than usual (+32% vs +24%). About 6 overlapping years of results, so a guide, not proof.

**How the call is made**
- **Learned weights per commodity.** Each rule's points × a weight from its own record: ×2, ×1, ×½, or ×0 for a rule worse than guessing. They are learned walk-forward, so the replay still never peeks. Scores can now be fractional, and the calls are bands (+1 up to +3 = BUY, between −1 and +1 = HOLD/WAIT…).
- **Trend cap:** the forecast, trend and long-trend rules together count at most ±2. They read the same direction and were being counted two or three times.
- **Confidence** is now also capped by the call's own record. An edge of 10+ points allows High, 3–10 allows Medium, less than that means Low.
- **Hold for two checks** (metals): a new call is shown only after 2 checks in a row (5 minutes apart). Until then a ⏳ note says what the score says now.

**Before → after** (whole-history replay; edge = points better than any day):

| | BUY | HOLD | SELL |
|---|---|---|---|
| Wheat | +5.5 → **+8.1** | −1.7 → **+10.9** | +7.3 → **+11.2** |
| Gold | +2.4 → **−3.3** (worse) | +11.4 → **+17.3** | +3.6 → **+5.3** |
| Silver | +0.3 → **+11.3** | −18.9 → −31.8 (13 days) | +0.7 → **+14.2** |
| Platinum | −2.5 → **+16.7** | +8.6 → **−16.3** (worse) | 0 → **+7.4** |

Weights helped most calls. Gold BUY and platinum HOLD got worse, and silver HOLD is rare and weak. The *Agent track record* tab shows both ways side by side, plus each rule's own record.

Today's calls under 2.2 vs the old equal weights: gold SELL (was STRONG SELL), silver BUY (was SELL), platinum BUY (was SELL), wheat BUY.

**Dashboard:** a score gauge in place of the integer bar. The proof table gains *Weight* and *Counted* columns and a trend-cap note. Also new: the changes card, the *Saving for years* box, the weighted-vs-equal and rule-record tables, and the plain line / trigger on each overview card.

**Mac app 2.2.0:** fractional scores. The menu adds the plain line, 🎯 trigger, 📊 record, 🤔 confidence reasons, 🔄 previous call and 📅 *Saving for years*. The proof shows *points ×weight = counted*.

## 2.1.0 - 20 Oct 2026

**🔮 Why the forecast says this.** Every forecast now comes with its reason.
- The expected move at 7, 14 and 30 days is split into its three parts: **recent trend** (the last 30 days' direction, season taken out, fading), **season** (the usual month-to-month pattern) and **last few days' average** (a one-day jump or dip counts half). They add up to the forecast; the biggest one is named as the main reason.
- With it: how far to trust the forecast (tested error vs "price stays the same", direction right %), the points it gives in today's call, and what it can't see (wheat: MSP, OMSS, harvest, export/stock rules; metals: US rates, crises, central-bank buying, Budget duty).
- Shown on the Timeline and Forecast tabs (card + a *Why* line on the Future tile), the Today tab, each overview card, the Mac menu (Mac app 2.1.0) and the English/తెలుగు briefing. Data: `forecast_reason` in each commodity's JSON, `forecast_why` in summary.json.

## 2.0.0 - 19 Oct 2026

**WheatWise is now Dharalu (ధరలు, "prices"), and it watches gold, silver and platinum as well as wheat.** The new address is https://sravankumartangudu.github.io/dharalu/. The old `/wheatwise/` address no longer updates.

**Gold, silver, platinum**
- Each gets the full wheat treatment: the call with proof, a 45-day forecast tested against the past, the seasonal pattern, the replayed track record, live grading, the briefing in English and తెలుగు, *Before you trade* and *My trades*.
- The India price is the world price × the ₹ rate + import duty: gold per 10 g, silver per kg, platinum per 10 g, with GST shown on top. History is 10 years of COMEX closes, lined up with today's spot price.
- The metal rules add a long trend (200-day), the rupee's 30-day move and, for silver, the gold/silver ratio. Holding cost is the bank interest you give up.
- *Before you trade* for metals has the making charge, GST, the buy-back cut and the break-even rate.
- *What to watch* for metals: the rupee, duty, US rates, central-bank buying, ETF flows, industrial demand and festivals.

**Timeline (new tab)**
- Past, today and the forecast on one chart: the real price, the call strip, today's live price, the forecast with its likely range, and what was predicted 30 days earlier for each day.
- Range 1M / 3M / 1Y / 3Y / All years, with Past / Present / Future tiles and tables.

**Every 5 minutes**
- The Mac job (`scripts/mac-schedule.sh install`) now checks every 5 minutes instead of twice a day. Metals are re-analysed every time; wheat makes one quick data.gov.in call (pausing 30 minutes after a 429), with a full fetch on new prices or every 6 hours. It publishes within 10 minutes of a change that matters, otherwise hourly. `install` removes the old WheatWise job. Keys for the Mac job (data.gov.in, Telegram, Anthropic) go in a git-ignored `.env`.
- The dashboard and the Mac app fetch live metal prices every 5 minutes (● live).
- GitHub Actions is now a backup, and skips its run when the Mac published in the last 3 hours.

**Dashboard**
- A commodity picker with an **All** overview: four cards and a "100 = a year ago" comparison chart.
- Links such as `#gold/timeline` can be bookmarked. Old `#today` links still open wheat.
- Trades and settings from WheatWise carry over in the same browser. Trades are kept per commodity.

**Mac app: Dharalu 2.0.0**
- ⚖️ in the menu bar, showing the commodity you pick (wheat, gold, silver or platinum) with its call and price.
- Each commodity has its own submenu: the live price, the proof, the track record, the briefing (with Copy), timing, and links to its dashboard and timeline.
- Alerts for each commodity on call changes and big moves (wheat 2.5%, gold 2%, silver and platinum 3%). Checks every 5 minutes by default.
- It reads the new `summary.json` and has a new icon: a gold balance weighing wheat against a ₹ coin.
- It replaces WheatWise.app; see guide/MAC_APP.md for upgrading.

**Agent**
- New `agent/metals.py`. `run.py` has `--quick` and `--if-stale`, writes `docs/data/summary.json`, and sends per-commodity Telegram alerts. A metal's new call must hold for two checks before it alerts.

## 1.3.1 - 18 Oct 2026

- **Dashboard header shows the price.** It ended in "₹ per quintal" with no number. It now shows today's benchmark price and the cheapest landed price at Srikakulam, e.g. *17 Oct 2026 · benchmark ₹2,693/qtl · landed ₹2,906/qtl*. The Mac app's window opens the dashboard, so it shows the new header too. The app itself is unchanged apart from the version number. The page now loads its script and styles with a version tag, so browsers and the app pick up changes straight away instead of running an old cached copy.

## 1.3.0 - 18 Oct 2026

**Prices kept refreshing on GitHub but stopped at 13 Oct.** data.gov.in refuses GitHub's servers, which are outside India. Each run showed ✅ but brought no new prices, and the dashboard looked fresh because only the "published" time changed.
- **Fetch from your Mac:** `scripts/mac-schedule.sh install` fetches and publishes at 12:00 and 19:00 (`run`, `status`, `uninstall` too). `scripts/mac-refresh.sh` does one fetch by hand. See guide/SETUP.md step 8.
- **Mac app:** ⚠︎ also appears when the newest mandi price is 3+ days old. The menu says which, and what to do.
- **Dashboard:** the header shows ⚠︎ *N days old* when prices are 3+ days old.
- **Agent:** when data.gov.in fails, the log says why (HTTP error, timeout, message).

## 1.2.1 - 15 Oct 2026

- **Sharper small icons.** At 16–64 px the app icon's drop shadow filled the whole image, leaving a faint grey
  square behind it in Finder lists, Spotlight and the menu. Every size is now shrunk from the full-size drawing,
  so the shadow keeps its proportions and the corners stay clear. The icon itself is unchanged.

## 1.2.0 - 15 Oct 2026

**Mac app**
- Settings menu is grouped (Menu bar, Alerts, General) with real switches, and segmented controls for Check every and Appearance. Same settings, same stored values.

**Dashboard**
- Theme button is now System / Light / Dark (System is the default and follows the device). Same saved setting as before, with "system" as a new value.
- Phone: the proof table now reflows into stacked rows (nothing clipped, every rule, value, source, test and points still shown); the header wraps neatly.
- Key numbers sit in an even grid (3 x 2, 2 x 3 or 1 column) instead of leaving one orphan tile.
- Muted grey text in light mode is darker, for readable contrast (4.5:1 or better).

## 1.1.0 - 15 Oct 2026

**Mac app**
- Settings › Appearance: System (follows macOS, Auto included), Light or Dark. Applies at once to the dashboard window and the app's own windows.

**Dashboard**
- No change: in a browser it still follows the system, with the existing ◐ toggle.

## 1.0.0 - 13 Oct 2026

First release.

**Agent**
- Twice-daily monitor on GitHub Actions, using Agmarknet data from data.gov.in.
- Chain-linked benchmark of Jabalpur, Indore and Kota, with an outlier filter.
- Six calls: STRONG BUY, BUY, **HOLD**, WAIT, SELL, STRONG SELL. HOLD means score 0 with the forecast + season still pointing up: keep your stock, don't add.
- Every call shows its proof: each rule's value, source, test and points.
- 45-day forecast with a likely range, and a no-peeking backtest against the "no change" guess.
- Seasonality learned from Agmarknet history.
- MSP floor with dated history; OMSS ceiling that only counts once sales start.
- Track record replayed day by day, for the last year and for the whole history since 2016. Live calls are graded after 30 days.
- Landed cost at Srikakulam for 16 source mandis.
- English + Telugu briefing, optionally written by Claude.
- Telegram alerts on a call change, a big daily move, and weekly.

**Dashboard**
- Seven tabs: Today, Forecast, Before you trade, My trades, Track record, Mandis, What to watch.
- Private trades in localStorage, with FIFO P&L, a timing score and lessons.

**Mac app**
- 🌾 menu-bar app with the call, proof, track record and briefing.
- Notifications on a call change or a big move.
- Dashboard window, Launch at Login, universal build, DMG installer.
