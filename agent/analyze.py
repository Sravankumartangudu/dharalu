"""Dharalu analysis engine - pure Python (no numpy), so it runs anywhere.

Pipeline:
  prices.csv -> per-mandi daily price -> BENCHMARK series (median of the
  long-history mandis Jabalpur / Indore / Kota) -> indicators, seasonality,
  forecast (backtested), evidence-based signal, landed cost at Srikakulam,
  selling reference, and the agent's own track record.

Every number that drives the BUY / SELL call is returned as an evidence row
(value, rule, points, source) so the dashboard can show the proof.
"""
import math
import statistics as st
from collections import defaultdict
from datetime import date, timedelta

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Typical Indian wheat price shape (harvest dip Apr-May, lean-season peak Dec-Feb).
# Used only until we have >= 2 full years of our own data, then blended out.
SEASONAL_PRIOR = [1.055, 1.05, 0.99, 0.945, 0.94, 0.96, 0.98, 0.995, 1.005, 1.015, 1.025, 1.04]

ACTIONS = [
    # (min score, key, English, Telugu, buyer advice, stock-holder advice)
    (3, "STRONG_BUY", "STRONG BUY", "బాగా కొనండి",
     "Good time to buy and stock up.", "Hold your stock - prices likely to rise."),
    (1, "BUY", "BUY", "కొనండి",
     "Buy gradually (in 2-3 lots).", "Hold - don't rush to sell."),
    # Score 0 splits in two: HOLD when the forward-looking rules (forecast, season) still
    # point up - keep stock, but today's price is no bargain - otherwise WAIT.
    (0, "HOLD", "HOLD", "నిల్వ ఉంచండి",
     "Don't add stock at today's price - buy only what you need.", "Keep your stock - the outlook beats your holding cost."),
    (0, "WAIT", "WAIT", "వేచి ఉండండి",
     "Buy only what you need now.", "No clear edge - sell in parts only if you need cash."),
    (-2, "SELL", "SELL", "అమ్మండి",
     "Avoid stocking - buy hand-to-mouth.", "Sell gradually - prices may soften."),
    (-99, "STRONG_SELL", "STRONG SELL", "వెంటనే అమ్మండి",
     "Do not stock now.", "Sell / clear stock now."),
]


def d(s):
    return date(int(s[:4]), int(s[5:7]), int(s[8:10]))


def pct(a, b):
    return (a / b - 1.0) * 100.0 if b else 0.0


def median(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def money(v):
    return "Rs %s" % format(int(round(v)), ",")


# --------------------------------------------------------------------------- prices
def market_daily(rows):
    """{market: {date: price}} - median across varieties, crazy values dropped."""
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        p = float(r["modal"])
        if 1200 <= p <= 7000:
            acc[r["market"]][r["date"]].append(p)
    out = {}
    for m, by in acc.items():
        daily = {dt: st.median(v) for dt, v in by.items()}
        keys = sorted(daily)
        clean = {}
        for i, k in enumerate(keys):
            # Drop one-off typos: a day more than 15% away from the mandi's own nearby days.
            near = [daily[x] for x in keys[max(0, i - 7):i + 8] if x != k]
            if len(near) >= 4 and abs(daily[k] / st.median(near) - 1) > 0.15:
                continue
            clean[k] = daily[k]
        out[m] = clean
    return out


def benchmark_series(mdaily, index_markets, min_overlap=15):
    """Chain-linked median of the index mandis.

    Mandis trade at different levels (Indore ~Rs 200 above Jabalpur), so each one
    is first scaled to the reference mandi using their median price ratio on days
    both reported. Without that, the benchmark would jump whenever a mandi starts
    or stops reporting. A mandi with too little overlap is left out."""
    have = [m for m in index_markets if mdaily.get(m)]
    if not have:
        return {}
    ref = max(have, key=lambda m: len(mdaily[m]))
    ratio = {ref: 1.0}
    for m in have:
        if m == ref:
            continue
        common = [d for d in mdaily[m] if d in mdaily[ref]]
        if len(common) >= min_overlap:
            ratio[m] = st.median(mdaily[m][d] / mdaily[ref][d] for d in common)
    level = st.median(ratio.values())  # publish at the typical mandi's level
    days = sorted({dt for m in ratio for dt in mdaily[m]})
    out = {}
    for dt in days:
        vals = [mdaily[m][dt] / ratio[m] for m in ratio if dt in mdaily[m]]
        out[dt] = st.median(vals) * level
    return out


def to_calendar(series, max_gap=10):
    """Forward-fill an irregular {date: price} into a daily list [(date, price|None)]."""
    if not series:
        return []
    keys = sorted(series)
    start, end = d(keys[0]), d(keys[-1])
    out, last, last_day = [], None, None
    cur = start
    while cur <= end:
        k = cur.isoformat()
        if k in series:
            last, last_day = series[k], cur
        elif last_day and (cur - last_day).days > max_gap:
            last = None
        out.append((cur, last))
        cur += timedelta(days=1)
    return out


# --------------------------------------------------------------------------- indicators
def sma(vals, n):
    v = [x for x in vals[-n:] if x is not None]
    return sum(v) / len(v) if len(v) >= max(2, n // 2) else None


def rsi(vals, n=14):
    v = [x for x in vals if x is not None][-(n * 3):]
    if len(v) < n + 1:
        return None
    gains, losses = [], []
    for a, b in zip(v[:-1], v[1:]):
        gains.append(max(b - a, 0))
        losses.append(max(a - b, 0))
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    for g, l in zip(gains[n:], losses[n:]):
        ag, al = (ag * (n - 1) + g) / n, (al * (n - 1) + l) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)


def value_ago(cal, days):
    if len(cal) <= days:
        return None
    return cal[-1 - days][1]


def indicators(cal):
    vals = [p for _, p in cal]
    last = vals[-1]
    year = [p for p in vals[-365:] if p is not None]
    rets = []
    for a, b in zip(vals[-91:-1], vals[-90:]):
        if a and b and a != b:
            rets.append(math.log(b / a))
    return {
        "price": last,
        "date": cal[-1][0].isoformat(),
        "chg_1d": pct(last, value_ago(cal, 1)) if value_ago(cal, 1) else None,
        "chg_7d": pct(last, value_ago(cal, 7)) if value_ago(cal, 7) else None,
        "chg_30d": pct(last, value_ago(cal, 30)) if value_ago(cal, 30) else None,
        "chg_365d": pct(last, value_ago(cal, 365)) if value_ago(cal, 365) else None,
        "sma7": sma(vals, 7),
        "sma30": sma(vals, 30),
        "sma90": sma(vals, 90),
        "rsi14": rsi(vals),
        "high_52w": max(year) if year else None,
        "low_52w": min(year) if year else None,
        "pctile_52w": (100.0 * sum(1 for p in year if p < last) / len(year)) if len(year) > 30 else None,
        "vol_daily_pct": (st.pstdev(rets) * 100) if len(rets) > 10 else None,
        "days_of_history": sum(1 for p in vals if p is not None),
    }


# --------------------------------------------------------------------------- seasonality
def seasonality(series, prior=SEASONAL_PRIOR, detrend=False):
    """Monthly index (avg = 1.0). Ratio of each month to its own year's average.

    detrend=True compares each month with a centred 12-month average instead, so a
    steady long rise (gold) doesn't show up as "December is always dearest"."""
    by_ym = defaultdict(list)
    for k, p in series.items():
        by_ym[(int(k[:4]), int(k[5:7]))].append(p)
    years = defaultdict(dict)
    for (y, m), v in by_ym.items():
        if len(v) >= 4:
            years[y][m] = st.mean(v)
    ratios = defaultdict(list)
    used = 0
    if detrend:
        mon = {y * 12 + m - 1: v for y, ms in years.items() for m, v in ms.items()}
        for k, v in mon.items():
            win = [mon.get(k + j) for j in range(-6, 7)]
            if None in win:
                continue
            centred = (sum(win[1:-1]) + 0.5 * (win[0] + win[-1])) / 12.0  # 2x12 moving average
            ratios[k % 12 + 1].append(v / centred)
        used = min(len(r) for r in ratios.values()) if len(ratios) == 12 else 0
    else:
        for y, months in years.items():
            if len(months) >= 10:
                used += 1
                avg = st.mean(months.values())
                for m, v in months.items():
                    ratios[m].append(v / avg)
    data = [st.median(ratios[m]) if ratios.get(m) else prior[m - 1] for m in range(1, 13)]
    w = used / (used + 2.0)
    idx = [w * a + (1 - w) * b for a, b in zip(data, prior)]
    norm = st.mean(idx)
    idx = [x / norm for x in idx]
    return {"index": idx, "years_used": used, "weight_on_data": round(w, 2)}


def seasonal_factor(idx, day):
    """Smooth daily factor: linear between the 15th of each month."""
    mid = date(day.year, day.month, 15)
    if day >= mid:
        nxt = date(day.year + (day.month == 12), day.month % 12 + 1, 15)
        a, b, lo, hi = idx[day.month - 1], idx[day.month % 12], mid, nxt
    else:
        prv = date(day.year - (day.month == 1), (day.month - 2) % 12 + 1, 15)
        a, b, lo, hi = idx[(day.month - 2) % 12], idx[day.month - 1], prv, mid
    return a + (b - a) * (day - lo).days / (hi - lo).days


class SeasonAsOf:
    """Seasonal index using only prices before the 1st of the given day's month,
    so backtests and replays never peek at the future."""

    def __init__(self, series, prior=SEASONAL_PRIOR, detrend=False):
        self.series, self.cache = series, {}
        self.prior, self.detrend = prior, detrend

    def __call__(self, day):
        key = (day.year, day.month)
        if key not in self.cache:
            cut = "%04d-%02d-01" % key
            self.cache[key] = seasonality({k: v for k, v in self.series.items() if k < cut},
                                          self.prior, self.detrend)
        return self.cache[key]


# --------------------------------------------------------------------------- forecast
PHI = 0.97  # trend damping per day


def _forecast_from(cal, idx, horizon):
    """Damped-trend on de-seasonalised log price + seasonal shape."""
    tail = cal[-60:]
    pts = [(i, math.log(p) - math.log(seasonal_factor(idx, dy))) for i, (dy, p) in enumerate(tail) if p]
    if len(pts) < 20:
        return None
    recent = pts[-30:]
    xs, ys = [x for x, _ in recent], [y for _, y in recent]
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in recent) / sxx if sxx else 0.0
    level = 0.5 * ys[-1] + 0.5 * st.mean(ys[-5:])
    last_day = cal[-1][0]
    out, damp = [], 0.0
    for h in range(1, horizon + 1):
        damp += PHI ** h
        dy = last_day + timedelta(days=h)
        out.append((dy, math.exp(level + slope * damp + math.log(seasonal_factor(idx, dy)))))
    return out


def backtest(cal, season_asof, horizons=(7, 14, 30), step=3, lookback_days=730):
    """Walk-forward test: forecast from past dates, compare with what really happened.
    Each test uses only the prices (and the seasonal pattern) known on that date."""
    errs = {h: [] for h in horizons}
    naive = {h: [] for h in horizons}
    hits = {h: [0, 0] for h in horizons}
    n = len(cal)
    start = max(60, n - lookback_days - max(horizons))
    for t in range(start, n - max(horizons) // 7, step):
        hist = cal[: t + 1]
        if not hist[-1][1]:
            continue
        fc = _forecast_from(hist, season_asof(hist[-1][0])["index"], max(horizons))
        if not fc:
            continue
        p0 = hist[-1][1]
        for h in horizons:
            if t + h >= n or not cal[t + h][1]:
                continue
            actual, pred = cal[t + h][1], fc[h - 1][1]
            errs[h].append(math.log(actual / pred))
            naive[h].append(abs(actual / p0 - 1))
            a_move, p_move = pct(actual, p0), pct(pred, p0)
            if abs(a_move) >= 1.0:
                hits[h][1] += 1
                if (a_move > 0) == (p_move > 0):
                    hits[h][0] += 1
    res = {}
    for h in horizons:
        e = sorted(errs[h])
        if len(e) < 15:
            res[h] = None
            continue
        q = lambda f: e[min(len(e) - 1, max(0, int(f * len(e))))]
        res[h] = {
            "tests": len(e),
            "mape_pct": round(st.mean(abs(math.exp(x) - 1) for x in e) * 100, 2),
            "naive_mape_pct": round(st.mean(naive[h]) * 100, 2),
            "direction_hit_pct": round(100.0 * hits[h][0] / hits[h][1], 1) if hits[h][1] >= 10 else None,
            "direction_tests": hits[h][1],
            "q10": q(0.10),
            "q90": q(0.90),
        }
    return res


def forecast(cal, idx, bt, horizon=45):
    fc = _forecast_from(cal, idx, horizon)
    if not fc:
        return []
    vol = None
    vals = [p for _, p in cal[-91:] if p]
    rets = [math.log(b / a) for a, b in zip(vals[:-1], vals[1:]) if a != b]
    if len(rets) > 10:
        vol = st.pstdev(rets)
    out = []
    for h, (dy, p) in enumerate(fc, start=1):
        ref = min((k for k in bt if bt[k]), key=lambda k: abs(k - h), default=None)
        if ref:
            scale = math.sqrt(h / ref)
            lo, hi = bt[ref]["q10"] * scale, bt[ref]["q90"] * scale
        else:
            s = (vol or 0.01) * math.sqrt(h) * 1.28
            lo, hi = -s, s
        out.append({"date": dy.isoformat(), "price": round(p), "low": round(p * math.exp(lo)),
                    "high": round(p * math.exp(hi))})
    return out


# --------------------------------------------------------------------------- signal
def carrying_cost_pct(cfg, price, days=30):
    c = cfg["carrying"]
    months = days / 30.0
    return (c["interest_pct_per_month"] + c["loss_pct_per_month"]) * months + \
        100.0 * c["storage_per_qtl_per_month"] * months / price


def msp_floor(cfg, today):
    """The MSP that was the floor on this date. A season's MSP takes over when its
    harvest/procurement starts (1 Mar), per the dated list in config.json."""
    m = cfg["msp"]
    past = [h for h in sorted(m.get("history", []), key=lambda h: h["from"]) if h["from"] <= today.isoformat()]
    if past:
        return past[-1]["value"], past[-1]["season"]
    return m["value"], m["season"]


def score_signal(cal, idx, cfg, fc=None, bt=None):
    """Return (score, evidence rows). Each row is the proof for one rule.
    Only uses data up to cal[-1], so the same function replays past days."""
    ind = indicators(cal)
    price, today = ind["price"], cal[-1][0]
    ev = []

    def add(rule, value, test, points, source, why, most=1, forward=False):
        ev.append({"rule": rule, "value": value, "test": test, "points": points,
                   "max": most, "source": source, "why": why, "forward": forward})

    # 1. Forecast vs cost of holding stock
    f30 = fc[29]["price"] if fc and len(fc) >= 30 else None
    if f30:
        exp = pct(f30, price)
        cc = carrying_cost_pct(cfg, price)
        edge = exp - cc
        pts = 2 if edge >= 3 else 1 if edge >= 1 else -2 if edge <= -3 else -1 if edge <= -1 else 0
        acc = (bt or {}).get(30) or {}
        weak = bool(acc) and acc["mape_pct"] > acc["naive_mape_pct"]
        if weak:  # forecast hasn't beaten "price stays the same" -> it only gets half a vote
            pts = max(-1, min(1, pts))
        add("30-day forecast vs holding cost",
            "Forecast %s (%+.1f%%) vs holding cost %.1f%% -> edge %+.1f%%" % (money(f30), exp, cc, edge),
            "edge >= +3%: +2 | >= +1%: +1 | <= -1%: -1 | <= -3%: -2" + (
                " (capped at 1 point: backtest error %.1f%% is not better than no-change %.1f%%)" % (
                    acc["mape_pct"], acc["naive_mape_pct"]) if weak else ""),
            pts, "Dharalu forecast (backtest error %s%% vs no-change %s%%, %s tests)" % (
                acc.get("mape_pct", "n/a"), acc.get("naive_mape_pct", "n/a"), acc.get("tests", 0)),
            "Stocking only pays if the expected rise beats interest + godown + losses.", most=2, forward=True)

    # 2. Seasonal pattern
    s_now, s_60 = seasonal_factor(idx["index"], today), seasonal_factor(idx["index"], today + timedelta(days=60))
    sp = pct(s_60, s_now)
    pts = 1 if sp >= 3 else -1 if sp <= -3 else 0
    add("Season (next 60 days)",
        "Prices in %s are usually %+.1f%% vs %s" % (MONTHS[(today + timedelta(days=60)).month - 1], sp, MONTHS[today.month - 1]),
        ">= +3%: +1 | <= -3%: -1", pts,
        "Seasonal index from %d year%s of Agmarknet data (%d%% weight, rest = typical pattern)" % (
            idx["years_used"], "" if idx["years_used"] == 1 else "s", int(idx["weight_on_data"] * 100)),
        "Wheat is cheapest at harvest (Apr-May) and dearest in the lean months (Dec-Feb).", forward=True)

    # 3. Trend
    if ind["sma7"] and ind["sma30"] and ind["chg_30d"] is not None:
        up = ind["sma7"] > ind["sma30"] and ind["chg_30d"] > 0
        down = ind["sma7"] < ind["sma30"] and ind["chg_30d"] < 0
        add("Trend",
            "7-day avg %s vs 30-day avg %s; 30-day change %+.1f%%" % (money(ind["sma7"]), money(ind["sma30"]), ind["chg_30d"]),
            "both up: +1 | both down: -1", 1 if up else -1 if down else 0,
            "Benchmark mandis (Agmarknet)", "Prices tend to keep moving the way they are moving for a few weeks.")

    # 4. Price level vs last 12 months
    if ind["pctile_52w"] is not None:
        p = ind["pctile_52w"]
        add("Price level vs last 12 months",
            "Today is higher than %.0f%% of the last year's days (range %s - %s)" % (p, money(ind["low_52w"]), money(ind["high_52w"])),
            "<= 25%: +1 (cheap) | >= 85%: -1 (expensive)", 1 if p <= 25 else -1 if p >= 85 else 0,
            "Benchmark mandis, last 365 days", "Buying in the cheap part of the yearly range limits risk.")

    # 5. RSI
    if ind["rsi14"] is not None:
        r = ind["rsi14"]
        add("Momentum (RSI-14)", "RSI %.0f" % r, "< 30: +1 (oversold) | > 70: -1 (overbought)",
            1 if r < 30 else -1 if r > 70 else 0, "Benchmark mandis, last 14 days",
            "A very fast rise/fall often pauses or reverses.")

    # 6. Government floor (MSP)
    floor, season = msp_floor(cfg, today)
    gap = pct(price, floor)
    add("Govt floor (MSP)", "Price is %+.1f%% vs MSP %s (%s)" % (gap, money(floor), season),
        "within +4% of MSP: +1", 1 if gap <= 4 else 0, "Cabinet MSP announcement (config.json)",
        "Near MSP, FCI procurement supports prices - downside is limited.")

    # 7. Government ceiling (OMSS)
    om = cfg.get("omss") or {}
    rp = om.get("reserve_price")
    if rp and (not om.get("active_from") or today.isoformat() >= om["active_from"]):
        g = pct(price, rp)
        add("Govt ceiling (FCI OMSS sales)", "Price is %+.1f%% vs OMSS reserve %s" % (g, money(rp)),
            ">= reserve: -1", -1 if g >= 0 else 0, "FCI OMSS reserve price (config.json)",
            "When FCI sells wheat to millers at the reserve price, open-market prices struggle to rise further.")

    score = sum(e["points"] for e in ev)
    return score, ev, ind


def outlook_points(evidence):
    """Points from the forward-looking rules only (30-day forecast + season)."""
    return sum(e["points"] for e in evidence if e.get("forward"))


def action_for(score, evidence=(), actions=ACTIONS):
    hold = score == 0 and outlook_points(evidence) > 0
    for mn, key, en, te, buy, hold_adv in actions:
        if key == "HOLD" and not hold:
            continue
        if score >= mn:
            return {"key": key, "label": en, "telugu": te, "buyer": buy, "holder": hold_adv}
    return None


def confidence(score, bt, ind):
    c = 1 if abs(score) <= 1 else 2 if abs(score) <= 3 else 3
    hit = ((bt or {}).get(30) or {}).get("direction_hit_pct")
    if ind["days_of_history"] < 120 or (hit is not None and hit < 55):
        c -= 1
    return ["Low", "Low", "Medium", "High"][max(0, c)]


# --------------------------------------------------------------------------- timing
def timing(idx, cal, raw):
    i = idx["index"]
    buy_m = sorted(range(12), key=lambda m: i[m])[:2]
    sell_m = sorted(range(12), key=lambda m: -i[m])[:2]
    today = cal[-1][0]

    def next_start(months):
        for k in range(0, 366):
            dy = today + timedelta(days=k)
            if dy.month - 1 in months:
                return dy.replace(day=1) if k else today
        return today

    nb = next_start(buy_m)
    # weekday effect: price vs 15-day centred mean
    dev = defaultdict(list)
    vals = cal[-400:]
    for k in range(7, len(vals) - 7):
        dy, p = vals[k]
        if dy.isoformat() not in raw:  # forward-filled day, no real trading
            continue
        win = [x for _, x in vals[k - 7:k + 8] if x]
        if p and len(win) > 8:
            dev[dy.weekday()].append(pct(p, st.mean(win)))
    wd = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekday = [{"day": wd[k], "avg_dev_pct": round(st.mean(v), 2), "n": len(v)} for k, v in sorted(dev.items()) if len(v) >= 8]
    return {
        "cheapest_months": [MONTHS[m] for m in sorted(buy_m)],
        "dearest_months": [MONTHS[m] for m in sorted(sell_m)],
        "seasonal_swing_pct": round(pct(max(i), min(i)), 1),
        "next_buy_window": nb.isoformat(),
        "days_to_buy_window": (nb - today).days,
        "weekday": weekday,
    }


# --------------------------------------------------------------------------- landed cost
def landed(cfg, price, km, override=None):
    c = cfg["costs"]
    freight = override if override is not None else km * cfg["freight"]["rate_per_qtl_per_km"]
    fee = price * c["source_mandi_fee_pct"] / 100.0
    extras = c["handling_per_qtl"] + c["bags_per_qtl"] + c["brokerage_per_qtl"]
    return {"mandi_price": round(price), "fee": round(fee), "freight": round(freight),
            "extras": round(extras), "landed": round(price + fee + freight + extras)}


def landed_table(cfg, mdaily, asof):
    out = []
    cutoff = (d(asof) - timedelta(days=6)).isoformat()
    for m in cfg["source_markets"]:
        series = mdaily.get(m["name"], {})
        recent = sorted(k for k in series if k >= cutoff)
        if not recent:
            continue
        k = recent[-1]
        row = landed(cfg, series[k], m["km"], m.get("freight_override"))
        row.update({"market": m["name"], "state": m["state"], "km": m["km"], "date": k})
        out.append(row)
    out.sort(key=lambda r: r["landed"])
    return out


def latest_day_rows(rows):
    if not rows:
        return "", []
    last = max(r["date"] for r in rows)
    return last, [r for r in rows if r["date"] == last]


def state_table(cfg, rows):
    """Today's all-India picture by state, from the CURRENT feed."""
    last, today = latest_day_rows(rows)
    by = defaultdict(list)
    for r in today:
        p = float(r["modal"])
        if 1200 <= p <= 7000:
            by[r["state"]].append(p)
    out = []
    for s, v in by.items():
        row = {"state": s, "median": round(st.median(v)), "mandis": len(v),
               "low": round(min(v)), "high": round(max(v)),
               "role": "selling" if s in cfg["consumer_states"] else "source"}
        km = cfg["state_km"].get(s)
        if km and row["role"] == "source":
            row["landed"] = landed(cfg, row["median"], km)["landed"]
        out.append(row)
    out.sort(key=lambda r: -r["mandis"])
    return last, out


# --------------------------------------------------------------------------- track record
def track_record(cal, season_asof, cfg, bt, lookback=365, step=1, scorer=score_signal,
                 carry=carrying_cost_pct, actions=ACTIONS, days=None):
    """Replay the signal on every past day (using only data up to that day, and the
    MSP/OMSS that applied then) and check what the price did over the next 30 days.
    This is the proof of how useful the signal has been.

    days: only replay these dates (real trading days, for metals that skip weekends).
    Each row also keeps the 30-day forecast made that day (pred30), so the timeline
    can show what the agent expected next to what really happened.
    The last 30 days are replayed too (for the timeline's call strip) with after30 =
    None; only days whose 30 days are over count in the summaries."""
    n = len(cal)
    rows = []
    for t in range(120, n, step):  # whole history; the headline table is the last `lookback` days
        hist = cal[: t + 1]
        later = cal[t + 30][1] if t + 30 < n else None
        if not hist[-1][1] or (t + 30 < n and not later):
            continue
        if days is not None and hist[-1][0].isoformat() not in days:
            continue
        idx = season_asof(hist[-1][0])
        fc = forecast(hist, idx["index"], {}, horizon=30)
        if not fc:
            continue
        score, ev, ind = scorer(hist, idx, cfg, fc, bt)
        rows.append({"date": hist[-1][0].isoformat(), "score": score,
                     "signal": action_for(score, ev, actions)["key"],
                     "price": round(hist[-1][1]), "pred30": fc[29]["price"],
                     "after30": round(later) if later else None,
                     "move_pct": round(pct(later, hist[-1][1]), 2) if later else None})
    done = [r for r in rows if r["after30"] is not None]
    cut = (cal[-31][0] - timedelta(days=lookback)).isoformat()
    recent = [r for r in done if r["date"] > cut]

    def grp(f, rows=recent):
        g = [r for r in rows if f(r)]
        if not g:
            return None
        cc = carry(cfg, st.mean(r["price"] for r in g))
        return {"days": len(g), "avg_move_pct": round(st.mean(r["move_pct"] for r in g), 2),
                "rose_pct": round(100.0 * sum(r["move_pct"] > 0 for r in g) / len(g), 1),
                "beat_holding_cost_pct": round(100.0 * sum(r["move_pct"] > cc for r in g) / len(g), 1)}
    groups = {
        "buy_days": lambda r: r["score"] >= 1,
        "hold_days": lambda r: r["signal"] == "HOLD",
        "wait_days": lambda r: r["signal"] == "WAIT",
        "sell_days": lambda r: r["score"] <= -1,
        "all_days": lambda r: True,
    }
    return {"summary": {k: grp(f) for k, f in groups.items()},
            "summary_all": {k: grp(f, done) for k, f in groups.items()},
            "since": done[0]["date"] if done else None, "rows": rows[-1130:]}


def predictions_made(cal, season_asof, back=60, days=None):
    """The 30-day forecast the agent made on each recent day, so the timeline can
    show it (also for days whose 30 days aren't over yet)."""
    out = []
    for t in range(max(120, len(cal) - back), len(cal)):
        dy, p = cal[t]
        if not p or (days is not None and dy.isoformat() not in days):
            continue
        fc = forecast(cal[: t + 1], season_asof(dy)["index"], {}, horizon=30)
        if fc:
            out.append({"date": dy.isoformat(), "target": fc[29]["date"], "pred30": fc[29]["price"]})
    return out



# --------------------------------------------------------------------------- main entry
def run(rows, cfg, current_rows=None):
    mdaily = market_daily(rows)
    index_markets = [m["name"] for m in cfg["source_markets"] if m.get("long_history")]
    bench = benchmark_series(mdaily, index_markets)
    cal = to_calendar(bench)
    if len(cal) < 30:
        raise SystemExit("Not enough history yet (%d days). Run agent/bootstrap.py first." % len(cal))
    # trim leading None gaps
    while cal and cal[0][1] is None:
        cal.pop(0)
    idx = seasonality(bench)
    season_asof = SeasonAsOf(bench)
    bt = backtest(cal, season_asof)
    fc = forecast(cal, idx["index"], bt)
    score, evidence, ind = score_signal(cal, idx, cfg, fc, bt)
    act = action_for(score, evidence)
    asof = cal[-1][0].isoformat()
    lt = landed_table(cfg, mdaily, asof)
    feed_day, states = state_table(cfg, current_rows or rows)
    sell_ref = median([s["median"] for s in states if s["role"] == "selling"])
    tr = track_record(cal, season_asof, cfg, bt)
    preds = predictions_made(cal, season_asof, days=set(bench))

    all_watched_today = median([r["mandi_price"] for r in lt])
    return {
        "asof": asof,
        "feed_day": feed_day,
        "benchmark": {"markets": index_markets, **ind},
        "watched_median": all_watched_today,
        "signal": {"score": score, "confidence": confidence(score, bt, ind), **act,
                   "evidence": evidence,
                   "max_score": sum(e["max"] for e in evidence)},
        "forecast": fc,
        "forecast_points": {str(h): fc[h - 1] for h in (7, 14, 30) if len(fc) >= h},
        "backtest": {str(k): v for k, v in bt.items()},
        "seasonality": {"months": MONTHS, **idx, "index": [round(x, 4) for x in idx["index"]]},
        "timing": timing(idx, cal, bench),
        "carrying_cost_30d_pct": round(carrying_cost_pct(cfg, ind["price"]), 2),
        "msp": {**{k: v for k, v in cfg["msp"].items() if k != "history"},
                "floor": msp_floor(cfg, cal[-1][0])[0], "season": msp_floor(cfg, cal[-1][0])[1]},
        "landed": lt,
        "best_source": lt[0] if lt else None,
        "states": states,
        "selling_reference": sell_ref,
        "margin_vs_selling_ref": (sell_ref - lt[0]["landed"]) if (sell_ref and lt) else None,
        "track_record": tr,
        "predictions": preds,
        "series": [{"date": dy.isoformat(), "price": round(p) if p else None} for dy, p in cal[-1100:]],
        "markets": {m["name"]: [{"date": k, "price": round(v)} for k, v in sorted(mdaily.get(m["name"], {}).items())[-180:]]
                    for m in cfg["source_markets"]},
        "costs": {"freight": cfg["freight"], "costs": cfg["costs"], "carrying": cfg["carrying"]},
    }
