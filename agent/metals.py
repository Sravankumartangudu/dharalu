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
    score, evidence, ind = scorer(cal, idx, m, fc, bt)
    act = az.action_for(score, evidence, METAL_ACTIONS)
    tr = az.track_record(cal, season_asof, m, bt, scorer=scorer, carry=carry, actions=METAL_ACTIONS, days=trading)
    price = ind["price"]
    gst = m["gst_pct"]
    return {
        "key": key, "label": m["label"], "telugu_name": m["telugu"], "emoji": m["emoji"],
        "unit": m["unit"], "grams": m["grams"], "purity": m["purity"],
        "asof": cal[-1][0].isoformat(),
        "price": round(price), "price_with_gst": round(price * (1 + gst / 100.0)),
        "indicators": ind,
        "signal": {"score": score, "confidence": az.confidence(score, bt, ind), **act,
                   "evidence": evidence, "max_score": sum(e["max"] for e in evidence)},
        "forecast": fc,
        "forecast_points": {str(h): fc[h - 1] for h in (7, 14, 30) if len(fc) >= h},
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
    }


def rule_brief(a):
    s, ind = a["signal"], a["indicators"]
    f30 = (a.get("forecast_points") or {}).get("30")
    for_ = [e for e in s["evidence"] if e["points"] > 0]
    against = [e for e in s["evidence"] if e["points"] < 0]
    p = lambda v: "%+.1f%%" % v if v is not None else "n/a"
    en = [
        "%s %s - %s (score %+d of %d, confidence %s)" % (a["asof"], a["label"], s["label"], s["score"], s["max_score"], s["confidence"]),
        "If buying: %s  If holding: %s" % (s["buyer"], s["holder"]),
        "Price in India: %s %s (%s with %g%% GST); 7 days %s, 30 days %s. World price US$%s/oz, Rs %.2f per US$." % (
            inr(a["price"]), a["unit"].replace("Rs ", ""), inr(a["price_with_gst"]), a["costs"]["gst_pct"],
            p(ind["chg_7d"]), p(ind["chg_30d"]), format(a["world"]["usd_oz"], ",.2f"), a["world"]["usdinr"]),
    ]
    if f30:
        en.append("30-day outlook: %s (likely range %s - %s)." % (inr(f30["price"]), inr(f30["low"]), inr(f30["high"])))
    if for_:
        en.append("Reasons to buy: " + "; ".join("%s (%s)" % (e["rule"], e["value"]) for e in for_))
    if against:
        en.append("Reasons for caution: " + "; ".join("%s (%s)" % (e["rule"], e["value"]) for e in against))
    conf = {"High": "ఎక్కువ", "Medium": "మధ్యస్థం", "Low": "తక్కువ"}[s["confidence"]]
    unit_te = "10 గ్రాములకు" if a["grams"] == 10 else "కిలోకు"
    te = [
        "%s %s - %s (స్కోరు %+d / %d, నమ్మకం %s)" % (a["asof"], a["telugu_name"], s["telugu"], s["score"], s["max_score"], conf),
        "భారత ధర: %s %s (GST తో %s); 7 రోజుల్లో %s, 30 రోజుల్లో %s." % (
            unit_te, inr(a["price"]), inr(a["price_with_gst"]), p(ind["chg_7d"]), p(ind["chg_30d"])),
    ]
    if f30:
        te.append("30 రోజుల అంచనా: %s (%s - %s మధ్య)." % (inr(f30["price"]), inr(f30["low"]), inr(f30["high"])))
    return {"source": "rules", "english": "\n".join(en), "telugu": "\n".join(te)}
