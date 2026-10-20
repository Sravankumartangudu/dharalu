"""Daily briefing in English + Telugu.

Always builds a rule-based briefing from the analysis. If ANTHROPIC_API_KEY is
set, Claude also writes a richer trader's note from the same numbers (it is told
to use only the numbers given, so it can't invent prices).
"""
import json
import os

MODEL = "claude-opus-5-5"


def _m(v):
    return "Rs %s" % format(int(round(v)), ",") if v is not None else "n/a"


def _p(v):
    return "%+.1f%%" % v if v is not None else "n/a"


def rule_based(a):
    s, b = a["signal"], a["benchmark"]
    f30 = (a.get("forecast_points") or {}).get("30")
    best = a.get("best_source")
    t = a["timing"]
    for_ = [e for e in s["evidence"] if e["points"] > 0]
    against = [e for e in s["evidence"] if e["points"] < 0]

    en = [
        "%s - %s (score %+d of %d, confidence %s)" % (a["asof"], s["label"], s["score"], s["max_score"], s["confidence"]),
        "If buying: %s  If holding stock: %s" % (s["buyer"], s["holder"]),
        "Benchmark price (median of %s): %s/qtl, 7 days %s, 30 days %s." % (
            ", ".join(x.replace(" APMC", "") for x in b["markets"]), _m(b["price"]), _p(b["chg_7d"]), _p(b["chg_30d"])),
    ]
    if f30:
        en.append("30-day outlook: %s (likely range %s - %s)." % (_m(f30["price"]), _m(f30["low"]), _m(f30["high"])))
        fr = a.get("forecast_reason")
        if fr:
            en.append("Why: " + fr["summary"] + " " + "Parts: " + ", ".join("%s %+.1f%%" % (d["name"].lower(), d["pct"]) for d in fr["drivers"]) + ".")
    if best:
        en.append("Cheapest to bring to Srikakulam: %s at %s/qtl landed (mandi %s + freight %s)." % (
            best["market"], _m(best["landed"]), _m(best["mandi_price"]), _m(best["freight"])))
    if for_:
        en.append("Reasons to buy: " + "; ".join("%s (%s)" % (e["rule"], e["value"]) for e in for_))
    if against:
        en.append("Reasons for caution: " + "; ".join("%s (%s)" % (e["rule"], e["value"]) for e in against))
    en.append("Season: cheapest in %s, dearest in %s (about %.0f%% swing)." % (
        " & ".join(t["cheapest_months"]), " & ".join(t["dearest_months"]), t["seasonal_swing_pct"]))

    te = [
        "%s - %s (స్కోరు %+d / %d, నమ్మకం %s)" % (a["asof"], s["telugu"], s["score"], s["max_score"],
                                               {"High": "ఎక్కువ", "Medium": "మధ్యస్థం", "Low": "తక్కువ"}[s["confidence"]]),
        "ప్రామాణిక ధర: క్వింటాల్‌కు %s; 7 రోజుల్లో %s, 30 రోజుల్లో %s." % (_m(b["price"]), _p(b["chg_7d"]), _p(b["chg_30d"])),
    ]
    if f30:
        te.append("30 రోజుల అంచనా: %s (%s - %s మధ్య)." % (_m(f30["price"]), _m(f30["low"]), _m(f30["high"])))
        if a.get("forecast_reason"):
            te.append(a["forecast_reason"]["telugu"])
    if best:
        te.append("శ్రీకాకుళానికి చౌకగా: %s - రవాణాతో కలిపి %s." % (best["market"], _m(best["landed"])))
    te.append("సాధారణంగా %s లో ధర తక్కువ, %s లో ఎక్కువ." % (
        ", ".join(t["cheapest_months"]), ", ".join(t["dearest_months"])))
    return {"source": "rules", "english": "\n".join(en), "telugu": "\n".join(te)}


PROMPT = """You are the market analyst for a wheat trading business in Srikakulam, Andhra Pradesh.
They buy wheat from mandis in Madhya Pradesh / Rajasthan / Maharashtra (Andhra Pradesh has no wheat mandis)
and sell locally. Below is today's analysis as JSON. Every number in it comes from Agmarknet (data.gov.in)
or from the business's own cost settings.

Write a short trader's note (max ~180 words) in plain English, then the same note in Telugu.
- Start with the action and who it applies to (buying vs. holding stock).
- Give the 2-4 strongest reasons, each with its actual number from the JSON (the proof).
- Name the main risk that would make this call wrong and what to watch for it.
- Mention the cheapest source mandi and its landed cost.
Use ONLY numbers that appear in the JSON - never invent prices, dates or news.
Return JSON: {"english": "...", "telugu": "..."} and nothing else.

ANALYSIS:
%s"""


def with_claude(a, base):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    slim = {k: a[k] for k in ("asof", "benchmark", "signal", "forecast_points", "forecast_reason", "backtest", "timing", "msp",
                              "best_source", "selling_reference", "margin_vs_selling_ref",
                              "carrying_cost_30d_pct") if k in a}
    slim["landed_top5"] = (a.get("landed") or [])[:5]
    slim["track_record"] = a["track_record"]["summary"]
    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            messages=[{"role": "user", "content": PROMPT % json.dumps(slim, default=str)}],
            extra_body={"fallbacks": "default", "output_config": {"effort": "medium"}},  # works on old SDKs too
        )
        if resp.stop_reason == "refusal":
            return None
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
        out = json.loads(text[text.find("{"): text.rfind("}") + 1])
        return {"source": "claude (%s)" % resp.model, "english": out["english"], "telugu": out["telugu"]}
    except Exception as e:  # briefing is optional - never fail the run for it
        print("  Claude briefing skipped: %s" % e)
        return None


def build(a):
    base = rule_based(a)
    ai = with_claude(a, base)
    return {"rules": base, "ai": ai}
