# FAQ and troubleshooting

## About the calls

**Should I just do what it says?**
No. Treat it as a well-informed second opinion. It only sees mandi prices, the season, MSP and OMSS. It knows nothing about a broker's quote, your cash position, or news it wasn't given. Read the proof table and decide.

**Why is confidence "Low" so often?**
Wheat prices are hard to forecast. Confidence is Low when the score is small, or when the forecast hasn't beaten "price stays the same" in the backtest. That honesty is on purpose.

**What is the difference between HOLD and WAIT?**
Both have score 0.
- **HOLD:** the forecast and season still point up. Keep your stock, but don't buy more at today's price.
- **WAIT:** no clear edge either way.

See [HOW_IT_WORKS.md](HOW_IT_WORKS.md#6-the-score).

**The call changed from yesterday. Why?**
Compare the proof table with yesterday's (or read the Telegram alert). Usually one rule crossed its threshold. For example, the price moved into the dearest 15% of the year.

**The track record shows only a handful of HOLD days last year.**
HOLD needs a specific mix of rules, so it's rarer than the others. That's why the dashboard also shows the **whole history since 2016**, and quotes it when the last year has fewer than 10 such days.

**Why no Srikakulam mandi price?**
Andhra Pradesh hasn't reported wheat mandi prices since 2017; it buys wheat from other states. So WheatWise works out the landed cost from 16 source mandis. Enter your local selling rate in *Mandis* to see your margin.

## Data

**The dashboard shows an old date.**
- Mandis don't report on Sundays and holidays, and data.gov.in is sometimes late or down. The agent then analyses the data it already has, and tries again at the next run.
- If the date is more than 2 days old, open GitHub → *Actions* and look for red ❌ runs.

**A mandi is missing from the landed-cost table.**
It hasn't reported in the last 7 days.

**The first history download is very slow.**
You're on the public sample key (10 rows per call). Add your own `DATA_GOV_IN_KEY` ([SETUP.md](SETUP.md#3-get-a-datagovin-key)) and re-run with *bootstrap* ticked.

## Alerts

**No Telegram messages.**
1. Both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` must be set.
2. You must have sent the bot a message first. For a group, the bot must be in the group.
3. Check the run log in *Actions*: it prints whether the alert was sent.

**Too many or too few alerts.**
Change `alerts.daily_move_pct` in `config.json` (default 2.5%).

## Trades

**My trades disappeared.**
They live in the browser you entered them in. A different browser, a private window, clearing site data, or the Mac app each has its own copy. Back up with *Export CSV* now and then.

**A sale says "sold with no recorded purchase".**
Enter the buy that stock came from (with its date), and P&L will include it.

## GitHub

**"Workflows aren't being run on this forked repository."**
Open *Actions* and click **I understand my workflows, go ahead and enable them**.

**GitHub stopped the schedule.**
GitHub pauses scheduled workflows in repositories with no activity for 60 days. The agent's own data commits count as activity, so this rarely happens. If it does: *Actions → WheatWise monitor → Enable workflow*.

**A run failed with a push error.**
`.github/save.sh` retries 3 times, and the next run catches up. Nothing is lost.

## Mac app
See [MAC_APP.md](MAC_APP.md#troubleshooting).
