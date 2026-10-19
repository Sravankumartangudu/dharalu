# config.json

Every cost in `config.json` is a **starting estimate**. Replace each one with what you really pay; the calls are only as good as these numbers.

To edit on GitHub: open `config.json`, click the ✏️ pencil, change the numbers, then *Commit changes*. The next run (or *Actions → Run workflow*) uses the new values. Keep the JSON shape: commas between items, no comma after the last one.

## Costs - landed price at Srikakulam

| Key | Default | Meaning |
|---|---|---|
| `freight.rate_per_qtl_per_km` | 0.30 | Truck freight in ₹ per quintal per km (₹3 per tonne-km). **Ask your transporter** |
| `costs.source_mandi_fee_pct` | 1.7 | Mandi tax + nirashrit charge at the source mandi, as % of price |
| `costs.handling_per_qtl` | 25 | Loading and unloading, ₹/qtl |
| `costs.bags_per_qtl` | 15 | Gunny bags, ₹/qtl |
| `costs.brokerage_per_qtl` | 10 | Commission, ₹/qtl |

## Holding cost - is stocking worth it?

| Key | Default | Meaning |
|---|---|---|
| `carrying.interest_pct_per_month` | 1.25 | Interest on the money tied up (15% a year) |
| `carrying.storage_per_qtl_per_month` | 8 | Godown rent, ₹/qtl/month |
| `carrying.loss_pct_per_month` | 0.25 | Moisture, rodent and handling loss |

A BUY or HOLD only makes sense if prices are expected to rise by more than this.

## Source mandis

Each entry in `source_markets`:

| Key | Meaning |
|---|---|
| `name` | Agmarknet market name (as in today's feed, e.g. `Katni APMC`) |
| `old_name` | Name before Nov 2025, used to download older history |
| `state` | State |
| `km` | Road distance to Srikakulam |
| `long_history` | `true` = part of the benchmark (Jabalpur, Indore, Kota). Change with care: the track record is built on these |
| `freight_override` | Optional fixed freight in ₹/qtl if you have a quote, e.g. `"freight_override": 310` |

To add a mandi, copy an entry, change the name, state and km, then run with *bootstrap* ticked once to fetch its history.

`state_km` is the rough distance per state, used for the all-India state table. `consumer_states` lists the states shown as "selling" markets for comparison.

## MSP - update every year

The Cabinet announces the next season's wheat MSP every Sep/Oct. When it does:
1. Add a row to `msp.history` that starts on 1 March of the harvest year:
   ```json
   { "from": "2028-03-01", "value": 2700, "season": "RMS 2028-29" }
   ```
2. Update `msp.value` / `msp.season` (the current floor) and `msp.next_value` / `msp.next_season` (the announced one).

`history` matters: the track record replays each past day with the MSP that applied then.

## OMSS - when FCI sells wheat

When FCI starts weekly OMSS e-auctions (usually in the lean season), open-market prices rarely stay above the reserve price plus freight. When sales start:
```json
"omss": { "reserve_price": 2550, "active_from": "2026-11-05", "note": "..." }
```
Set both back to `null` when sales stop. The −1 rule only counts on days on or after `active_from`.

## Gold, silver, platinum

Each metal has its own block under `metals` (`gold`, `silver`, `platinum`):

| Key | Default | Meaning |
|---|---|---|
| `grams` | 10 / 1000 / 10 | The unit the price is shown for: gold per 10 g, silver per kg, platinum per 10 g |
| `duty_pct` | 6 / 6 / 6.4 | Import duty (basic customs duty + AIDC) since the July 2024 Budget. **Check after every Union Budget** (1 Feb) |
| `gst_pct` | 3 | GST paid on top when you buy, shown as "with GST" |
| `sell_discount_pct` | 1 | What a jeweller or dealer usually knocks off when you sell back. Used in *Before you trade* |
| `interest_pct_per_month` | 0.6 | What the money would earn in the bank (about 7.2% a year). This is the metal's holding cost |
| `move_alert_pct` | 2 / 3 / 3 | Alert if the price moves this much in a day |
| `futures` | `GC=F` / `SI=F` / `PL=F` | Yahoo Finance symbol for the price history. Change with care: the track record is built on it |
| `spot` | `XAU` / `XAG` / `XPT` | gold-api.com symbol for the live price |
| `label`, `telugu`, `emoji`, `unit`, `purity` | | How it is named and shown |

`metals.fx_symbol` (`INR=X`) is the Yahoo Finance symbol for the US$/₹ rate.

After a Budget changes duty or GST: edit the numbers, then run `python3 agent/run.py --offline` (or wait for the next run). The whole price history is recomputed with the new duty, so the chart and the track record stay consistent.

## Alerts

| Key | Default | Meaning |
|---|---|---|
| `alerts.daily_move_pct` | 2.5 | Wheat: Telegram (and Mac) alert if the benchmark moves this much in a day |
| `alerts.weekly_summary_weekday` | 0 | Day for the weekly summary (0 = Monday … 6 = Sunday) |
