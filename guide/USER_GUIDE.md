# User guide

Dashboard: https://sravankumartangudu.github.io/wheatwise/ · All prices are **₹ per quintal (100 kg)**.

The header at the top always shows the latest mandi day, the **benchmark** price (median of Jabalpur, Indore, Kota) and the cheapest **landed** price at Srikakulam (mandi price + freight).

## A daily routine

| When | What to do | Where |
|---|---|---|
| Every morning (after 12:30 IST) | Read the call and the advice for your case | *Today*, or 🌾 in the Mac menu bar |
| Before any big buy | Check the break-even price and the go/no-go checklist | *Before you trade* |
| After every buy or sale | Record it | *My trades* |
| Weekly (Monday alert) | Is the agent still being right? Any government moves? | *Agent track record*, *What to watch* |
| Every Sep/Oct | When the new MSP is announced, update `config.json` | [CONFIG.md](CONFIG.md) |

## The calls

| Call | What it means |
|---|---|
| **STRONG BUY / BUY** | Prices look set to rise by more than it costs you to hold stock. Buy, in lots |
| **HOLD** | Today's price is no bargain, but the forecast and the season still point up. **Keep your stock, don't add more** |
| **WAIT** | No clear edge either way. Buy only what you need; sell only if you need cash |
| **SELL / STRONG SELL** | Prices look set to soften. Sell in parts; don't stock up |

Each call gives two pieces of advice, because the right move depends on your position: **if you are buying** and **if you are holding stock**. Confidence (Low / Medium / High) depends on how strong the score is. It drops a level when there's less than 4 months of history, or when the forecast's 30-day direction has been right less than 55% of the time.

## Tabs

### Today · ఈరోజు
- **The call**, with the score bar, confidence, and date of the latest prices.
- **Briefing** in English / తెలుగు. "Briefing by claude" means the AI wrote it; "by rules" means the built-in template did.
- **Why this call - the proof.** One row per rule:
  - *What the data shows today*: the real number and its source.
  - *Test used*: the threshold.
  - *Points*: what the rule added or took away.

  Add up the points and you get the score.
- **Has this worked before?** How often the same call was right in the replay. If the last year had fewer than 10 such days, it quotes the whole history since 2016.
- **Key numbers:**
  - benchmark price and its 1/7/30-day change;
  - 30-day forecast;
  - cheapest landed source;
  - MSP;
  - your margin (enter your selling rate in *Mandis*);
  - 30-day holding cost.
- **Chart:** the last 12 months plus the next 45 days, with the likely range.

### Forecast · అంచనా
- The 45-day forecast with its likely range (the band widens the further ahead it goes).
- **How accurate has it been?** The average error at 7, 14 and 30 days (and how often it called the direction right), next to the "price stays the same" guess. If the forecast doesn't beat that guess at 30 days, its vote is cut to 1 point.
- **Seasonal pattern:** which months are usually cheap or dear, learned from your own Agmarknet history.

### Before you trade (pre-analysis)
Pick the source mandi, price, quantity, freight and holding days. You get:
- the landed cost at Srikakulam and the total money needed;
- holding cost for the period, and the **break-even sell price**;
- profit in the pessimistic / likely / optimistic case (from the forecast range);
- a **go/no-go checklist**:
  - does the agent's call support buying?
  - does the expected rise beat the holding cost?
  - is this among the cheapest sources (within 2%)?
  - is the price close to the MSP floor (within 8%)?
  - is there a margin at your Srikakulam selling rate?

  ✅ means nearly all checks pass, ⚠️ that it's mixed (consider a smaller lot), and ❌ that the numbers are against the trade.

### My trades · after (post-analysis)
- Enter each **buy** and **sell** (date, quantity, price, from/to, notes).
- **P&L** is first-in-first-out: each sale is matched with your oldest unsold buy, after holding costs for the days held. A sale with no recorded buy is flagged and left out of P&L.
- **Timing score (0-100):** where your trade sat among the benchmark prices 30 days either side of it. For a buy, 100 means the cheapest day; for a sale, the dearest. The score is marked * until 30 days have passed.
- **Agent's call that day:** green if you followed it, orange if you went against it. Buying on a SELL day or selling on a HOLD day counts as against.
- **Lessons:** how much of your profit holding costs ate, how many sales lost money, your average holding period, and how well your sales were timed.
- **Export CSV / Import CSV** to back up or move your trades. The columns are `date,type,qty,price,place,notes`.

**Your trades are private.** They are stored only in this browser (or in the Mac app), never on GitHub. A different phone or browser starts empty; use Export and Import to move them.

### Agent track record
- **Last year:** every day re-run with only the data known that day. The table shows the average price move 30 days later after each call, how often the price rose, and how often the rise beat the holding cost.
- **Whole history since 2016:** the same replay over every day there's data for.
- **Chart:** green tint marks BUY days, orange HOLD days, red SELL days.
- **Live calls:** the agent's real calls, graded 30 days later.
  - BUY and HOLD are right if the price rose.
  - SELL is right if it fell.
  - WAIT is right if it moved less than 3%.

How to read it: a useful BUY row has a positive average move and "price rose" well above 50%. If the rows stop looking like that, trust the call less.

### Mandis & landed cost
- **Your Srikakulam selling rate:** type your local rate to see your margin on every source.
- The **16 source mandis**, sorted by landed cost. Each shows the mandi price, fee, freight, extras and landed total, plus the date of its latest report.
- Click a mandi for its price chart.
- **All-India today:** state medians from today's feed, with the southern consumer states marked as "selling" for comparison.

### What to watch
The outside things that move wheat prices, each with its status and a source to check:
- MSP and FCI procurement;
- OMSS sales;
- central pool stocks;
- stock limits;
- trade policy;
- sowing and weather;
- the festival and wedding calendar.

Also a month-by-month "wheat year" for a Srikakulam trader.

## Share
**Share** opens your phone's share sheet (WhatsApp etc.) with today's call and the link. On a computer it copies them.

## Light / dark
The ◐ button cycles System (follows your device, the default), Light and Dark.
