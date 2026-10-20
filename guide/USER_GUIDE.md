# User guide

Dashboard: https://sravankumartangudu.github.io/dharalu/

The top row picks the commodity: **All**, 🌾 **Wheat**, 🥇 **Gold**, 🥈 **Silver**, 💠 **Platinum**. Each button shows today's price and is coloured by its call (green buy · orange hold · grey wait · red sell). Under it are the tabs for that commodity. The address remembers where you are (for example `#gold/timeline`), so you can bookmark or share a page.

| | Unit | Price |
|---|---|---|
| 🌾 Wheat | ₹ per quintal (100 kg) | The **benchmark** (Jabalpur, Indore, Kota) and the cheapest **landed** price at Srikakulam |
| 🥇 Gold | ₹ per 10 g, 24 carat | World spot × ₹ rate + 6% import duty. GST (3%) on top |
| 🥈 Silver | ₹ per kg, 999 | The same |
| 💠 Platinum | ₹ per 10 g, 999.5 | The same, 6.4% duty |

**Every 5 minutes** the page checks for new data, and fetches the live world price for gold, silver and platinum. A pulsing green **● live** dot means the price shown is the live one. Prices are also re-checked when you come back to the tab.

## A daily routine

| When | What to do | Where |
|---|---|---|
| Every morning | Read all four calls; open the one you trade for its advice | *All*, or ⚖️ in the Mac menu bar |
| Before any big buy | Check the break-even price and the go/no-go checklist | *Before you trade* |
| After every buy or sale | Record it | *My trades* |
| Weekly (Monday alert) | Is the agent still being right? Anything to watch? | *Timeline*, *Agent track record*, *What to watch* |
| Every Sep/Oct | When the new wheat MSP is announced, update `config.json` | [CONFIG.md](CONFIG.md) |
| After each Union Budget (1 Feb) | If import duty or GST on metals changed, update `config.json` | [CONFIG.md](CONFIG.md#gold-silver-platinum) |

## The calls

| Call | What it means |
|---|---|
| **STRONG BUY / BUY** | Prices look set to rise by more than it costs you to hold. Buy, in parts |
| **HOLD** | Today's price is no bargain, but the forecast and the season still point up. **Keep what you have, don't add more** |
| **WAIT** | No clear edge either way. Buy only what you need; sell only if you need cash |
| **SELL / STRONG SELL** | Prices look set to soften. Sell in parts / book profit; don't stock up |

Each call gives two pieces of advice, because the right move depends on your position: **if you are buying** and **if you are holding**. Confidence (Low / Medium / High) depends on how strong the score is. It drops a level when there's less than 4 months of history, or when the forecast's 30-day direction has been right less than 55% of the time. Since 2.2 it is also capped by the call's own record: if past days with this call were barely more right than any day, confidence stays Low.

**Reading a call in 30 seconds** (Today tab, top right):
1. **The plain line**: why, in one sentence.
2. **🎯 What would change it**: e.g. *Turns WAIT if the price falls to ₹1,17,670 (−11.8%)*. A trigger that is far away means a settled call; a trigger 1–2% away means it could flip soon.
3. **📊 Its record**: past days with this call vs any day. *Edge +5 points* means a SELL was right 5 points more often than guessing "lower" on any day. Near 0 means the call adds little.
4. **🤔 Why … confidence**: the reasons for Low / Medium / High.
5. **⚖️ Without learned weights** (shown when it differs): the call if every rule counted the same.
6. **⏳** (metals, sometimes): the score has just crossed into a new call. It switches only if the next check agrees.

**Holding cost** - wheat: interest + godown rent + losses. Metals: the bank interest (fixed deposit) the money would have earned.

## All - the overview

- One card per commodity: the call, the price (live for metals), the 1-day change, and a sparkline of the last year with the 30-day forecast and **🔮 Why** (its biggest reason). Click a card to open it.
- **Compared - 100 = a year ago:** all four on one chart, each scaled to 100 a year ago, so you can see which rose most.

## Tabs

### Today · ఈరోజు
- **The call**, with the score gauge (the middle is 0; the ticks are the ±1 and ±3 call bands), confidence, and date of the latest prices.
- **The plain line, what would change it, its record, why this confidence**: see *Reading a call in 30 seconds* above.
- **🔄 What changed since <date>**: shown on a new prices day. Which rules moved (counted points then → now) and whether the call changed.
- **Saving for years** (metals): ADD / STEADY / GO SLOW for money you'll keep a year or more, its reason, its 1-year record, and the 5- and 10-year growth. Open *The long-term rules and their record* for each rule and whether it counts.
- **Briefing** in English / తెలుగు. "Briefing by claude" means the AI wrote it; "by rules" means the built-in template did.
- **Why this call - the proof.** One row per rule:
  - *What the data shows today*: the real number and its source.
  - *Test used*: the threshold.
  - *Points*: what the rule added or took away.
  - *Weight*: earned from the rule's own past record (×2, ×1, ×½, or ×0 when it did worse than guessing). Hover it to see the record.
  - *Counted*: points × weight. *trend cap* means the forecast and trend rules together hit the ±2 limit.

  Add up the counted points and you get the score.
- **Has this worked before?** How often the same call was right in the replay. If the last year had fewer than 10 such days, it quotes the whole history.
- **Key numbers** -
  - wheat: benchmark price and changes, 30-day forecast, cheapest landed source, MSP, your margin, holding cost;
  - metals: the India price (live), with GST, the world price in US$ and the ₹ rate, 30-day forecast, holding cost.
- **Chart:** the last year, a **Now** dot at today's (live) price, and the next 45 days with the likely range (shaded).

### Timeline · past → future
Everything on one time axis:
- **Range:** 1M · 3M · 1Y · 3Y · All (remembered).
- **Past** (solid line): the actual price. Under it, a **strip** coloured by the call the agent made (or would have made, in the replay) each day.
- **Now:** today's price, live for metals.
- **Future** (dashed line + shaded band): the 45-day forecast with its likely range.
- **Predicted 30 days earlier** (dotted line): what the agent forecast for each day, 30 days before, using only what it knew then. Where it hugs the real line, the forecasts were good. Hover any point for the date, price, call and forecast.
- **Past / Present / Future** tiles: the change over the range, today's price (live for metals), and the 30-day forecast.
- **Tables** (click to open): the forecast day by day, and each recent day's 30-days-earlier prediction next to the real price and the miss.
- **🔮 Why the forecast says this:** the expected move at 7, 14 and 30 days split into its parts (recent trend, season, last few days' average), a sentence on each, how far to trust it, what it adds to today's call and what it can't see (news, policy).

### Forecast · అంచనా
- The 45-day forecast with its likely range (the band widens the further ahead it goes).
- **🔮 Why the forecast says this** - the same card as on the Timeline.
- **How accurate has it been?** The average error at 7, 14 and 30 days (and how often it called the direction right), next to the "price stays the same" guess. If the forecast doesn't beat that guess at 30 days, its vote is cut to 1 point.
- **Seasonal pattern:** which months are usually cheap or dear, learned from the price history.

### Before you trade (pre-analysis)
**Wheat:** pick the source mandi, price, quantity, freight and holding days. You get:
- the landed cost at Srikakulam and the total money needed;
- holding cost for the period, and the **break-even sell price**;
- profit in the pessimistic / likely / optimistic case (from the forecast range).

**Gold / silver / platinum:** enter the grams, the rate (it starts at today's live price), the making charge or premium, GST, the days you'll hold it, the buy-back cut when you sell, and optionally your planned sell rate. You get:
- **total you pay** (metal + making + GST);
- what you get back when you sell (after the buy-back cut), and the bank interest you give up;
- the **market rate you need to break even**, and the bad / likely / good cases.

Coins and bars usually carry a 1–3% premium. Jewellery making charges (often 8–20%) and GST are not paid back when you sell, so the price has to rise a lot before jewellery makes money.

Both end with a **go/no-go checklist** (does the call support buying? does the expected rise beat the cost? … ). ✅ means nearly all checks pass, ⚠️ that it's mixed (consider a smaller amount), and ❌ that the numbers are against the trade.

### My trades · after (post-analysis)
Each commodity has its own list.
- Enter each **buy** and **sell** (date, quantity, price, from/to, notes). Wheat quantities are in quintals; metal quantities in grams, at the price per 10 g / kg shown.
- **P&L** is first-in-first-out: each sale is matched with your oldest unsold buy, after holding costs for the days held. A sale with no recorded buy is flagged and left out of P&L.
- **Timing score (0-100):** where your trade sat among the prices 30 days either side of it. For a buy, 100 means the cheapest day; for a sale, the dearest. The score is marked * until 30 days have passed.
- **Agent's call that day:** green if you followed it, orange if you went against it.
- **Lessons:** how much of your profit holding costs ate, how many sales lost money, your average holding period, and how well your sales were timed.
- **Export CSV / Import CSV** to back up or move your trades (`dharalu-<commodity>-trades.csv`). The columns are `date,type,qty,price,place,notes`.

**Your trades are private.** They are stored only in this browser (or in the Mac app), never on GitHub. A different phone or browser starts empty; use Export and Import to move them. Trades entered in WheatWise 1.x are carried over as wheat trades.

### Agent track record
- **Last year:** every day re-run with only the data known that day. The table shows the average price move 30 days later after each call, how often the price rose, and how often the rise beat the holding cost.
- **Whole history:** the same replay over every day there's data for.
- **Learned weights vs every rule counting the same:** the replay done both ways, with days, right % and **edge** (points better than any day) for each kind of call. Above 0 = the call adds something.
- **Each rule's own record:** every rule's votes, how often it was right vs the usual rate, and today's weight.
- **Chart:** the price with the call strip underneath.
- **Live calls:** the agent's real calls, graded 30 days later.
  - BUY and HOLD are right if the price rose.
  - SELL is right if it fell.
  - WAIT is right if it moved less than 3%.

How to read it: a useful BUY row has a positive average move and "price rose" well above 50%. If the rows stop looking like that, trust the call less.

### Mandis & landed cost (wheat only)
- **Your Srikakulam selling rate:** type your local rate to see your margin on every source.
- The **16 source mandis**, sorted by landed cost. Each shows the mandi price, fee, freight, extras and landed total, plus the date of its latest report.
- Click a mandi for its price chart.
- **All-India today:** state medians from today's feed.

### What to watch
The outside things that move each price, with a status colour and a source to check.
- **Wheat:** MSP and FCI procurement, OMSS sales, central pool stocks, stock limits, trade policy, sowing and weather, the festival and wedding calendar, plus a month-by-month "wheat year".
- **Metals:** the world price, the rupee, import duty and GST, US interest rates and the dollar, festival and wedding demand - then per metal: central-bank buying and ETF flows (gold), industrial demand and the gold/silver ratio (silver), car catalysts, mine supply and selling it back (platinum). Each has a "year at a glance".

## Share
**Share** opens your phone's share sheet (WhatsApp etc.) with the call for the commodity you're looking at and the link. On a computer it copies them.

## Light / dark
The ◐ button cycles System (follows your device, the default), Light and Dark.
