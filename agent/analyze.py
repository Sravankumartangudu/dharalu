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


TE_PLACE = {"Jabalpur": "జబల్‌పూర్", "Indore": "ఇండోర్", "Kota": "కోటా", "Madhya Pradesh": "మధ్యప్రదేశ్",
            "Rajasthan": "రాజస్థాన్", "Maharashtra": "మహారాష్ట్ర"}


def where_wheat(cfg, index_markets, best):
    """Which place the wheat price is from - shown beside every price."""
    state = {m["name"]: m.get("state") for m in cfg["source_markets"]}
    towns = [m.replace(" APMC", "").replace("APMC ", "") for m in index_markets]
    states = sorted({state.get(m) for m in index_markets if state.get(m)}, key=[state.get(m) for m in index_markets].index)
    home = cfg["business"]["location"]
    join = lambda xs: ", ".join(xs[:-1]) + " & " + xs[-1] if len(xs) > 1 else "".join(xs)
    w = {
        "short": "Wholesale mandi price · %s (%s)" % (join(towns), ", ".join(states)),
        "short_te": "మండీ టోకు ధర · %s (%s)" % (", ".join(TE_PLACE.get(t, t) for t in towns),
                                               ", ".join(TE_PLACE.get(s, s) for s in states)),
        "detail": "The middle of the day's modal (most-traded) wholesale prices at %s APMC mandis (%s), from "
                  "data.gov.in Agmarknet. Andhra Pradesh publishes no wheat mandi prices, so this is not a %s "
                  "rate." % (join(towns), ", ".join(states), home.split(",")[0]),
        "home": home,
    }
    if best:
        w["landed"] = "At %s: cheapest landed %s/qtl from %s, %s (%s km) = mandi %s + fee + freight + handling." % (
            home.split(",")[0], money(best["landed"]), best["market"], best["state"], best["km"], money(best["mandi_price"]))
        w["landed_te"] = "%s వద్ద: %s, %s (%s కి.మీ) నుండి తెచ్చిన ధర %s/క్వింటాల్ (మండీ ధర + ఫీజు + రవాణా)." % (
            "శ్రీకాకుళం" if home.startswith("Srikakulam") else home.split(",")[0],
            best["market"], best["state"], best["km"], money(best["landed"]))
    return w


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


def _fit(cal, idx):
    """The forecast's two inputs, on the de-seasonalised log price: the starting level
    (half today, half the last-5-day average) and the per-day slope of the last 30 points."""
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
    return {"level": level, "slope": slope, "last": ys[-1], "span": xs[-1] - xs[0]}


def _damp(h):
    """Days of trend the forecast carries to day h (the trend fades by PHI each day)."""
    return sum(PHI ** k for k in range(1, h + 1))


def _forecast_from(cal, idx, horizon):
    """Damped-trend on de-seasonalised log price + seasonal shape."""
    f = _fit(cal, idx)
    if not f:
        return None
    last_day = cal[-1][0]
    out, damp = [], 0.0
    for h in range(1, horizon + 1):
        damp += PHI ** h
        dy = last_day + timedelta(days=h)
        out.append((dy, math.exp(f["level"] + f["slope"] * damp + math.log(seasonal_factor(idx, dy)))))
    return out


BLIND = {  # what the forecast can't see, by commodity
    "wheat": "a new MSP, government wheat sales (OMSS), the size of the next harvest, or export/stock-limit rules",
    "metal": "US interest-rate moves, war or crisis news, central-bank buying, or an import-duty change in the Budget",
}


def forecast_reason(cal, se, bt, fc, evidence=(), kind="wheat"):
    """Why the forecast says what it says. The forecast is
         log(price on day h) = level + slope x damp(h) + log(season on day h),
    so the move from today's price splits exactly into three parts (in log terms):
      trend  = slope x damp(h)                  - the last 30 days' direction, fading out
      season = log(season day h / season today) - the usual month-to-month pattern
      level  = level - today's adjusted price   - today's price smoothed with the last 5 days."""
    idx = se["index"]
    f = _fit(cal, idx)
    if not f or not fc:
        return None
    last_day, p0 = cal[-1][0], cal[-1][1]
    s0 = seasonal_factor(idx, last_day)
    pc_ = lambda x: round((math.exp(x) - 1) * 100, 2)
    hz = {}
    for h in (7, 14, 30):
        if len(fc) < h:
            continue
        p = fc[h - 1]
        hz[str(h)] = {
            "total_pct": round(pct(p["price"], p0), 2),
            "trend_pct": pc_(f["slope"] * _damp(h)),
            "season_pct": pc_(math.log(seasonal_factor(idx, last_day + timedelta(days=h)) / s0)),
            "level_pct": pc_(f["level"] - f["last"]),
            "low_pct": round(pct(p["low"], p0), 1), "high_pct": round(pct(p["high"], p0), 1),
        }
    if "30" not in hz:
        return None
    r = hz["30"]
    past = pc_(f["slope"] * f["span"])  # the season-adjusted move over the last 30 points
    kept = round(100 * _damp(30) / 30)
    m_now = MONTHS[last_day.month - 1]
    m_then = MONTHS[(last_day + timedelta(days=30)).month - 1]
    word = lambda v: "rise" if v >= 1 else "fall" if v <= -1 else "stay about the same"
    drivers = [
        {"key": "trend", "name": "Recent trend", "pct": r["trend_pct"],
         "why": "Over the last 30 days the price %s %s once the usual seasonal effect is taken out. "
                "The forecast carries that direction forward but lets it fade each day, so about %d%% of "
                "it is kept over the next 30 days." % (
                    "rose" if past > 0 else "fell" if past < 0 else "moved", "%.1f%%" % abs(past), kept)},
        {"key": "season", "name": "Season", "pct": r["season_pct"],
         "why": ("In the seasonal pattern (from %d years of prices) the price is usually %.1f%% %s in 30 days' time (%s) than now (%s)." % (
                    se.get("years_used", 0), abs(r["season_pct"]), "higher" if r["season_pct"] > 0 else "lower", m_then, m_now))
                if abs(r["season_pct"]) >= 0.1 else "No real seasonal pull between %s and %s." % (m_now, m_then)},
        {"key": "level", "name": "Last few days' average", "pct": r["level_pct"],
         "why": ("Today's price is %s the last 5 days' average, and the forecast counts a one-day %s only half, "
                 "so it starts %.1f%% %s than today." % (
                     "below" if r["level_pct"] > 0 else "above", "dip" if r["level_pct"] > 0 else "jump",
                     abs(r["level_pct"]), "higher" if r["level_pct"] > 0 else "lower"))
                if abs(r["level_pct"]) >= 0.1 else "Today's price is in line with the last 5 days - no effect."},
    ]
    main = max(drivers, key=lambda d: abs(d["pct"]))
    summary = "Expected to %s%s in 30 days. Biggest reason: %s (%s)." % (
        word(r["total_pct"]), (" about %.1f%%" % abs(r["total_pct"])) if abs(r["total_pct"]) >= 1 else "",
        main["name"].lower(), pct_str(main["pct"]))
    b = (bt or {}).get(30)
    trust = None
    if b:
        better = b["mape_pct"] < b["naive_mape_pct"]
        trust = "Tested on %d past dates: off by %.1f%% on average at 30 days, vs %.1f%% for \"price stays the same\" - %s.%s" % (
            b["tests"], b["mape_pct"], b["naive_mape_pct"],
            "it adds a little value" if better else "it is NOT better than no-change here, so read it as a range, not a number",
            (" Direction right %.0f%% of the time." % b["direction_hit_pct"]) if b.get("direction_hit_pct") is not None else "")
    in_call = next(({"rule": e["rule"], "points": e["points"], "max": e["max"], "counted": counted(e),
                     "weight": e.get("weight", 1.0)}
                    for e in evidence if e["rule"].startswith("30-day forecast")), None)
    te = "30 రోజుల్లో సుమారు %.1f%% %s. ప్రధాన కారణం: %s (%s)." % (
        abs(r["total_pct"]),
        "పెరగవచ్చు" if r["total_pct"] >= 1 else "తగ్గవచ్చు" if r["total_pct"] <= -1 else "దాదాపు అలాగే ఉండవచ్చు",
        {"Recent trend": "ఇటీవలి ధోరణి", "Season": "సీజన్", "Last few days' average": "గత కొన్ని రోజుల సగటు"}[main["name"]],
        pct_str(main["pct"]))
    return {
        "summary": summary, "telugu": te, "main": main["name"],
        "biggest": "%s %s" % (main["name"].lower(), pct_str(main["pct"])), "drivers": drivers, "horizons": hz,
        "past_30d_adjusted_pct": past, "trend_kept_pct": kept,
        "range": "80%% of past misses fell inside %s to %s at 30 days, so that is the likely range." % (
            pct_str(r["low_pct"]), pct_str(r["high_pct"])),
        "trust": trust, "in_call": in_call,
        "blind": "It reads only the price's own trend and season. It can't see %s - news like that can move the price outside the range." % BLIND[kind],
    }


def pct_str(v):
    return "%+.1f%%" % v


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


def counted(e):
    """The points a rule really adds to the score (after its weight and the trend cap)."""
    return e.get("counted", e["points"])


def outlook_points(evidence):
    """Points from the forward-looking rules only (30-day forecast + season)."""
    return sum(counted(e) for e in evidence if e.get("forward"))


def action_key(score, evidence=()):
    """Score -> call. Scores can be fractions now (rules are weighted), so the calls are bands:
    >= 3 STRONG BUY | >= 1 BUY | between -1 and +1 HOLD or WAIT | > -3 SELL | else STRONG SELL."""
    if score >= 3:
        return "STRONG_BUY"
    if score >= 1:
        return "BUY"
    if score > -1:
        return "HOLD" if outlook_points(evidence) > 0 else "WAIT"
    return "SELL" if score > -3 else "STRONG_SELL"


def action_info(key, actions=ACTIONS):
    for _mn, k, en, te, buy, hold_adv in actions:
        if k == key:
            return {"key": k, "label": en, "telugu": te, "buyer": buy, "holder": hold_adv}
    return None


def action_for(score, evidence=(), actions=ACTIONS):
    return action_info(action_key(score, evidence), actions)


# --------------------------------------------------------------------------- weighing the rules
# The rules don't all deserve the same vote. Each rule's weight comes from its OWN past
# record - but only outcomes that were already known on the day (walk-forward), so a
# rule can't look good by being graded on the days it was tuned on.
TREND_FAMILY = ("30-day forecast vs holding cost", "Trend", "Trend (weeks)", "Long trend (months)")
TREND_CAP = 2       # the forecast and the trend rules all read the same thing - the recent direction
MIN_VOTES = 60      # fewer graded votes than this: the rule keeps weight 1 (not enough proof yet)
BOLD_VOTES = 120    # weight 2 needs at least this many graded votes
CALL_GROUP = {"STRONG_BUY": "buy", "BUY": "buy", "HOLD": "hold", "WAIT": "wait", "SELL": "sell", "STRONG_SELL": "sell"}
GROUP_WORD = {"buy": "BUY", "hold": "HOLD", "wait": "WAIT", "sell": "SELL"}
WAIT_BAND = 3.0     # a WAIT was right if the price moved less than this (%) in 30 days


class RuleBook:
    """Each rule's record so far: when it voted up (down), how often the price really
    rose (fell) over the next 30 days - against how often it did on ANY day (the usual
    rate). A rule is only useful if it beats the usual rate."""

    def __init__(self):
        self.r = {}
        self.days = self.rose = self.fell = 0

    def add(self, votes, move):
        self.days += 1
        self.rose += move > 0
        self.fell += move < 0
        for rule, p in votes:
            s = self.r.setdefault(rule, [0, 0, 0, 0])  # up votes, up right, down votes, down right
            if p > 0:
                s[0] += 1
                s[1] += move > 0
            elif p < 0:
                s[2] += 1
                s[3] += move < 0

    def stat(self, rule):
        nu, ru, nd, rd = self.r.get(rule, (0, 0, 0, 0))
        n = nu + nd
        if not n or not self.days:
            return {"votes": n}
        right = 100.0 * (ru + rd) / n
        usual = 100.0 * (nu * self.rose + nd * self.fell) / (n * self.days)
        return {"votes": n, "up": nu, "down": nd, "right_pct": round(right, 1),
                "usual_pct": round(usual, 1), "edge_pts": round(right - usual, 1)}

    def weight(self, rule):
        s = self.stat(rule)
        if s["votes"] < MIN_VOTES:
            return 1.0, s, "only %d graded votes so far - full weight until it has %d" % (s["votes"], MIN_VOTES)
        e = s["edge_pts"]
        if e >= 10 and s["votes"] >= BOLD_VOTES:
            return 2.0, s, "beat the usual rate by %.0f points - counts double" % e
        if e >= 3:
            return 1.0, s, "beat the usual rate by %.0f points - full weight" % e
        if e >= 0:
            return 0.5, s, "only %.1f points better than the usual rate - half weight" % e
        return 0.0, s, "did worse than the usual rate (%+.1f points) - not counted" % e


def weigh(evidence, book):
    """Fill each evidence row's weight + counted points; return (score, max score, note).
    The forecast and the trend rules count at most TREND_CAP together, because they all
    measure the same recent direction (without the cap a trend is counted 2-3 times)."""
    for e in evidence:
        w, s, why = book.weight(e["rule"]) if book else (1.0, {"votes": 0}, "")
        e.update({"weight": w, "weight_why": why, "rule_record": s, "counted": round(e["points"] * w, 2) + 0.0})
    fam = [e for e in evidence if e["rule"] in TREND_FAMILY]
    tot = sum(e["counted"] for e in fam)
    note = None
    if abs(tot) > TREND_CAP:
        k = TREND_CAP / abs(tot)
        for e in fam:
            e["counted"] = round(e["counted"] * k, 2) + 0.0
            e["capped"] = True
        note = "The forecast and trend rules together said %+g; they all read the recent direction, so together they count at most %+d." % (
            tot, TREND_CAP if tot > 0 else -TREND_CAP)
    score = round(sum(e["counted"] for e in evidence), 2)
    fam_max = min(TREND_CAP, sum(e["max"] * e["weight"] for e in fam))
    most = fam_max + sum(e["max"] * e["weight"] for e in evidence if e["rule"] not in TREND_FAMILY)
    return score, round(most, 2), note


def score_str(v):
    """+1.5, -2, 0 - scores are halves/fractions now."""
    v = round(v, 1)
    return "0" if v == 0 else ("%+.1f" % v).replace(".0", "")


def group_right(group, move):
    if group in ("buy", "hold"):
        return move > 0
    if group == "sell":
        return move < 0
    return abs(move) < WAIT_BAND


def call_record(rows, key, field="signal"):
    """How this kind of call did in the walk-forward replay, against any day.
    BUY/HOLD: price higher 30 days later | SELL: lower | WAIT: moved less than 3%."""
    group = CALL_GROUP[key]
    done = [r for r in rows if r.get("move_pct") is not None]
    g = [r for r in done if CALL_GROUP.get(r[field]) == group]
    if not done:
        return None
    base = 100.0 * sum(group_right(group, r["move_pct"]) for r in done) / len(done)
    what = {"buy": "higher", "hold": "higher", "sell": "lower", "wait": "within 3%"}[group]
    out = {"group": group, "call": GROUP_WORD[group], "what": what, "days": len(g),
           "base_pct": round(base, 1), "all_days": len(done), "since": done[0]["date"]}
    if g:
        right = 100.0 * sum(group_right(group, r["move_pct"]) for r in g) / len(g)
        out.update({"right_pct": round(right, 1), "edge_pts": round(right - base, 1),
                    "avg_move_pct": round(st.mean(r["move_pct"] for r in g), 2)})
    return out


def record_line(rec):
    """'Past SELL days: lower 30 days later on 49% vs 43% of all days -> edge +6 points'."""
    if not rec or rec.get("right_pct") is None:
        return "No past %s days to judge yet." % (rec or {}).get("call", "such")
    return "Past %s days (%d since %s): %s 30 days later on %.0f%% vs %.0f%% of all days -> edge %+.0f points" % (
        rec["call"], rec["days"], rec["since"][:4], rec["what"], rec["right_pct"], rec["base_pct"], rec["edge_pts"])


def record_line_te(rec):
    if not rec or rec.get("right_pct") is None:
        return "ఇలాంటి సూచనకు గత రికార్డు ఇంకా లేదు."
    what = {"higher": "ధర పెరిగింది", "lower": "ధర తగ్గింది", "within 3%": "ధర 3% లోపే మారింది"}[rec["what"]]
    return "గతంలో %s రోజుల్లో (%d రోజులు) 30 రోజుల తర్వాత %.0f%% సార్లు %s; ఏ రోజైనా %.0f%% (తేడా %+.0f)." % (
        rec["call"], rec["days"], rec["right_pct"], what, rec["base_pct"], rec["edge_pts"])


CONF_TE = {"High": "ఎక్కువ", "Medium": "మధ్యస్థం", "Low": "తక్కువ"}


def brief_lines(sig):
    """The four lines every briefing starts with: the call, why, what would change it,
    how sure. (English, Telugu) - each a list of 4 strings."""
    en = ["%s (score %s of %g): If buying: %s  If holding: %s" % (
              sig["label"], score_str(sig["score"]), sig["max_score"], sig["buyer"], sig["holder"]),
          "Why: " + sig["plain"],
          "What would change it: " + sig["change_line"],
          "How sure: %s. %s." % (sig["confidence"], sig["record_line"])]
    te = ["%s (స్కోరు %s / %g)" % (sig["telugu"], score_str(sig["score"]), sig["max_score"]),
          "ఎందుకు: " + sig["plain_te"],
          "ఏది మారిస్తే మారుతుంది: " + sig["change_line_te"],
          "నమ్మకం: %s. %s" % (CONF_TE[sig["confidence"]], record_line_te(sig.get("record")))]
    if sig.get("pending"):
        en.append("Note: " + sig["pending"]["note"])
    return en, te


def confidence(score, bt, ind, rec=None):
    """How sure: starts from the size of the score, then can't be higher than the call's
    own walk-forward record allows. Returns (Low | Medium | High, reasons)."""
    why = []
    c = 1 if abs(score) < 1.5 else 2 if abs(score) < 3.5 else 3
    why.append("score %s -> %s" % (score_str(score), ["", "Low", "Medium", "High"][c]))
    hit = ((bt or {}).get(30) or {}).get("direction_hit_pct")
    if ind["days_of_history"] < 120:
        c -= 1
        why.append("less than 120 days of prices - one step lower")
    elif hit is not None and hit < 55:
        c -= 1
        why.append("the forecast got the 30-day direction right only %.0f%% of the time - one step lower" % hit)
    if rec is not None:
        edge, days = rec.get("edge_pts"), rec.get("days", 0)
        if edge is None or days < 30:
            cap, txt = 1, "only %d past %s days to judge - at most Low" % (days, rec["call"])
        elif edge >= 10:
            cap, txt = 3, "past %s days beat any day by %.0f points - High allowed" % (rec["call"], edge)
        elif edge >= 3:
            cap, txt = 2, "past %s days beat any day by only %.0f points - at most Medium" % (rec["call"], edge)
        else:
            cap, txt = 1, "past %s days were no better than any day (%+.0f points) - at most Low" % (rec["call"], edge)
        if c > cap:
            c = cap
            why.append(txt)
        else:
            why.append(txt.split(" - ")[0])
    return ["Low", "Low", "Medium", "High"][max(0, c)], why


# --------------------------------------------------------------------------- the call in plain words
PLAIN = {  # rule -> (when it points up, when it points down), each (English, Telugu)
    "30-day forecast vs holding cost": (
        ("the 30-day forecast expects a rise bigger than the holding cost", "30 రోజుల అంచనా నిల్వ ఖర్చు కంటే ఎక్కువ పెరుగుదల చూపుతోంది"),
        ("the 30-day forecast doesn't beat the holding cost", "30 రోజుల అంచనా నిల్వ ఖర్చును కూడా దాటడం లేదు")),
    "Season (next 60 days)": (
        ("prices usually rise in the next two months", "రాబోయే రెండు నెలల్లో ధరలు సాధారణంగా పెరుగుతాయి"),
        ("prices usually ease in the next two months", "రాబోయే రెండు నెలల్లో ధరలు సాధారణంగా తగ్గుతాయి")),
    "Trend": (
        ("prices have been rising for weeks", "కొన్ని వారాలుగా ధరలు పెరుగుతున్నాయి"),
        ("prices have been falling for weeks", "కొన్ని వారాలుగా ధరలు తగ్గుతున్నాయి")),
    "Trend (weeks)": (
        ("prices have been rising for weeks", "కొన్ని వారాలుగా ధరలు పెరుగుతున్నాయి"),
        ("prices have been falling for weeks", "కొన్ని వారాలుగా ధరలు తగ్గుతున్నాయి")),
    "Long trend (months)": (
        ("the months-long trend is up", "నెలల తరబడి ధోరణి పైకి ఉంది"),
        ("the months-long trend is down", "నెలల తరబడి ధోరణి కిందికి ఉంది")),
    "Price level vs last 12 months": (
        ("the price is in the cheap part of the year's range", "ధర ఈ ఏడాది పరిధిలో తక్కువ భాగంలో ఉంది"),
        ("the price is near the top of the year's range", "ధర ఈ ఏడాది గరిష్ఠ స్థాయి దగ్గర ఉంది")),
    "Momentum (RSI-14)": (
        ("it fell very fast, and such falls often bounce back", "చాలా వేగంగా పడిపోయింది, ఇలాంటప్పుడు తరచుగా మళ్ళీ పెరుగుతుంది"),
        ("it rose very fast, and such rises often pause", "చాలా వేగంగా పెరిగింది, ఇలాంటప్పుడు తరచుగా ఆగుతుంది")),
    "Govt floor (MSP)": (
        ("it is close to the government floor (MSP)", "ప్రభుత్వ కనీస మద్దతు ధర (MSP) దగ్గర ఉంది"), None),
    "Govt ceiling (FCI OMSS sales)": (
        None, ("FCI's open-market sales keep prices from rising", "FCI బహిరంగ మార్కెట్ అమ్మకాలు ధర పెరగకుండా ఆపుతాయి")),
    "Rupee (US$/Rs, 30 days)": (
        ("a weaker rupee makes it dearer in India", "రూపాయి బలహీనపడటం వల్ల భారత్‌లో ధర పెరుగుతుంది"),
        ("a stronger rupee makes it cheaper in India", "రూపాయి బలపడటం వల్ల భారత్‌లో ధర తగ్గుతుంది")),
    "Gold / silver ratio": (
        ("silver is cheap compared with gold", "బంగారంతో పోలిస్తే వెండి చౌకగా ఉంది"),
        ("silver is dear compared with gold", "బంగారంతో పోలిస్తే వెండి ఖరీదుగా ఉంది")),
}


def _phrase(e, lang):
    pair = PLAIN.get(e["rule"])
    p = pair and pair[0 if counted(e) > 0 else 1]
    return p[lang] if p else e["rule"].lower()


def plain_reason(key, evidence):
    """The call in one line: the biggest counted reasons for it and the biggest against."""
    live = [e for e in evidence if counted(e)]
    up = sorted((e for e in live if counted(e) > 0), key=lambda e: -counted(e))
    dn = sorted((e for e in live if counted(e) < 0), key=lambda e: counted(e))
    g = CALL_GROUP[key]
    pro, con = (up, dn) if g in ("buy", "hold") else (dn, up) if g == "sell" else (up, dn)
    j = lambda xs, lang, word: (" %s " % word).join(_phrase(e, lang) for e in xs)
    if g == "wait":
        if not live:
            return ("No rule gives a clear signal today.", "ఈరోజు ఏ నియమమూ స్పష్టమైన సంకేతం ఇవ్వడం లేదు.")
        if pro and con:
            return ("The reasons cancel out: %s, but %s." % (j(pro[:1], 0, "and"), j(con[:1], 0, "and")),
                    "కారణాలు ఒకదానికొకటి సరిపోతున్నాయి: %s, కానీ %s." % (j(pro[:1], 1, "మరియు"), j(con[:1], 1, "మరియు")))
        one = (pro or con)[:1]
        return ("Only a weak signal: %s." % j(one, 0, "and"), "బలహీన సంకేతం మాత్రమే: %s." % j(one, 1, "మరియు"))
    en = "Mainly because %s." % j(pro[:2], 0, "and") if pro else "No single strong reason."
    te = "ముఖ్య కారణం: %s." % j(pro[:2], 1, "మరియు") if pro else "బలమైన ఒక్క కారణమూ లేదు."
    if con:
        en += " Against it: %s." % j(con[:1], 0, "and")
        te += " వ్యతిరేకంగా: %s." % j(con[:1], 1, "మరియు")
    return en, te


# --------------------------------------------------------------------------- what would change the call
def triggers(cal, idx, cfg, bt, scorer, book, key_now, step=0.25, most=15.0):
    """Re-score today with only today's price changed (forecast re-made too), stepping
    0.25% at a time up and down: the nearest prices where the call would change."""
    price = cal[-1][1]

    def call_at(f):
        c = cal[:-1] + [(cal[-1][0], price * f)]
        fc = forecast(c, idx["index"], bt)
        _s, ev, _i = scorer(c, idx, cfg, fc, bt)
        sc = weigh(ev, book)[0]
        return action_key(sc, ev), sc

    out = {"price": round(price), "step_pct": step, "most_pct": most}
    for name, sign in (("up", 1), ("down", -1)):
        out[name] = None
        k = 1
        while k * step <= most + 1e-9:
            f = 1 + sign * k * step / 100.0
            key, sc = call_at(f)
            if key != key_now:
                out[name] = {"price": round(price * f), "pct": round(sign * k * step, 2), "key": key,
                             "label": key.replace("_", " "), "score": sc}
                break
            k += 1
    return out


def trigger_line(tr, fmt, key_now):
    if not tr:
        return ""
    bits = []
    for name, word in (("up", "rises"), ("down", "falls")):
        t = tr.get(name)
        if t:
            bits.append("%s if the price %s to %s (%+.1f%%)" % (t["label"], word, fmt(t["price"]), t["pct"]))
    if not bits:
        return "%s holds even if the price moves %.0f%% either way." % (key_now.replace("_", " "), tr["most_pct"])
    line = "Turns " + "; turns ".join(bits) + "."
    for name, word in (("up", "rises"), ("down", "falls")):
        if not tr.get(name):
            line += " Stays %s even if it %s %.0f%%." % (key_now.replace("_", " "), word, tr["most_pct"])
    return line


def trigger_line_te(tr, fmt, actions):
    if not tr:
        return ""
    te = {k: t for _m, k, _e, t, _b, _h in actions}
    bits = []
    for name, word in (("up", "పెరిగితే"), ("down", "తగ్గితే")):
        t = tr.get(name)
        if t:
            bits.append("ధర %s (%+.1f%%) కి %s %s" % (fmt(t["price"]), t["pct"], word, te.get(t["key"], t["label"])))
    if not bits:
        return "ధర %.0f%% అటూ ఇటూ మారినా ఇదే సూచన." % tr["most_pct"]
    line = "; ".join(bits) + "."
    for name, word in (("up", "పెరిగినా"), ("down", "తగ్గినా")):
        if not tr.get(name):
            line += " ధర %.0f%% %s ఇదే సూచన." % (tr["most_pct"], word)
    return line


# --------------------------------------------------------------------------- what changed since the last prices day
def snapshot(asof, sig):
    return {"asof": asof, "key": sig["key"], "label": sig["label"], "score": sig["score"],
            "rules": [{"rule": e["rule"], "points": e["points"], "counted": counted(e), "value": e["value"]}
                      for e in sig["evidence"]]}


def changes(prev, asof, sig):
    """Which rules moved since the previous prices day's final call."""
    if not prev or prev.get("asof") == asof:
        return None
    before = {r["rule"]: r for r in prev.get("rules") or []}
    moved = []
    for e in sig["evidence"]:
        b = before.pop(e["rule"], None)
        was = b.get("counted", b["points"]) if b else 0
        if round(was, 2) != round(counted(e), 2):
            moved.append({"rule": e["rule"], "was": was, "now": counted(e),
                          "value_was": b["value"] if b else None, "value_now": e["value"]})
    for r, b in before.items():
        if b.get("counted", b["points"]):
            moved.append({"rule": r, "was": b.get("counted", b["points"]), "now": 0, "value_was": b["value"], "value_now": None})
    return {"since": prev["asof"], "key_was": prev["key"], "label_was": prev["label"], "score_was": prev["score"],
            "call_changed": prev["key"] != sig["key"], "rules": moved}


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
    None; only days whose 30 days are over count in the summaries.

    Two passes. 1: every day's raw rule votes. 2: walk forward through the days, weighing
    each day's votes with each rule's record from the days whose 30 days were ALREADY
    over then (weigh()), exactly as the live agent would have. The old equal-weight call
    is kept per row (signal_equal) so the two ways can be compared honestly.
    Returns (track record, RuleBook with every graded day - the weights for today)."""
    n = len(cal)
    raw = []
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
        raw.append((hist[-1][0], ev, {"date": hist[-1][0].isoformat(), "score_equal": score,
                                      "signal_equal": action_for(score, ev, actions)["key"],
                                      "price": round(hist[-1][1]), "pred30": fc[29]["price"],
                                      "after30": round(later) if later else None,
                                      "move_pct": round(pct(later, hist[-1][1]), 2) if later else None}))
    book, rows, j = RuleBook(), [], 0
    for dy, ev, row in raw:
        while j < len(raw) and raw[j][0] + timedelta(days=30) <= dy:  # outcomes known by this day
            if raw[j][2]["move_pct"] is not None:
                book.add([(e["rule"], e["points"]) for e in raw[j][1]], raw[j][2]["move_pct"])
            j += 1
        ev = [dict(e) for e in ev]
        sc = weigh(ev, book)[0]
        row.update({"score": sc, "signal": action_key(sc, ev)})
        rows.append(row)
    for _dy, ev, row in raw[j:]:  # the rest that are graded (all of them, for today's weights)
        if row["move_pct"] is not None:
            book.add([(e["rule"], e["points"]) for e in ev], row["move_pct"])
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
        "buy_days": lambda r: CALL_GROUP[r["signal"]] == "buy",
        "hold_days": lambda r: r["signal"] == "HOLD",
        "wait_days": lambda r: r["signal"] == "WAIT",
        "sell_days": lambda r: CALL_GROUP[r["signal"]] == "sell",
        "all_days": lambda r: True,
    }
    # The weighted way (now) vs equal weights (up to 2.1), on the same days.
    compare = {name: {g: call_record(done, k, field) for g, k in
                      (("buy", "BUY"), ("hold", "HOLD"), ("wait", "WAIT"), ("sell", "SELL"))}
               for name, field in (("weighted", "signal"), ("equal", "signal_equal"))}
    return {"summary": {k: grp(f) for k, f in groups.items()},
            "summary_all": {k: grp(f, done) for k, f in groups.items()},
            "compare": compare,
            "rules": {r: book.stat(r) for r in sorted(book.r)},
            "graded_days": book.days,
            "since": done[0]["date"] if done else None,
            "rows": [{k: v for k, v in r.items() if k not in ("score_equal", "signal_equal")} for r in rows[-1130:]]}, book


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



def decide(cal, idx, cfg, fc, bt, season_asof, scorer=score_signal, carry=carrying_cost_pct,
           actions=ACTIONS, days=None, fmt=money):
    """Today's call with everything that explains it. Returns (signal, track record)."""
    score_eq, evidence, ind = scorer(cal, idx, cfg, fc, bt)
    eq_key = action_key(score_eq, [dict(e) for e in evidence])
    tr, book = track_record(cal, season_asof, cfg, bt, scorer=scorer, carry=carry, actions=actions, days=days)
    score, most, cap_note = weigh(evidence, book)
    key = action_key(score, evidence)
    rec = tr["compare"]["weighted"][CALL_GROUP[key]]
    conf, conf_why = confidence(score, bt, ind, rec)
    plain, plain_te = plain_reason(key, evidence)
    trig = triggers(cal, idx, cfg, bt, scorer, book, key)
    sig = {"score": score, "confidence": conf, "confidence_why": conf_why, **action_info(key, actions),
           "evidence": evidence, "max_score": most, "trend_cap": cap_note,
           "plain": plain, "plain_te": plain_te,
           "record": rec, "record_line": record_line(rec),
           "triggers": trig, "change_line": trigger_line(trig, fmt, key),
           "change_line_te": trigger_line_te(trig, fmt, actions),
           "equal": {"score": score_eq, "key": eq_key, "label": eq_key.replace("_", " ")}}
    return sig, tr, ind


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
    sig, tr, ind = decide(cal, idx, cfg, fc, bt, season_asof)
    asof = cal[-1][0].isoformat()
    lt = landed_table(cfg, mdaily, asof)
    feed_day, states = state_table(cfg, current_rows or rows)
    sell_ref = median([s["median"] for s in states if s["role"] == "selling"])
    preds = predictions_made(cal, season_asof, days=set(bench))

    all_watched_today = median([r["mandi_price"] for r in lt])
    return {
        "asof": asof,
        "feed_day": feed_day,
        "benchmark": {"markets": index_markets, **ind},
        "watched_median": all_watched_today,
        "signal": sig,
        "forecast": fc,
        "forecast_points": {str(h): fc[h - 1] for h in (7, 14, 30) if len(fc) >= h},
        "forecast_reason": forecast_reason(cal, idx, bt, fc, sig["evidence"], "wheat"),
        "backtest": {str(k): v for k, v in bt.items()},
        "seasonality": {"months": MONTHS, **idx, "index": [round(x, 4) for x in idx["index"]]},
        "timing": timing(idx, cal, bench),
        "carrying_cost_30d_pct": round(carrying_cost_pct(cfg, ind["price"]), 2),
        "msp": {**{k: v for k, v in cfg["msp"].items() if k != "history"},
                "floor": msp_floor(cfg, cal[-1][0])[0], "season": msp_floor(cfg, cal[-1][0])[1]},
        "landed": lt,
        "best_source": lt[0] if lt else None,
        "where": where_wheat(cfg, index_markets, lt[0] if lt else None),
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
