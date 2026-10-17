# WheatWise for Mac

A menu-bar app: **🌾 SELL ₹2,590**, always in view. Click it for the call, the proof, the track record and the briefing. It notifies you when the call changes, and it opens the full dashboard in its own window.

## Requirements
macOS 13 Ventura or newer, on Apple Silicon or Intel (it's a universal app). No account or key is needed: it reads the public dashboard data.

## Install

1. Download **`WheatWise-<version>.dmg`** from [Releases](https://github.com/Sravankumartangudu/wheatwise/releases/latest).
2. Open it and drag **WheatWise** onto **Applications**.
3. Open WheatWise from Applications. The app isn't notarized by Apple, so the first time macOS says it *can't be verified*:
   - Click **Done** (or Cancel).
   - Go to **System Settings → Privacy & Security**, scroll down, and click **Open Anyway** next to WheatWise. Confirm with your password.
   - You only do this once.
4. Click **Allow** when it asks to send notifications.
5. Optional: *🌾 → Settings → Launch at Login*, so it always runs.

**Update:** download the new DMG and drag it over the old app (choose *Replace*). Your settings and trades are kept.

**Uninstall:** quit it (🌾 → Quit), then move `/Applications/WheatWise.app` to the Bin.

## The menu

| Item | What |
|---|---|
| **SELL · అమ్మండి** | Today's call in English and Telugu, coloured (green buy · orange hold · grey wait · red sell) |
| Score · confidence · date | e.g. *Score −2 of ±7 · confidence Low · 13 Oct 2026* |
| Buying / Holding | The advice for each case |
| Key numbers | Benchmark price and its changes, 30-day forecast, cheapest landed source, MSP |
| **Why this call - the proof ▸** | Every rule with its value, test and points, then the total |
| **Has this worked before? ▸** | How the same call did in the replay (BUY / HOLD / WAIT / SELL), plus the live record |
| **Today's briefing ▸** | The note in English and Telugu, with *Copy English* / *Copy తెలుగు* for WhatsApp |
| Timing | When wheat is usually cheapest and dearest |
| **Open Dashboard…** ⌘D | The full dashboard in a window |
| Open in Browser | The same, in your browser |
| **Refresh** ⌘R | Check now |
| Checked … · agent ran … | When the app last checked, and when the agent last published |
| **Settings ▸** | See below |
| Help - How to Use | Opens this page |
| Quit WheatWise ⌘Q | |

The menu-bar title shows **⚠︎** when the data can't be loaded, when the agent hasn't published for 36 hours, or when the newest mandi price is 3 or more days old. **Refresh** reloads what the agent published; it doesn't fetch new prices. For those, see [SETUP.md step 8](SETUP.md#8-fetch-prices-from-your-mac-important).

## Settings

The Settings menu is grouped: **Menu bar**, **Alerts** and **General**. On/off settings are switches; Check every and Appearance are segmented controls.

| Setting | Default | What |
|---|---|---|
| Show price | On | `🌾 SELL ₹2,590`, or just `🌾 SELL` |
| Notify on signal change / big moves | On | Notify when the call changes, or when the price moves 2.5% or more in a day |
| Launch at login | Off | Start with your Mac |
| Appearance | System | System (follows macOS, Auto included) / Light / Dark. Changes at once |
| Check every | 30 min | 15 / 30 / 60 / 120 minutes. The agent publishes twice a day, so 30 is plenty |
| Data Source… | this repo's dashboard | Change it only if you run your own fork: `https://<you>.github.io/wheatwise/data/latest.json` |

## Your trades in the app

The dashboard window works like the website. **Trades you enter in the app are stored in the app**, separately from the trades in your browser. To move them, use *My trades → Export CSV* in one and *Import CSV* in the other.

## Menu-bar folder (Nexus)

If you use the Nexus menu-bar folder, WheatWise appears inside it like the other fleet apps.

## Build from source

You need the Xcode Command Line Tools (`xcode-select --install`).

```bash
cd mac
./build.sh               # builds WheatWise.app for this Mac
./build.sh --universal   # Apple Silicon + Intel
./package.sh             # universal build + dist/WheatWise-<version>.dmg
open WheatWise.app
```

- `swift Icon/make_icon.swift` redraws the icon.
- The version is set in `build.sh`.
- The app is ad-hoc signed; it isn't notarized.

## Troubleshooting

| Problem | Fix |
|---|---|
| "WheatWise can't be opened" / "unverified developer" | System Settings → Privacy & Security → **Open Anyway** (once) |
| No 🌾 in the menu bar | The menu bar may be full: quit some menu-bar apps, or hold ⌘ and drag icons to make room. If you use a menu-bar folder or manager (Nexus, Bartender), look there |
| No notifications | System Settings → Notifications → WheatWise → Allow. Also check 🌾 → Settings → Notify on Signal Change / Big Moves |
| ⚠︎ next to 🌾 | Open the menu: it says why. *Prices are N days old*: run `scripts/mac-schedule.sh run` in the repo, and check the job is installed. *Hours old* or *can't load*: check your internet connection, then GitHub *Actions* for a failed run |
| Launch at Login won't turn on | Move the app to /Applications first, then try again |
