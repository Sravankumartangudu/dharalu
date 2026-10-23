"""Gold, silver and platinum: fetch world prices, turn them into Indian rupee
prices, and run the same kind of analysis as wheat (forecast, backtest, season,
signal with proof, track record).

Sources (both free, no key):
  * Yahoo Finance daily closes - COMEX futures GC=F / SI=F / PL=F (US$ per troy
    ounce, 10 years) and the US$/Rs rate INR=X.
  * gold-api.com - the live spot price (XAU / XAG / XPT).

Futures trade a little above spot (interest until delivery), so the history is
lined up with today's spot price ("basis"), and today's point *is* the spot price.

India price = US$/oz x Rs per US$ / 31.1035 g x grams x (1 + import duty).
GST is shown separately (it is paid on top when you buy).
"""
import bisect
import csv
import json
import math
import os
import statistics as st
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import analyze as az
from fetch import ROOT

METALS = ("gold", "silver", "platinum")
OZ_G = 31.1034768
DIR = os.path.join(ROOT, "data", "metals")
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d"
LIVE = "https://api.gold-api.com/price/%s"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Dharalu/2.0"
FLAT = [1.0] * 12  # metals have no strong harvest cycle: start from "no season"
IST = timezone(timedelta(hours=5, minutes=30))

METAL_ACTIONS = [
    (3, "STRONG_BUY", "STRONG BUY", "బాగా కొనండి",
     "Good time to buy - buy in 2-3 parts.", "Hold - prices likely to rise."),
    (1, "BUY", "BUY", "కొనండి",
     "Buy gradually, in parts.", "Hold - don't rush to sell."),
    (0, "HOLD", "HOLD", "నిల్వ ఉంచండి",
     "Don't add at today's price - buy only for a real need (a wedding, a gift).",
     "Keep holding - the outlook beats what the money would earn in the bank."),
    (0, "WAIT", "WAIT", "వేచి ఉండండి",
     "Buy only what you need now.", "No clear edge - sell only if you need the cash."),
    (-2, "SELL", "SELL", "అమ్మండి",
     "Avoid buying now - wait for a dip.", "Consider selling a part to book profit."),
    (-99, "STRONG_SELL", "STRONG SELL", "వెంటనే అమ్మండి",
     "Do not buy now.", "Sell / book profit now."),
]


def inr(v):
    """Rs with Indian digit grouping: 1,34,826."""
    n = int(round(v))
    s, neg = str(abs(n)), n < 0
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-Rs " if neg else "Rs ") + s


# --------------------------------------------------------------------------- fetch
def _json(url, tries=3):
    why = "no answer"
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            why = "%s: %s" % (type(e).__name__, str(e)[:80])
            time.sleep(2 * (k + 1))
    raise RuntimeError("%s failed (%s)" % (url.split("?")[0], why))


def yahoo(symbol, rng="5d"):
    """({date: close}, meta) for one Yahoo Finance symbol, dated in the exchange's time zone."""
    j = _json(YAHOO % (urllib.parse.quote(symbol), rng))
    r = j["chart"]["result"][0]
    meta = r["meta"]
    off = meta.get("gmtoffset") or 0
    closes = (r.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    out = {}
    for t, c in zip(r.get("timestamp") or [], closes):
        if c:
            out[datetime.fromtimestamp(t + off, timezone.utc).date().isoformat()] = round(c, 4)
    return out, {"price": meta.get("regularMarketPrice"), "time": meta.get("regularMarketTime"),
                 "prev_close": meta.get("chartPreviousClose")}


def live_spot(symbol):
    j = _json(LIVE % symbol)
    return {"usd": float(j["price"]), "updated": j.get("updatedAt")}


def _csv(name):
    return os.path.join(DIR, name + ".csv")


def load(name):
    p = _csv(name)
    if not os.path.exists(p):
        return {}
    with open(p, newline="", encoding="utf-8") as f:
        return {r["date"]: float(r["close"]) for r in csv.DictReader(f)}


def save(name, series):
    os.makedirs(DIR, exist_ok=True)
    with open(_csv(name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "close"])
        for k in sorted(series):
            w.writerow([k, series[k]])


def update(cfg, log=print):
    """Refresh the saved closes (a 5-day top-up, or 10 years when missing/stale)
    and the live spot prices. Returns {name: meta}; failures keep the saved data."""
    m = cfg["metals"]
    names = {k: m[k]["futures"] for k in METALS}
    names["usdinr"] = m["fx_symbol"]
    metas = {}
    stale_cut = (datetime.now(timezone.utc) - timedelta(days=10)).date().isoformat()
    for name, sym in names.items():
        have = load(name)
        rng = "5d" if have and max(have) >= stale_cut else "10y"
        try:
            new, meta = yahoo(sym, rng)
            have.update(new)
            save(name, have)
            metas[name] = meta
        except (RuntimeError, KeyError, IndexError, TypeError) as e:
            log("  ! %s (%s): %s" % (name, sym, e))
    live_path = os.path.join(DIR, "live.json")
    try:
        live = json.load(open(live_path, encoding="utf-8"))
    except (OSError, ValueError):
        live = {}
    for k in METALS:
        try:
            live[k] = {**live_spot(m[k]["spot"]), "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            if metas.get(k, {}).get("price"):
                live[k]["futures_usd"] = metas[k]["price"]
        except (RuntimeError, KeyError, ValueError) as e:
            log("  ! live %s: %s" % (k, e))
    if metas.get("usdinr", {}).get("price"):
        live["usdinr"] = {"rate": metas["usdinr"]["price"], "time": metas["usdinr"]["time"]}
    os.makedirs(DIR, exist_ok=True)
    with open(live_path, "w", encoding="utf-8") as f:
        json.dump(live, f, indent=2)
    return live


# --------------------------------------------------------------------------- helpers
class AsOf:
    """Value of a dated series on a day (or the last day before it)."""

    def __init__(self, series):
        self.keys = sorted(series)
        self.series = series

    def __call__(self, day):
        k = day if isinstance(day, str) else day.isoformat()
        i = bisect.bisect_right(self.keys, k) - 1
        return self.series[self.keys[i]] if i >= 0 else None


def carry(m, price=None, days=30):
    """Holding cost in % - what the money would have earned in the bank."""
    return m["interest_pct_per_month"] * days / 30.0


def india(usd, fx, m):
    return usd * fx / OZ_G * m["grams"] * (1 + m["duty_pct"] / 100.0)


def make_scorer(key, m, trading, fx_at, ratio_at=None):
    """Signal rules for a metal. Same shape as analyze.score_signal, so the same
    replay (track record) and proof table work. Only data up to cal[-1] is used."""

    def score(cal, idx, _cfg, fc=None, bt=None):
        ind = az.indicators(cal)
        price, today = ind["price"], cal[-1][0]
        vals = [p for _, p in cal]
        ev = []

        def add(rule, value, test, points, source, why, most=1, forward=False):
            ev.append({"rule": rule, "value": value, "test": test, "points": points,
                       "max": most, "source": source, "why": why, "forward": forward})

        # 1. Forecast vs holding cost (bank interest)
        f30 = fc[29]["price"] if fc and len(fc) >= 30 else None
        if f30:
            exp = az.pct(f30, price)
            cc = carry(m)
            edge = exp - cc
            pts = 2 if edge >= 3 else 1 if edge >= 1 else -2 if edge <= -3 else -1 if edge <= -1 else 0
            acc = (bt or {}).get(30) or {}
            weak = bool(acc) and acc["mape_pct"] > acc["naive_mape_pct"]
            if weak:
                pts = max(-1, min(1, pts))
            add("30-day forecast vs holding cost",
                "Forecast %s (%+.1f%%) vs bank interest %.1f%% -> edge %+.1f%%" % (inr(f30), exp, cc, edge),
                "edge >= +3%: +2 | >= +1%: +1 | <= -1%: -1 | <= -3%: -2" + (
                    " (capped at 1 point: backtest error %.1f%% is not better than no-change %.1f%%)" % (
                        acc["mape_pct"], acc["naive_mape_pct"]) if weak else ""),
                pts, "Dharalu forecast (backtest error %s%% vs no-change %s%%, %s tests)" % (
                    acc.get("mape_pct", "n/a"), acc.get("naive_mape_pct", "n/a"), acc.get("tests", 0)),
                "Holding metal only pays if the expected rise beats the interest the money would earn.",
                most=2, forward=True)

        # 2. Season
        s_now = az.seasonal_factor(idx["index"], today)
        s_60 = az.seasonal_factor(idx["index"], today + timedelta(days=60))
        sp = az.pct(s_60, s_now)
        add("Season (next 60 days)",
            "Prices in %s are usually %+.1f%% vs %s (after removing the long trend)" % (
                az.MONTHS[(today + timedelta(days=60)).month - 1], sp, az.MONTHS[today.month - 1]),
            ">= +1.5%: +1 | <= -1.5%: -1", 1 if sp >= 1.5 else -1 if sp <= -1.5 else 0,
            "Seasonal index from %d year%s of prices (%d%% weight, rest = no season)" % (
                idx["years_used"], "" if idx["years_used"] == 1 else "s", int(idx["weight_on_data"] * 100)),
            "Indian demand peaks around Dhanteras, Diwali and the wedding season; world demand around Chinese New Year.",
            forward=True)

        # 3. Short trend
        if ind["sma7"] and ind["sma30"] and ind["chg_30d"] is not None:
            up = ind["sma7"] > ind["sma30"] and ind["chg_30d"] > 0
            down = ind["sma7"] < ind["sma30"] and ind["chg_30d"] < 0
            add("Trend (weeks)",
                "7-day avg %s vs 30-day avg %s; 30-day change %+.1f%%" % (inr(ind["sma7"]), inr(ind["sma30"]), ind["chg_30d"]),
                "both up: +1 | both down: -1", 1 if up else -1 if down else 0,
                "World price x Rs rate (Yahoo Finance)", "Prices tend to keep moving the way they are moving for a few weeks.")

        # 4. Long trend (50 / 200 trading days ~ 70 / 280 calendar days)
        s50, s200 = az.sma(vals, 70), az.sma(vals, 280)
        if s50 and s200:
            up, down = price > s200 and s50 > s200, price < s200 and s50 < s200
            add("Long trend (months)",
                "Price %s vs 200-day avg %s; 50-day avg %s" % (inr(price), inr(s200), inr(s50)),
                "price and 50-day both above the 200-day: +1 | both below: -1", 1 if up else -1 if down else 0,
                "World price x Rs rate, last ~9 months", "Metals move in long waves; going with the big trend avoids fighting it.")

        # 5. Price level vs last 12 months
        if ind["pctile_52w"] is not None:
            p = ind["pctile_52w"]
            add("Price level vs last 12 months",
                "Today is higher than %.0f%% of the last year's days (range %s - %s)" % (p, inr(ind["low_52w"]), inr(ind["high_52w"])),
                "<= 25%: +1 (cheap) | >= 85%: -1 (expensive)", 1 if p <= 25 else -1 if p >= 85 else 0,
                "World price x Rs rate, last 365 days", "Buying in the cheap part of the yearly range limits risk.")

        # 6. RSI on real trading days
        tv = [p for dy, p in cal[-90:] if p and dy.isoformat() in trading]
        r = az.rsi(tv)
        if r is not None:
            add("Momentum (RSI-14)", "RSI %.0f" % r, "< 30: +1 (oversold) | > 70: -1 (overbought)",
                1 if r < 30 else -1 if r > 70 else 0, "World price x Rs rate, last 14 trading days",
                "A very fast rise/fall often pauses or reverses.")

        # 7. Rupee
        fx_now, fx_30 = fx_at(today), fx_at(today - timedelta(days=30))
        if fx_now and fx_30:
            ch = az.pct(fx_now, fx_30)
            add("Rupee (US$/Rs, 30 days)",
                "Rs %.2f per US$ vs Rs %.2f a month ago (%+.1f%%)" % (fx_now, fx_30, ch),
                ">= +1% (rupee weaker): +1 | <= -1% (rupee stronger): -1", 1 if ch >= 1 else -1 if ch <= -1 else 0,
                "Yahoo Finance INR=X", "Metal is priced in dollars: a falling rupee makes it dearer in India, a rising one cheaper.")

        # 8. Silver only: gold/silver ratio
        if ratio_at:
            gr = ratio_at(today)
            if gr:
                add("Gold / silver ratio", "1 oz of gold buys %.1f oz of silver" % gr,
                    ">= 85: +1 (silver cheap vs gold) | <= 65: -1 (silver dear vs gold)",
                    1 if gr >= 85 else -1 if gr <= 65 else 0, "COMEX futures closes (Yahoo Finance)",
                    "Over the long run the ratio swings around ~65-85; at the extremes silver tends to catch up or lag.")

        score = sum(e["points"] for e in ev)
        return score, ev, ind

    return score


def weekly(series):
    """Last price of each week - for the long-range timeline."""
    out = {}
    for k in sorted(series):
        y, w, _ = az.d(k).isocalendar()
        out[(y, w)] = (k, series[k])
    return [{"date": k, "price": round(v)} for k, v in sorted(out.values())]


# --------------------------------------------------------------------------- the long run (1 year +)
LONG_CALLS = {  # key: (label, Telugu label, advice, Telugu advice)
    "ADD": ("ADD FOR THE LONG RUN", "దీర్ఘకాలానికి కొనండి",
            "A good time to add for the long run - still buy in 2-3 parts.",
            "దీర్ఘకాలానికి కొనడానికి మంచి సమయం - అయినా 2-3 భాగాలుగా కొనండి."),
    "STEADY": ("BUY STEADILY", "క్రమంగా కొనండి",
               "Keep buying a small fixed amount regularly (say every month); don't try to time it.",
               "ప్రతి నెలా కొద్ది మొత్తం క్రమంగా కొంటూ ఉండండి; సరైన సమయం కోసం ఎదురుచూడకండి."),
    "GO_SLOW": ("GO SLOW", "నెమ్మదిగా కొనండి",
                "The long-run signs are weak right now: keep the small regular buys, but avoid one big purchase now.",
                "దీర్ఘకాల సంకేతాలు ఇప్పుడు బలహీనంగా ఉన్నాయి: చిన్న క్రమమైన కొనుగోళ్లు కొనసాగించండి, ఇప్పుడు ఒకేసారి పెద్ద మొత్తం కొనకండి."),
}
LONG_PLAIN = {  # rule -> (+1 phrase, -1 phrase), each (English, Telugu)
    "Price vs 3-year average": (("it is at or below its 3-year average", "ధర 3 ఏళ్ల సగటు కంటే తక్కువగా ఉంది"),
                                ("it is far above its 3-year average", "ధర 3 ఏళ్ల సగటు కంటే చాలా ఎక్కువగా ఉంది")),
    "Change over 12 months": (("it fell a lot in the past year", "గత ఏడాదిలో బాగా పడిపోయింది"),
                              ("it rose very fast in the past year", "గత ఏడాదిలో చాలా వేగంగా పెరిగింది")),
    "Long trend (200 days)": (("the long wave is up (above the 200-day average)", "దీర్ఘకాల ధోరణి పైకి ఉంది (200 రోజుల సగటు పైన)"),
                              ("the long wave is down (below the 200-day average)", "దీర్ఘకాల ధోరణి కిందికి ఉంది (200 రోజుల సగటు కింద)")),
}
Y3 = 3 * 365
LONG_MIN = 100  # days on one side of a long-term rule before its record can switch it off


def long_key(score):
    return "ADD" if score >= 1 else "GO_SLOW" if score <= -1 else "STEADY"


def long_view(cal, trading):
    """For someone saving for years (a daughter's wedding, a pension), not trading a month:
    three simple, fixed rules, checked against what the price did ONE YEAR later.
    The thresholds were set by hand, not fitted, and years overlap, so the record is
    a guide (about one independent result per year), not proof."""
    n = len(cal)
    vals = [p for _, p in cal]
    pre = [0.0]
    for v in vals:
        pre.append(pre[-1] + (v or 0))
    avg = lambda a, b: (pre[b] - pre[a]) / (b - a)

    def rules(t):
        if t < Y3 or not vals[t] or not vals[t - 365]:
            return None
        price, a3, a200 = vals[t], avg(t - Y3 + 1, t + 1), avg(t - 279, t + 1)
        g3, ch = az.pct(price, a3), az.pct(price, vals[t - 365])
        return [
            {"rule": "Price vs 3-year average", "value": "%s vs 3-year average %s (%+.0f%%)" % (inr(price), inr(a3), g3),
             "test": "at or below the average: +1 (cheap for the long run) | 30%+ above: -1 (far above)",
             "points": 1 if g3 <= 0 else -1 if g3 >= 30 else 0},
            {"rule": "Change over 12 months", "value": "%+.0f%% in a year (from %s)" % (ch, inr(vals[t - 365])),
             "test": "fell 10%+: +1 | rose 30%+: -1 (a fast run-up often cools)",
             "points": 1 if ch <= -10 else -1 if ch >= 30 else 0},
            {"rule": "Long trend (200 days)", "value": "%s vs 200-day average %s" % (inr(price), inr(a200)),
             "test": "above: +1 (the long wave is up) | below: -1",
             "points": 1 if price > a200 else -1},
        ]

    graded = []
    for t in range(Y3, n - 365):
        if cal[t][0].isoformat() not in trading or not vals[t + 365]:
            continue
        ev = rules(t)
        if ev:
            graded.append(({e["rule"]: e["points"] for e in ev}, az.pct(vals[t + 365], vals[t])))
    ev = rules(n - 1)
    if not ev or len(graded) < 200:
        return None
    all_avg = st.mean(mv for _v, mv in graded)
    # A rule only counts when its own record agrees with it: on its +1 days the next year
    # beat the usual year, on its -1 days it fell short. With under LONG_MIN days on a side
    # there is no record yet and the rule counts as set.
    for e in ev:
        side = [mv for v, mv in graded if v[e["rule"]] == e["points"]] if e["points"] else []
        up = [mv for v, mv in graded if v[e["rule"]] > 0]
        dn = [mv for v, mv in graded if v[e["rule"]] < 0]
        e["record"] = {"up_days": len(up), "up_avg_1y_pct": round(st.mean(up), 1) if up else None,
                       "down_days": len(dn), "down_avg_1y_pct": round(st.mean(dn), 1) if dn else None}
        if not e["points"]:
            e["counts"], e["why"] = True, "not pointing either way today"
        elif len(side) < LONG_MIN:
            e["counts"], e["why"] = True, "only %d such days so far - counts as set" % len(side)
        else:
            gap = st.mean(side) - all_avg
            e["counts"] = gap * e["points"] > 0
            e["why"] = "on such days the next year was %+.0f%% vs %+.0f%% usually - %s" % (
                st.mean(side), all_avg, "agrees, counts" if e["counts"] else "the record disagrees, NOT counted")
        e["counted"] = e["points"] if e["counts"] else 0
    side_ok = {}
    for e in ev:
        for p in (1, -1):
            side = [mv for w, mv in graded if w[e["rule"]] == p]
            side_ok[(e["rule"], p)] = len(side) < LONG_MIN or (st.mean(side) - all_avg) * p > 0
    scored = [(sum(p for r, p in v.items() if p and side_ok[(r, p)]), mv) for v, mv in graded]
    score = sum(e["counted"] for e in ev)
    key = long_key(score)

    def rec(sel):
        g = [mv for sc, mv in scored if sel(sc)]
        if not g:
            return None
        return {"days": len(g), "avg_1y_pct": round(st.mean(g), 1), "rose_pct": round(100.0 * sum(x > 0 for x in g) / len(g), 1)}
    groups = {k: rec(lambda sc, k=k: long_key(sc) == k) for k in LONG_CALLS}
    alld = rec(lambda sc: True)
    cagr = {}
    for yrs in (5, 10):
        t0 = n - 1 - yrs * 365
        if t0 >= 0 and vals[t0]:
            cagr[str(yrs)] = round(((vals[-1] / vals[t0]) ** (1.0 / yrs) - 1) * 100, 1)
    lab, te, adv, adv_te = LONG_CALLS[key]
    g = groups.get(key)
    line = None
    if g and alld:
        line = "Past %s days: 1 year later %+.0f%% on average (higher on %.0f%%) vs %+.0f%% for any day (higher on %.0f%%)." % (
            lab, g["avg_1y_pct"], g["rose_pct"], alld["avg_1y_pct"], alld["rose_pct"])
    span_y = round((n - 365 - Y3) / 365.0, 1)
    live = [e for e in ev if e["counted"]]
    say = lambda lang: (" and " if lang == 0 else " మరియు ").join(
        LONG_PLAIN[e["rule"]][0 if e["counted"] > 0 else 1][lang] for e in live)
    why = ("Because %s." % say(0)) if live else "No long-run rule points either way today."
    why_te = ("కారణం: %s." % say(1)) if live else "ఈరోజు దీర్ఘకాల నియమాలేవీ ఏ వైపూ చూపడం లేదు."
    off = [e["rule"] for e in ev if e["points"] and not e["counts"]]
    if off:
        why += " Not counted (its record disagrees): %s." % ", ".join(off)
    return {"key": key, "label": lab, "telugu": te, "advice": adv, "advice_te": adv_te, "score": score,
            "why": why, "why_te": why_te, "evidence": ev, "groups": groups, "all_days": alld, "record_line": line, "cagr_pct": cagr,
            "years_graded": span_y,
            "note": ("Graded on the price 1 year later over about %.0f years. Those years overlap (about one independent "
                     "result per year), and the rules were switched on/off using the same years, so read it as a guide, "
                     "not proof." % span_y)}


def where(m, home):
    """Which place the metal price is for - shown beside every price."""
    town = home.split(",")[0]
    return {
        "place_note": "Same import price in %s as everywhere in India" % town,
        "short": "All-India import price · world spot + %g%% duty, before GST" % m["duty_pct"],
        "short_te": "అఖిల భారత దిగుమతి ధర · ప్రపంచ ధర + %g%% సుంకం, GST లేకుండా" % m["duty_pct"],
        "detail": "World spot %s in US$ per troy ounce (gold-api.com; history COMEX %s, Yahoo Finance) x the US$/Rs "
                  "rate (Yahoo INR=X) + %g%% import duty, for %s. The same for all of India - not a %s jeweller's "
                  "rate: shops add their own premium, making charges and %g%% GST on top." % (
                      m["spot"], m["futures"], m["duty_pct"], m["purity"], town, m["gst_pct"]),
        "home": home,
    }


# --------------------------------------------------------------------------- one metal
def analyse(key, cfg, live):
    m = cfg["metals"][key]
    fut, fxs = load(key), load("usdinr")
    if len(fut) < 300 or len(fxs) < 300:
        raise RuntimeError("%s: not enough saved history (%d days) - run without --offline once" % (key, len(fut)))
    fx_at = AsOf(fxs)
    lv = live.get(key) or {}
    fx_live = (live.get("usdinr") or {}).get("rate") or fx_at(max(fxs))
    # Line the futures history up with spot.
    last_k = max(fut)
    basis = 1.0
    if lv.get("usd") and lv.get("futures_usd"):
        b = lv["usd"] / lv["futures_usd"]
        if 0.9 < b < 1.1:
            basis = b
    series = {k: round(india(v * basis, fx_at(k), m), 2) for k, v in fut.items() if fx_at(k)}
    spot_usd = lv.get("usd") or fut[last_k] * basis
    series[last_k] = round(india(spot_usd, fx_live, m), 2)
    trading = set(series)
    cal = az.to_calendar(series)
    while cal and cal[0][1] is None:
        cal.pop(0)

    ratio_at = None
    if key == "silver":
        g = load("gold")
        ratio_at = AsOf({k: g[k] / v for k, v in fut.items() if k in g and v})
    scorer = make_scorer(key, m, trading, fx_at, ratio_at)

    idx = az.seasonality(series, FLAT, detrend=True)
    season_asof = az.SeasonAsOf(series, FLAT, detrend=True)
    bt = az.backtest(cal, season_asof)
    fc = az.forecast(cal, idx["index"], bt)
    sig, tr, ind = az.decide(cal, idx, m, fc, bt, season_asof, scorer=scorer, carry=carry,
                             actions=METAL_ACTIONS, days=trading, fmt=inr)
    price = ind["price"]
    gst = m["gst_pct"]
    return {
        "key": key, "label": m["label"], "telugu_name": m["telugu"], "emoji": m["emoji"],
        "unit": m["unit"], "grams": m["grams"], "purity": m["purity"],
        "asof": cal[-1][0].isoformat(),
        "price": round(price), "price_with_gst": round(price * (1 + gst / 100.0)),
        "indicators": ind,
        "signal": sig,
        "long_term": long_view(cal, trading),
        "forecast": fc,
        "forecast_points": {str(h): fc[h - 1] for h in (7, 14, 30) if len(fc) >= h},
        "forecast_reason": az.forecast_reason(cal, idx, bt, fc, sig["evidence"], "metal"),
        "backtest": {str(k): v for k, v in bt.items()},
        "seasonality": {"months": az.MONTHS, **idx, "index": [round(x, 4) for x in idx["index"]]},
        "timing": az.timing(idx, cal, series),
        "carrying_cost_30d_pct": round(carry(m), 2),
        "track_record": tr,
        "predictions": az.predictions_made(cal, season_asof, days=trading),
        "series": [{"date": k, "price": round(series[k])} for k in sorted(series)[-800:]],
        "series_weekly": weekly(series),
        "world": {"usd_oz": round(spot_usd, 2), "usd_oz_futures": lv.get("futures_usd") or fut[last_k],
                  "basis_pct": round((basis - 1) * 100, 2), "usdinr": round(fx_live, 4),
                  "spot_symbol": m["spot"], "futures_symbol": m["futures"], "updated": lv.get("updated"),
                  "fx_chg_30d": round(az.pct(fx_live, fx_at(cal[-1][0] - timedelta(days=30))), 2)},
        "ratio_gold_silver": round(ratio_at(cal[-1][0]), 1) if ratio_at else None,
        "costs": {k: m[k] for k in ("duty_pct", "gst_pct", "sell_discount_pct", "interest_pct_per_month")},
        "convert": {"oz_g": OZ_G, "grams": m["grams"], "duty_pct": m["duty_pct"]},
        "where": where(m, az.default_place(cfg)["location"]),
        "where_by_place": {p["key"]: where(m, p["location"]) for p in az.places(cfg)},
    }


def rule_brief(a):
    """Four lines first - the call, why, what would change it, how sure - then the price."""
    s, ind = a["signal"], a["indicators"]
    f30 = (a.get("forecast_points") or {}).get("30")
    p = lambda v: "%+.1f%%" % v if v is not None else "n/a"
    four, four_te = az.brief_lines(s)
    en = ["%s %s - %s" % (a["asof"], a["label"], four[0])] + four[1:]
    price = "Price: %s %s (%s with %g%% GST); 7 days %s, 30 days %s." % (
        inr(a["price"]), a["unit"].replace("Rs ", ""), inr(a["price_with_gst"]), a["costs"]["gst_pct"],
        p(ind["chg_7d"]), p(ind["chg_30d"]))
    if f30:
        price += " 30-day outlook %s (likely %s - %s)." % (inr(f30["price"]), inr(f30["low"]), inr(f30["high"]))
    en.append(price)
    lt = a.get("long_term")
    if lt:
        en.append("Saving for years: %s - %s %s" % (lt["label"], lt["advice"], lt["why"]))
    unit_te = "10 గ్రాములకు" if a["grams"] == 10 else "కిలోకు"
    te = ["%s %s - %s" % (a["asof"], a["telugu_name"], four_te[0])] + four_te[1:]
    tp = "ధర: %s %s (GST తో %s); 7 రోజుల్లో %s, 30 రోజుల్లో %s." % (
        unit_te, inr(a["price"]), inr(a["price_with_gst"]), p(ind["chg_7d"]), p(ind["chg_30d"]))
    if f30:
        tp += " 30 రోజుల అంచనా %s (%s - %s)." % (inr(f30["price"]), inr(f30["low"]), inr(f30["high"]))
    te.append(tp)
    if lt:
        te.append("ఏళ్ల తరబడి దాచుకునేవారికి: %s - %s %s" % (lt["telugu"], lt["advice_te"], lt["why_te"]))
    return {"source": "rules", "english": "\n".join(en), "telugu": "\n".join(te)}
