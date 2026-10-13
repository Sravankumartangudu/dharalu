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

## Alerts

| Key | Default | Meaning |
|---|---|---|
| `alerts.daily_move_pct` | 2.5 | Telegram alert if the benchmark moves this much in a day |
| `alerts.weekly_summary_weekday` | 0 | Day for the weekly summary (0 = Monday … 6 = Sunday) |
