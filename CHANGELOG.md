# Changelog

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
