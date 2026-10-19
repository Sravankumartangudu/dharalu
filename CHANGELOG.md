# Changelog

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
