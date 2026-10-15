# Changelog

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
