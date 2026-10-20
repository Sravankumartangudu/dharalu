# Dharalu for Mac

A menu-bar app: **⚖️ 🌾 SELL ₹2,693**, always in view. Click it for all four calls - wheat, gold, silver and platinum - each with the proof, the track record and the briefing. Gold, silver and platinum are checked **live every 5 minutes**. It notifies you when a call changes or a price jumps, and it opens the full dashboard in its own window.

## Requirements
macOS 13 Ventura or newer, on Apple Silicon or Intel (it's a universal app). No account or key is needed: it reads the public dashboard data and the free gold-api.com price.

## Install

1. Download **`Dharalu-<version>.dmg`** from [Releases](https://github.com/Sravankumartangudu/dharalu/releases/latest).
2. Open it and drag **Dharalu** onto **Applications**.
3. Open Dharalu from Applications. The app isn't notarized by Apple, so the first time macOS says it *can't be verified*:
   - Click **Done** (or Cancel).
   - Go to **System Settings → Privacy & Security**, scroll down, and click **Open Anyway** next to Dharalu. Confirm with your password.
   - You only do this once.
4. Click **Allow** when it asks to send notifications.
5. Optional: *⚖️ → Settings → Launch at login*, so it always runs.

**Update:** download the new DMG and drag it over the old app (choose *Replace*). Your settings and trades are kept.

**Coming from WheatWise 1.x?** Dharalu replaces it. Quit WheatWise (🌾 → Quit), move `/Applications/WheatWise.app` to the Bin, and turn off its Launch at Login if you had it on. Settings start fresh (the default is wheat in the menu bar, checking every 5 minutes). Trades you entered in the WheatWise app window stay in that app's storage: before removing it, use *My trades → Export CSV* there, then *Import CSV* in Dharalu.

**Uninstall:** quit it (⚖️ → Quit Dharalu), then move `/Applications/Dharalu.app` to the Bin.

## The menu

| Item | What |
|---|---|
| 🌾 **Wheat  SELL  ₹2,693/qtl  +0.4%** ▸ | One row per commodity: the call (coloured green buy · orange hold · grey wait · red sell), today's price and the 1-day change. Metals show the **live** price, with ● and the change since the last close. ✓ marks the one in the menu bar |
| … ▸ the submenu | Everything for that commodity (below) |
| **Open Dashboard…** ⌘D | The full dashboard (the overview) in a window |
| Open in Browser | The same, in your browser |
| **Refresh Now** ⌘R | Check now |
| Checked … · agent ran … · every 5 min | When the app last checked, and when the agent last published |
| **Settings ▸** | See below |
| Help - How to Use | Opens this page |
| Quit Dharalu ⌘Q | |

Each commodity's submenu:

| Item | What |
|---|---|
| **🥇 Gold · బంగారం - STRONG SELL · వెంటనే అమ్మండి** | The call in English and Telugu |
| Score · confidence · date | e.g. *Score −2 of ±6 · confidence Medium · 20 Oct 2026* |
| The plain line | Why, in one sentence. A ⏳ line when a new call is waiting for its second check |
| If buying / If holding | The advice for each case |
| 🎯 · 📊 · 🤔 | What would change the call, its past record vs any day, why this confidence |
| 🔄 · 📅 | The call on the previous prices day (when it changed); metals: *Saving for years* (ADD / STEADY / GO SLOW) |
| Live … at 18:52 · since last close … | Metals: the live price and how far it has moved today; then the agent's price with its 7- and 30-day changes |
| Key numbers | 30-day forecast with its likely range and **🔮 Why** (e.g. *Expected to fall about 5.7% in 30 days. Biggest reason: recent trend (−4.2%)*); wheat: cheapest landed source and MSP; metals: price with GST and the world price × ₹ rate; holding cost |
| **Why this call - the proof ▸** | Every rule with its value, test and points × weight = counted (e.g. *−1 ×0.5 = −0.5*), the trend cap note, then the total and the equal-weights call when it differs |
| **Has this worked before? ▸** | How today's call did in the replay, the live record, and *Open the full track record…* |
| **Today's briefing ▸** | The note in English and Telugu, with *Copy English* / *Copy తెలుగు* for WhatsApp |
| Timing | When it is usually cheapest and dearest |
| Open … in Dashboard… / Timeline - past, now, forecast… | That commodity's page in the dashboard window |
| Show … in the Menu Bar | Make this the one in the menu bar |

The menu-bar title shows **⚠︎** when the data can't be loaded or the agent hasn't published for 6 hours. A commodity's submenu also warns when its newest price is old: wheat 3+ days (mandis skip Sundays and holidays), metals 4+ days (markets close at weekends). **Refresh** reloads what the agent published and the live metal prices. It doesn't fetch new mandi prices; for those, see [SETUP.md step 8](SETUP.md#8-run-the-agent-from-your-mac-important).

## Settings

The Settings menu is grouped: **Menu bar**, **Alerts** and **General**. On/off settings are switches; the rest are segmented controls.

| Setting | Default | What |
|---|---|---|
| Show | 🌾 Wheat | Which commodity the menu bar shows: Wheat / Gold / Silver / Platinum |
| Show price | On | `⚖️ 🌾 SELL ₹2,693`, or just `⚖️ 🌾 SELL` |
| Notify on call changes / big moves | On | For every commodity: notify when its call changes, or when its price moves a lot in a day - wheat 2.5%, gold 2%, silver and platinum 3% (once a day each). Clicking a notification opens that commodity |
| Check prices every | 5 min | 5 / 15 / 30 minutes or 1 hour. Each check reloads the agent's data and the live gold, silver and platinum prices |
| Launch at login | Off | Start with your Mac |
| Appearance | System | System (follows macOS, Auto included) / Light / Dark. Changes at once, in the menu and the dashboard window |
| Data Source… | this repo's dashboard | Change it only if you run your own fork: `https://<you>.github.io/dharalu/data/summary.json` |

A live price more than 15% away from the agent's last price is ignored as a bad tick, and the agent's price is shown instead.

## Your trades in the app

The dashboard window works like the website. **Trades you enter in the app are stored in the app**, separately from the trades in your browser. To move them, use *My trades → Export CSV* in one and *Import CSV* in the other.

## Menu-bar folder (Nexus)

If you use the Nexus menu-bar folder, Dharalu appears inside it like the other fleet apps.

## Build from source

You need the Xcode Command Line Tools (`xcode-select --install`).

```bash
cd mac
./build.sh               # builds Dharalu.app for this Mac
./build.sh --universal   # Apple Silicon + Intel
./package.sh             # universal build + dist/Dharalu-<version>.dmg
open Dharalu.app
```

- `swift Icon/make_icon.swift` redraws the icon (a gold balance weighing wheat against a ₹ coin).
- The version is set in `build.sh`.
- The app is ad-hoc signed; it isn't notarized.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Dharalu can't be opened" / "unverified developer" | System Settings → Privacy & Security → **Open Anyway** (once) |
| No ⚖️ in the menu bar | The menu bar may be full: quit some menu-bar apps, or hold ⌘ and drag icons to make room. If you use a menu-bar folder or manager (Nexus, Bartender), look there |
| No notifications | System Settings → Notifications → Dharalu → Allow. Also check ⚖️ → Settings → Notify on call changes / big moves |
| ⚠︎ next to the price | Open the menu: it says why. *Hours old* or *can't load*: check your internet connection, then `scripts/mac-schedule.sh status` on the Mac that runs the agent. *Price is N days old* (in a submenu): for wheat run `scripts/mac-schedule.sh run`; for metals it is normal at weekends |
| Metal prices have no ● live dot | gold-api.com couldn't be reached, or sent a price that looked wrong; the agent's last price is shown. It tries again at the next check |
| Launch at Login won't turn on | Move the app to /Applications first, then try again |
