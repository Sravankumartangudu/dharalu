# FAQ and troubleshooting

## About the calls

**Should I just do what it says?**
No. Treat it as a well-informed second opinion. For wheat it only sees mandi prices, the season, MSP and OMSS; for metals, the world price, the rupee and the season. It knows nothing about a broker's quote, your cash position, or news it wasn't given. Read the proof table and decide.

**Why is confidence "Low" so often?**
Prices are hard to forecast. Confidence is Low when the score is small, when the forecast hasn't beaten "price stays the same" in the backtest, or (since 2.2) when past days with this call were barely more right than any day. That honesty is on purpose.

**Why is the score a fraction, like +1.5?**
Since 2.2 each rule's points are multiplied by a weight learned from its own record (×2, ×1, ×½ or ×0), so counted points can be halves. The calls use bands: +1 up to +3 is BUY, between −1 and +1 is HOLD or WAIT, and so on.

**Why does a rule show points but count 0?**
Its weight is ×0: on past days it was right less often than a blind guess. It is still shown so you can see what it says. The *Agent track record* tab has each rule's record.

**Gold says SELL but "Saving for years" says GO SLOW, not sell. Which one?**
They answer different questions. The call is about the next 30 days. *Saving for years* is about money you'll keep a year or more. Long-term metal buyers usually keep regular small buys and avoid one big purchase when it says GO SLOW.

**Did the learned weights make it better?**
Mostly, but not everywhere. The *Agent track record* tab replays both ways. Silver and platinum BUY/SELL improved a lot. Gold's SELL and HOLD improved but its BUY got worse, and platinum HOLD got worse. See [HOW_IT_WORKS.md](HOW_IT_WORKS.md#7-track-record---no-peeking).

**What is the difference between HOLD and WAIT?**
Both have a score between −1 and +1.
- **HOLD:** the forecast and season still point up. Keep your stock, but don't buy more at today's price.
- **WAIT:** no clear edge either way.

See [HOW_IT_WORKS.md](HOW_IT_WORKS.md#6-the-score).

**The call changed from yesterday. Why?**
Look at **🔄 What changed since …** on the Today tab: it lists the rules that moved. Usually one rule crossed its threshold. For example, the price moved into the dearest 15% of the year, or the rupee moved more than 1% in a month.

**The track record shows only a handful of HOLD days last year.**
HOLD needs a specific mix of rules, so it's rarer than the others. That's why the dashboard also shows the **whole history** (wheat since 2016, metals about 10 years), and quotes it when the last year has fewer than 10 such days.

**Why no Srikakulam (or Hyderabad) mandi price?**
Andhra Pradesh hasn't reported wheat mandi prices since 2017; it buys wheat from other states. Telangana reports none either. So Dharalu works out the landed cost from 16 source mandis, for the place you pick. Enter your local selling rate in *Mandis* to see your margin.

**Does the call change when I switch to Hyderabad?**
No. The buy / hold / sell call reads the benchmark mandi price (Jabalpur, Indore, Kota), which is the same for everyone. The place changes the landed cost, the margins and the 📍 lines. Hyderabad is closer to the MP mandis, so wheat lands there about ₹50-90/qtl cheaper than in Srikakulam. The Hyderabad km are estimates: replace them with your transporter's in `config.json` → `places`.

**Are gold and silver dearer in Hyderabad?**
Dharalu's price is the same: the all-India import price. Local jewellers' rates differ a little by city (their premium), and jewellery adds making charges and GST.

**Why does the forecast say the price will rise (or fall)?**
Open 🔮 *Why the forecast says this* on the Timeline or Forecast tab. The move is split into the recent trend, the season and the last few days' average, with the biggest named as the main reason. The forecast reads only the price's own history, so news and policy changes (MSP, duty, US rates…) are not in it. When the card says it is NOT better than "price stays the same", trust the range more than the single number.

## Gold, silver, platinum

**My jeweller's rate is different.**
Dharalu shows the import price: the world price × the ₹ rate + import duty, for 24 carat (999) gold, 999 silver and 999.5 platinum. Jewellers add a local premium, and 22-carat jewellery is about 8% cheaper per gram than 24 carat, before making charges. Use the trend and the call, and check the rate in *Before you trade* with your jeweller's numbers.

**Why does the ₹ price include duty but not GST?**
Duty is already in every rate you'll be quoted in India. GST (3%) is paid on top when you buy, so it is shown separately ("with GST").

**What does the green ● live dot mean?**
The price was fetched from gold-api.com in the last few minutes, by the page or the Mac app itself. Without it you see the agent's last price. A live price more than 15% away from the agent's price is ignored as a bad tick.

**Why do metal calls change less often than the live price?**
The live price updates every 5 minutes, but the call only changes when the agent re-runs (every 5 minutes on the Mac) and a rule crosses its threshold. Telegram alerts for metals wait until the new call has held for two checks in a row.

## Data

**Which place are the prices for?**
- **Wheat**: the wholesale mandi price at **Jabalpur, Indore & Kota** (Madhya Pradesh, Rajasthan). These three have the longest daily records on data.gov.in Agmarknet. Andhra Pradesh and Telangana publish no wheat mandi prices, so there is no "Srikakulam" or "Hyderabad" wheat price to show. Instead the agent works out what wheat costs **landed** at the place you pick (📍) from each source mandi: mandi price + mandi fee + freight + handling (Mandis & landed cost tab).
- **Gold, silver, platinum**: the **all-India import price**: the world spot price × the ₹ rate + import duty, before GST. It is the same for all of India, Srikakulam and Hyderabad included. A local jeweller's rate is usually a little higher (their premium), and jewellery adds making charges and GST.
- Every price shows a 📍 line saying this.

**The dashboard shows an old date (⚠︎ N days old).**
- Mandis don't report on Sundays and holidays, and data.gov.in is sometimes late or down. The agent then analyses the data it already has, and tries again at the next run. Metal markets close at weekends.
- data.gov.in refuses GitHub's servers, so the GitHub runs show ✅ but bring no new wheat prices. Fresh prices come from your Mac: `scripts/mac-schedule.sh status` to check it's installed, `scripts/mac-schedule.sh run` to fetch now ([SETUP.md](SETUP.md#8-run-the-agent-from-your-mac-important)).
- The dashboard header shows ⚠︎ when wheat's newest price is 3 or more days old, or when the agent last ran 3 or more hours ago. The Mac app warns at 3 days for wheat and 4 for metals.

**I pressed Refresh in the Mac app and nothing changed.**
Refresh reloads what the agent last published, and the live gold, silver and platinum prices. It doesn't fetch new mandi prices. If wheat prices are old, run `scripts/mac-schedule.sh run` (or `scripts/mac-refresh.sh`) and press Refresh again after a minute.

**A mandi is missing from the landed-cost table.**
It hasn't reported in the last 7 days.

**The first wheat history download is very slow.**
You're on the public sample key (10 rows per call). Add your own `DATA_GOV_IN_KEY` ([SETUP.md](SETUP.md#3-get-a-datagovin-key)) and re-run with *bootstrap* ticked.

## Alerts

**No Telegram messages.**
1. Both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` must be set.
2. You must have sent the bot a message first. For a group, the bot must be in the group.
3. Check the run log in *Actions*: it prints whether the alert was sent.

**Too many or too few alerts.**
Change `alerts.daily_move_pct` in `config.json` for wheat (default 2.5%), and `move_alert_pct` under each metal (gold 2%, silver and platinum 3%). The Mac app uses the same numbers.

## Trades

**My trades disappeared.**
They live in the browser you entered them in. A different browser, a private window, clearing site data, or the Mac app each has its own copy. Each commodity has its own list. Back up with *Export CSV* now and then.

**My WheatWise trades are gone.**
The dashboard copies them over once, as wheat trades, the first time you open the new address in the same browser. The Mac app's trades don't carry over: export them in WheatWise and import them in Dharalu ([MAC_APP.md](MAC_APP.md#install)).

**A sale says "sold with no recorded purchase".**
Enter the buy that stock came from (with its date), and P&L will include it.

## GitHub

**"Workflows aren't being run on this forked repository."**
Open *Actions* and click **I understand my workflows, go ahead and enable them**.

**GitHub stopped the schedule.**
GitHub pauses scheduled workflows in repositories with no activity for 60 days. The agent's own data commits count as activity, so this rarely happens. If it does: *Actions → Dharalu monitor → Enable workflow*. The Mac job doesn't depend on it.

**A run failed with a push error.**
`.github/save.sh` retries 3 times, and the next run catches up. Nothing is lost. On the Mac, a failed push is committed locally and pushed by a later run.

## Mac app
See [MAC_APP.md](MAC_APP.md#troubleshooting).
