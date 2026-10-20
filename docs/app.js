/* Dharalu dashboard - reads what the agent publishes in data/:
     summary.json            every commodity's call, price and proof in one small file
     latest.json             wheat (mandis, landed cost, the full analysis)
     <metal>.json            gold / silver / platinum: call, proof, forecast
     <metal>-history.json    their long price history and day-by-day replay
   Gold, silver and platinum are also priced live from gold-api.com every 5 minutes.
   Trades and local rates live only in this browser (localStorage). */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const rs = v => v == null || isNaN(v) ? "–" : "₹" + Math.round(v).toLocaleString("en-IN");
const pc = (v, d = 1) => v == null || isNaN(v) ? "–" : (v > 0 ? "+" : "") + v.toFixed(d) + "%";
const cls = v => v > 0 ? "pos" : v < 0 ? "neg" : "zero";
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const fmtDate = s => { const d = new Date(s + "T00:00:00"); return d.getDate() + " " + MON[d.getMonth()] + " " + d.getFullYear(); };
const fmtShort = s => { const d = new Date(s + "T00:00:00"); return d.getDate() + " " + MON[d.getMonth()]; };
const hm = iso => { const d = new Date(iso); return isNaN(d) ? "–" : d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }); };
const dayDiff = (a, b) => Math.round((new Date(b) - new Date(a)) / 864e5);
const addDays = (s, n) => { const d = new Date(s + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const signed = n => (n > 0 ? "+" : "") + n;
const store = {
  get: (k, dflt) => { try { return JSON.parse(localStorage.getItem("dh." + k)) ?? dflt; } catch { return dflt; } },
  set: (k, v) => localStorage.setItem("dh." + k, JSON.stringify(v)),
};
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

// WheatWise 1.x kept everything under "ww." - copy it over once (same origin, so trades carry across).
try {
  const old = [];
  for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (k && k.startsWith("ww.")) old.push(k); }
  old.forEach(k => { const n = "dh." + k.slice(3); if (localStorage.getItem(n) === null) localStorage.setItem(n, localStorage.getItem(k)); });
} catch { }

const EVERY = 5 * 60 * 1000;   // live prices + new agent output, every 5 minutes
const LIVE_URL = "https://api.gold-api.com/price/";
const COLOR = { wheat: "--s3", gold: "--s4", silver: "--s1", platinum: "--s2" };   // colour follows the commodity
const CALL_COLOR = { buy: "#0ca30c", hold: "#c98500", wait: "#8a8984", sell: "#d03b3b" };

let S = null;          // summary.json
const D = {};          // commodity -> full analysis (loaded on demand)
let C = "all";         // commodity on screen ("all" = overview)
let V = "today";       // view (sub-tab) on screen
let A = null;          // = D[C]
let PX = {};           // date -> price, for A
let SIG = {};          // date -> { score, key } (replayed + live), for A
const LIVE = {};       // metal -> { usd, rs, updated }
let LANG = "en";
let lastTick = 0;

const isMetal = k => k && k !== "wheat" && k !== "all";
const VIEWS = [
  ["today", "Today · ఈరోజు"], ["timeline", "Timeline · past → future"], ["forecast", "Forecast · అంచనా"],
  ["pre", "Before you trade"], ["trades", "My trades · after"], ["record", "Agent track record"],
  ["mandis", "Mandis & landed cost", "wheat"], ["watch", "What to watch"],
];

/* ------------------------------------------------------------------ charts */
function niceTicks(lo, hi, n = 5) {
  const span = hi - lo || 1, step0 = span / n, mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= step0);
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(v);
  return out;
}

/* Line chart: series [{name, color, dash, pts:[{x:"YYYY-MM-DD", y}], band:[{x, lo, hi}]}], refs [{y, label}].
   Timeline extras: marker {x, label} (a "Today" line), future x (shade what is still to come),
   strip [{x, color}] (one coloured cell per day under the plot), dots [{x, y, color, label}],
   tipExtra(x) -> html added to the hover tooltip. */
function lineChart(el, { series, refs = [], height = 300, yfmt = rs, marker = null, future = null, strip = null, dots = [], tipExtra = null }) {
  const W = 1000, H = height, m = { l: 62, r: 92, t: marker ? 24 : 12, b: strip ? 42 : 28 };
  const all = series.flatMap(s => s.pts.map(p => p.x).concat((s.band || []).map(p => p.x))).concat(dots.map(d => d.x));
  const xs = [...new Set(all)].sort();
  if (!xs.length) { el.innerHTML = '<p class="muted">No data yet.</p>'; return; }
  const t0 = Date.parse(xs[0]), t1 = Date.parse(xs[xs.length - 1]) || t0 + 1;
  let ys = series.flatMap(s => s.pts.map(p => p.y).concat((s.band || []).flatMap(b => [b.lo, b.hi]))).filter(v => v != null);
  ys = ys.concat(refs.map(r => r.y), dots.map(d => d.y));
  let lo = Math.min(...ys), hi = Math.max(...ys); const pad = (hi - lo) * 0.08 || 50; lo -= pad; hi += pad;
  const X = s => m.l + (Date.parse(s) - t0) / (t1 - t0 || 1) * (W - m.l - m.r);
  const Y = v => m.t + (hi - v) / (hi - lo) * (H - m.t - m.b);
  let g = "";
  if (future && Date.parse(future) < t1) {
    const x0 = Math.max(m.l, X(future));
    g += `<rect x="${x0}" y="${m.t}" width="${W - m.r - x0}" height="${H - m.t - m.b}" fill="${css("--wash")}"/>`;
    g += `<text x="${x0 + 6}" y="${m.t + 13}">Future →</text>`;
    if (x0 - m.l > 70) g += `<text x="${x0 - 6}" y="${m.t + 13}" text-anchor="end">← Past</text>`;
  }
  for (const v of niceTicks(lo, hi)) g += `<line class="gridline" x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${m.l - 8}" y="${Y(v) + 4}" text-anchor="end">${yfmt(v)}</text>`;
  const span = (t1 - t0) / 864e5;
  if (span < 75) {
    // short ranges: a label each week
    for (let s = xs[0]; Date.parse(s) <= t1; s = addDays(s, 7)) g += `<text x="${X(s)}" y="${H - 8}" text-anchor="middle">${fmtShort(s)}</text>`;
  } else {
    const months = Math.max(1, Math.round(span / 30.4));
    const every = months > 60 ? 12 : months > 30 ? 6 : months > 14 ? 3 : months > 6 ? 2 : 1;
    const d0 = new Date(t0); d0.setDate(1);
    for (let d = new Date(d0); d <= new Date(t1); d.setMonth(d.getMonth() + 1)) {
      if (d < new Date(t0) || d.getMonth() % every) continue;
      const s = d.toISOString().slice(0, 10);
      const lbl = every >= 12 ? String(d.getFullYear()) : d.getMonth() === 0 || every >= 3 ? MON[d.getMonth()] + " " + String(d.getFullYear()).slice(2) : MON[d.getMonth()];
      g += `<text x="${X(s)}" y="${H - 8}" text-anchor="middle">${lbl}</text>`;
    }
  }
  g += `<line class="axis" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/>`;
  if (strip && strip.length) {
    // merge runs of the same colour into one cell
    const day = (W - m.l - m.r) / Math.max(1, span), y = H - m.b + 5;
    let run = null;
    const flush = () => { if (run) g += `<rect x="${run.x0}" y="${y}" width="${Math.max(1, run.x1 - run.x0)}" height="8" rx="2" fill="${run.c}"/>`; };
    for (const s of strip) {
      if (Date.parse(s.x) < t0 || Date.parse(s.x) > t1) continue;
      const x = X(s.x);
      if (run && run.c === s.color && x - run.x1 < day * 6) run.x1 = x + day; else { flush(); run = { c: s.color, x0: x, x1: x + day }; }
    }
    flush();
  }
  for (const r of refs) g += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(r.y)}" y2="${Y(r.y)}" stroke="${css("--muted")}" stroke-dasharray="3 4"/><text class="lbl" x="${W - m.r + 6}" y="${Y(r.y) + 4}">${esc(r.label)}</text>`;
  for (const s of series) {
    if (s.band && s.band.length) {
      const up = s.band.map(b => `${X(b.x)},${Y(b.hi)}`), dn = s.band.slice().reverse().map(b => `${X(b.x)},${Y(b.lo)}`);
      g += `<polygon points="${up.concat(dn).join(" ")}" fill="${s.color}" opacity=".16"/>`;
    }
    let path = "", pen = false;
    for (const p of s.pts) { if (p.y == null) { pen = false; continue; } path += (pen ? "L" : "M") + X(p.x).toFixed(1) + "," + Y(p.y).toFixed(1); pen = true; }
    g += `<path d="${path}" fill="none" stroke="${s.color}" stroke-width="${s.width || 2}" stroke-linejoin="round" ${s.dash ? `stroke-dasharray="${s.dash === true ? "6 4" : s.dash}"` : ""}/>`;
    const last = s.pts.filter(p => p.y != null).pop();
    if (last && s.label !== false) g += `<text class="lbl" x="${X(last.x) + 6}" y="${Y(last.y) + 4}">${esc(s.short || s.name)}</text>`;
  }
  if (marker) {
    const x = X(marker.x);
    g += `<line x1="${x}" x2="${x}" y1="${m.t - 4}" y2="${H - m.b}" stroke="${css("--ink-2")}" stroke-dasharray="2 3"/><text class="lbl" x="${x}" y="${m.t - 9}" text-anchor="middle">${esc(marker.label)}</text>`;
  }
  for (const d of dots) {
    g += `<circle class="livedot" cx="${X(d.x)}" cy="${Y(d.y)}" r="6" fill="${d.color}" stroke="${css("--surface")}" stroke-width="2"/>`;
    if (d.label) g += `<text class="lbl" x="${X(d.x) - 10}" y="${Y(d.y) - 10}" text-anchor="end">${esc(d.label)}</text>`;
  }
  g += `<line id="xh" y1="${m.t}" y2="${H - m.b}" stroke="${css("--axis")}" visibility="hidden"/><g id="dots"></g>`;
  g += `<rect x="${m.l}" y="${m.t}" width="${W - m.l - m.r}" height="${H - m.t - m.b + (strip ? 14 : 0)}" fill="transparent" id="hit"/>`;
  el.classList.add("chart");
  el.innerHTML = `<div class="legend">${series.length > 1 ? series.map(s => `<span class="${s.dash ? "dash" : ""}" style="--c:${s.color}">${esc(s.name)}</span>`).join("") : ""}</div>
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(series.map(s => s.name).join(", "))}">${g}</svg><div class="tip"></div>`;
  const svg = $("svg", el), tip = $(".tip", el), xh = $("#xh", el), dl = $("#dots", el);
  const lookup = series.map(s => { const o = {}; s.pts.forEach(p => o[p.x] = p.y); (s.band || []).forEach(b => o[b.x + "~"] = b); return o; });
  const move = ev => {
    const r = svg.getBoundingClientRect(), vx = (ev.clientX - r.left) / r.width * W;
    const t = t0 + (vx - m.l) / (W - m.l - m.r) * (t1 - t0);
    let best = xs[0], bd = Infinity; for (const x of xs) { const dd = Math.abs(Date.parse(x) - t); if (dd < bd) { bd = dd; best = x; } }
    xh.setAttribute("x1", X(best)); xh.setAttribute("x2", X(best)); xh.setAttribute("visibility", "visible");
    let rows = "", dd = "";
    series.forEach((s, i) => {
      const y = lookup[i][best], b = lookup[i][best + "~"];
      if (y == null) return;
      dd += `<circle cx="${X(best)}" cy="${Y(y)}" r="4.5" fill="${s.color}" stroke="${css("--surface")}" stroke-width="2"/>`;
      rows += `<div><span class="sw" style="background:${s.color}"></span>${esc(s.tipName || s.name)}: <b>${yfmt(y)}</b>${b ? ` <span class="muted">(${yfmt(b.lo)}–${yfmt(b.hi)})</span>` : ""}</div>`;
    });
    const extra = tipExtra ? tipExtra(best) : "";
    dl.innerHTML = dd;
    if (!rows && !extra) { tip.style.display = "none"; return; }
    tip.innerHTML = `<div class="muted">${fmtDate(best)}</div>${rows}${extra || ""}`;
    tip.style.display = "block";
    const px = X(best) / W * r.width, left = px > r.width * 0.6 ? px - tip.offsetWidth - 12 : px + 12;
    tip.style.left = left + "px"; tip.style.top = "26px";
  };
  $("#hit", el).addEventListener("mousemove", move);
  $("#hit", el).addEventListener("mouseleave", () => { tip.style.display = "none"; xh.setAttribute("visibility", "hidden"); dl.innerHTML = ""; });
}

/* Bars around a baseline (diverging): items [{label, value, tip}] */
function barChart(el, { items, base = 0, height = 220, fmt = v => v.toFixed(1), colorPos, colorNeg, highlight = -1 }) {
  const W = 1000, H = height, m = { l: 50, r: 10, t: 16, b: 26 };
  const vals = items.map(i => i.value);
  let lo = Math.min(base, ...vals), hi = Math.max(base, ...vals); const pad = (hi - lo) * .12 || 1; lo -= pad; hi += pad;
  const Y = v => m.t + (hi - v) / (hi - lo) * (H - m.t - m.b);
  const bw = (W - m.l - m.r) / items.length, gap = Math.max(2, bw * 0.22);
  let g = "";
  for (const v of niceTicks(lo, hi, 4)) g += `<line class="gridline" x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${m.l - 6}" y="${Y(v) + 4}" text-anchor="end">${fmt(v)}</text>`;
  items.forEach((it, k) => {
    const x = m.l + k * bw + gap / 2, w = bw - gap, y0 = Y(base), y1 = Y(it.value);
    const top = Math.min(y0, y1), h = Math.max(1, Math.abs(y1 - y0)), c = it.value >= base ? colorPos : colorNeg, rr = Math.min(4, h / 2, w / 2);
    const d = it.value >= base
      ? `M${x},${y0}V${top + rr}Q${x},${top} ${x + rr},${top}H${x + w - rr}Q${x + w},${top} ${x + w},${top + rr}V${y0}Z`
      : `M${x},${y0}V${top + h - rr}Q${x},${top + h} ${x + rr},${top + h}H${x + w - rr}Q${x + w},${top + h} ${x + w},${top + h - rr}V${y0}Z`;
    g += `<path d="${d}" fill="${c}" ${k === highlight ? `stroke="${css("--ink")}" stroke-width="2"` : ""}><title>${esc(it.tip || it.label + ": " + fmt(it.value))}</title></path>`;
    g += `<text x="${x + w / 2}" y="${H - 8}" text-anchor="middle" ${k === highlight ? 'class="lbl"' : ""}>${esc(it.label)}</text>`;
    g += `<rect x="${x - gap / 2}" y="${m.t}" width="${bw}" height="${H - m.t - m.b}" fill="transparent" data-k="${k}"/>`;
  });
  g += `<line class="axis" x1="${m.l}" x2="${W - m.r}" y1="${Y(base)}" y2="${Y(base)}"/>`;
  el.classList.add("chart");
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img">${g}</svg><div class="tip"></div>`;
  const svg = $("svg", el), tip = $(".tip", el);
  svg.querySelectorAll("rect[data-k]").forEach(r => {
    r.addEventListener("mousemove", ev => {
      const it = items[+r.dataset.k], b = svg.getBoundingClientRect();
      tip.innerHTML = it.tip || `${esc(it.label)}: <b>${fmt(it.value)}</b>`; tip.style.display = "block";
      const px = ev.clientX - b.left; tip.style.left = (px > b.width * .6 ? px - tip.offsetWidth - 12 : px + 12) + "px"; tip.style.top = "8px";
    });
    r.addEventListener("mouseleave", () => tip.style.display = "none");
  });
}

/* Tiny trend line for the overview cards: last 90 days + the 30-day forecast. */
function spark(el, hist, fc, color) {
  if (!el || !hist.length) return;
  const W = 300, H = 54, pts = hist.concat(fc), ys = pts.map(p => p.y);
  const lo = Math.min(...ys), hi = Math.max(...ys), t0 = Date.parse(pts[0].x), t1 = Date.parse(pts[pts.length - 1].x);
  const X = s => 2 + (Date.parse(s) - t0) / (t1 - t0 || 1) * (W - 4), Y = v => 4 + (hi - v) / (hi - lo || 1) * (H - 8);
  const line = a => a.map((p, i) => (i ? "L" : "M") + X(p.x).toFixed(1) + "," + Y(p.y).toFixed(1)).join("");
  const last = hist[hist.length - 1];
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">
    <rect x="${X(last.x)}" y="0" width="${W - X(last.x)}" height="${H}" fill="${css("--wash")}"/>
    <path d="${line(hist)}" fill="none" stroke="${color}" stroke-width="2" vector-effect="non-scaling-stroke"/>
    <path d="${line([last].concat(fc))}" fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="4 3" vector-effect="non-scaling-stroke"/>
    <circle cx="${X(last.x)}" cy="${Y(last.y)}" r="3" fill="${color}"/></svg>`;
}

/* ------------------------------------------------------------------ helpers */
const localRate = () => store.get("localRate", null);
const priceOf = a => a.benchmark ? a.benchmark.price : a.price;
const unitTxt = () => C === "wheat" ? "₹ per quintal" : A.unit.replace("Rs ", "₹ ");
const qtyUnit = () => C === "wheat" ? "qtl" : "g";
function nowPrice(k) {
  const it = S && S.items[k];
  if (!it) return null;
  const lv = LIVE[k];
  return lv ? lv.rs : it.price;
}
function forecastAt(days) {
  const f = A.forecast || [];
  return f[Math.min(f.length, Math.max(1, days)) - 1];
}
function verdictWord(score, key) {
  if (key) return key.replace("_", " ");
  return score >= 3 ? "STRONG BUY" : score >= 1 ? "BUY" : score > -1 ? "WAIT" : score > -3 ? "SELL" : "STRONG SELL";
}
// Since 2.2 rules are weighted, so scores can be fractional: the call's key decides the group.
const GROUP_OF = { STRONG_BUY: "buy", BUY: "buy", HOLD: "hold", WAIT: "wait", SELL: "sell", STRONG_SELL: "sell" };
const callGroup = (score, key) => GROUP_OF[key] || (score >= 1 ? "buy" : score <= -1 ? "sell" : "wait");
const absTxt = n => Math.abs(Math.round(+n * 10) / 10);
const scoreTxt = n => n == null || n === "" ? "–" : (+n > 0 ? "+" : +n < 0 ? "−" : "") + Math.abs(Math.round(+n * 10) / 10);
function tableToggle(id, head, rows, title = "Show as table") {
  return `<details><summary>${title}</summary><div class="tablewrap"><table id="${id}"><tr>${head.map(h => `<th>${h}</th>`).join("")}</tr>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("")}</table></div></details>`;
}
function liveNote(k) {
  const lv = LIVE[k];
  return lv ? `<span class="live">live · ${hm(lv.updated || lv.at)}</span>` : "";
}

/* ------------------------------------------------------------------ shared Today pieces */
function scoreGauge(s) {
  // A fractional score on a −max..+max line: the fill runs from the middle to the score.
  const m = s.max_score || 1, w = Math.min(50, Math.abs(s.score) / m * 50);
  const band = v => `<i style="left:${50 + v / m * 50}%"></i>`;
  return `<div class="gauge" title="Score ${scoreTxt(s.score)} of ±${absTxt(m)}">
    <b class="${cls(s.score)}" style="${s.score >= 0 ? "left" : "right"}:50%;width:${w}%"></b>${[-3, -1, 1, 3].filter(v => Math.abs(v) < m).map(band).join("")}</div>`;
}
function signalCard(s, brief) {
  const te = LANG === "te";
  return `
  <div class="card signal">
    <div class="badge ${s.key}">
      <div class="kind">${A.emoji} ${esc(A.label)} · ${esc(A.telugu_name)}</div>
      <div class="big">${esc(s.label)}</div><div class="te">${esc(s.telugu)}</div>
      ${scoreGauge(s)}
      <div class="meta">Score ${scoreTxt(s.score)} of ±${absTxt(s.max_score)} · Confidence ${esc(s.confidence)}</div>
      <div class="meta">${fmtDate(A.asof)}</div>
    </div>
    <div>
      ${s.plain ? `<p class="plain" data-en="${esc(s.plain)}" data-te="${esc(s.plain_te || s.plain)}">${esc(te ? s.plain_te || s.plain : s.plain)}</p>` : ""}
      ${s.pending ? `<div class="pending">⏳ ${esc(s.pending.note)}</div>` : ""}
      <div class="advice"><div><b>If you are buying</b>${esc(s.buyer)}</div><div><b>If you are holding ${C === "wheat" ? "stock" : esc(A.label.toLowerCase())}</b>${esc(s.holder)}</div></div>
      <div class="facts">
        ${A.where ? `<div><span>📍 Prices from</span><span title="${esc(A.where.detail)}"><span data-en="${esc(A.where.short)}" data-te="${esc(A.where.short_te || A.where.short)}">${esc(te ? A.where.short_te || A.where.short : A.where.short)}</span>
          <br><span class="muted">${esc(A.where.detail)}</span>${A.where.landed ? `<br><span data-en="${esc(A.where.landed)}" data-te="${esc(A.where.landed_te || A.where.landed)}">${esc(te ? A.where.landed_te || A.where.landed : A.where.landed)}</span>` : ""}</span></div>` : ""}
        ${s.change_line ? `<div><span>🎯 What would change it</span><span data-en="${esc(s.change_line)}" data-te="${esc(s.change_line_te || s.change_line)}">${esc(te ? s.change_line_te || s.change_line : s.change_line)}</span></div>` : ""}
        ${s.record_line ? `<div><span>📊 Its record</span><span>${esc(s.record_line)}</span></div>` : ""}
        ${s.confidence_why ? `<div><span>🤔 Why ${esc(s.confidence)} confidence</span><span>${s.confidence_why.map(esc).join(" · ")}</span></div>` : ""}
        ${s.equal && s.equal.key !== s.key ? `<div><span>⚖️ Without learned weights</span><span>every rule counting the same would say <b>${esc(s.equal.label)}</b> (${scoreTxt(s.equal.score)}) - <a href="#${C}/record">which way did better?</a></span></div>` : ""}
      </div>
      <div class="tabs2"><button data-lang="en" class="${LANG === "en" ? "primary" : ""}">English</button><button data-lang="te" class="${LANG === "te" ? "primary" : ""}">తెలుగు</button>
        <span class="muted small" style="align-self:center">Briefing by ${esc(brief.source)}</span></div>
      <div class="pre" id="brief">${esc(te ? brief.telugu : brief.english)}</div>
    </div>
  </div>${changesCard(s)}${longTermCard()}`;
}
function changesCard(s) {
  const c = s.changes;
  if (!c) return "";
  const head = c.call_changed
    ? `The call changed from <b>${esc(c.label_was)}</b> (${scoreTxt(c.score_was)}) to <b>${esc(s.label)}</b> (${scoreTxt(s.score)}).`
    : `The call stayed <b>${esc(s.label)}</b> (score ${scoreTxt(c.score_was)} → ${scoreTxt(s.score)}).`;
  const rows = c.rules.map(r => `<tr><td><b>${esc(r.rule)}</b></td><td class="small">${esc(r.value_was || "–")}</td><td class="small">${esc(r.value_now || "–")}</td>
    <td class="num pts ${cls(r.was)}">${scoreTxt(r.was)}</td><td class="num pts ${cls(r.now)}">${scoreTxt(r.now)}</td></tr>`).join("");
  return `<div class="card changes"><b>🔄 What changed since ${fmtDate(c.since)}</b> ${head}
    ${c.rules.length ? `<div class="tablewrap"><table><tr><th>Rule</th><th>Then</th><th>Now</th><th class="num">Counted then</th><th class="num">Now</th></tr>${rows}</table></div>`
      : `<div class="small muted">No rule moved - only the prices did.</div>`}</div>`;
}
function longTermCard() {
  const L = A.long_term;
  if (!L) return "";
  const te = LANG === "te";
  const g = L.groups || {}, all = L.all_days || {};
  const rows = (L.evidence || []).map(e => `<tr><td><b>${esc(e.rule)}</b><div class="why">${esc(e.test)}</div></td><td class="small">${esc(e.value)}</td>
    <td class="small ${e.counts ? "" : "muted"}">${esc(e.why)}</td><td class="num pts ${cls(e.counted)}">${scoreTxt(e.counted)}</td></tr>`).join("");
  return `<div class="card longterm">
    <div class="lt-head"><span class="pill lt ${L.key}">${esc(L.label)}</span> <b>Saving for years (1 year or more)</b> <span class="te small">${esc(L.telugu)}</span></div>
    <p data-en="${esc(L.advice)}" data-te="${esc(L.advice_te || L.advice)}">${esc(te ? L.advice_te || L.advice : L.advice)}</p>
    <p class="small" data-en="${esc(L.why)}" data-te="${esc(L.why_te || L.why)}">${esc(te ? L.why_te || L.why : L.why)}</p>
    <p class="small">📊 ${esc(L.record_line)}${L.cagr_pct ? ` · ${A.label} grew ${L.cagr_pct["5"] != null ? `${pc(L.cagr_pct["5"])} a year over 5 years` : ""}${L.cagr_pct["10"] != null ? `, ${pc(L.cagr_pct["10"])} a year over 10` : ""}.` : ""}</p>
    <details><summary>The long-term rules and their record</summary><div class="tablewrap"><table>
      <tr><th>Rule</th><th>Today</th><th>Its record (price 1 year later)</th><th class="num">Counted</th></tr>${rows}</table></div>
      <table class="small"><tr><th>Past days that said</th><th class="num">Days</th><th class="num">Avg 1 year later</th><th class="num">Higher on</th></tr>
      ${["ADD", "STEADY", "GO_SLOW"].filter(k => g[k]).map(k => `<tr><td>${k.replace("_", " ")}</td><td class="num">${g[k].days}</td><td class="num ${cls(g[k].avg_1y_pct)}">${pc(g[k].avg_1y_pct)}</td><td class="num">${g[k].rose_pct}%</td></tr>`).join("")}
      <tr><td><i>Any day</i></td><td class="num">${all.days || "–"}</td><td class="num ${cls(all.avg_1y_pct)}">${pc(all.avg_1y_pct)}</td><td class="num">${all.rose_pct}%</td></tr></table>
      <p class="small muted">${esc(L.note)}</p></details>
  </div>`;
}
function wireBrief(brief) {
  document.querySelectorAll("[data-lang]").forEach(bt => bt.onclick = () => {
    LANG = bt.dataset.lang;
    document.querySelectorAll("[data-lang]").forEach(x => x.classList.toggle("primary", x === bt));
    $("#brief").textContent = LANG === "te" ? brief.telugu : brief.english;
    document.querySelectorAll("[data-en]").forEach(x => x.textContent = LANG === "te" ? x.dataset.te : x.dataset.en);
  });
}
function proofTable(s) {
  const rec = e => e.rule_record && e.rule_record.votes
    ? `${e.rule_record.votes} past votes, right ${e.rule_record.right_pct}% vs ${e.rule_record.usual_pct}% usual (edge ${signed(e.rule_record.edge_pts)})` : "";
  return `
  <h2>Why this call - the proof</h2>
  <p class="ink2 small">Each rule below looks at real data and gives points. Each rule's points are then multiplied by a <b>weight</b> it earned from its own past record
    (only days whose result was already known at the time - no peeking): 2× if it beat the usual rate by 10+ points, 1× if by 3+, ½ if barely, 0 if it was worse than guessing.
    The forecast and trend rules all read the recent direction, so together they count at most ±2.
    Total ≥ +3 = strong buy, +1 to +3 = buy, between −1 and +1 = hold (if the forward-looking rules still point up) or wait, −1 to −3 = sell, ≤ −3 = strong sell.</p>
  <div class="card tablewrap"><table class="proof">
    <tr><th>Rule</th><th>What the data shows today</th><th>Test used</th><th class="num">Points</th><th class="num">Weight</th><th class="num">Counted</th></tr>
    ${s.evidence.map(e => `<tr><td data-label="Rule"><b>${esc(e.rule)}</b><div class="why">${esc(e.why)}</div></td>
      <td data-label="What the data shows today">${esc(e.value)}<div class="why">Source: ${esc(e.source)}</div></td><td data-label="Test used" class="small ink2">${esc(e.test)}</td>
      <td data-label="Points" class="num pts ${cls(e.points)}">${signed(e.points)}</td>
      <td data-label="Weight" class="num" title="${esc(rec(e))}">${e.weight != null ? `×${e.weight}` : "×1"}<div class="why">${esc(e.weight_why || "")}</div></td>
      <td data-label="Counted" class="num pts ${cls(e.counted ?? e.points)}">${scoreTxt(e.counted ?? e.points)}${e.capped && Math.abs((e.counted ?? 0) - e.points * (e.weight ?? 1)) > 0.01 ? `<div class="why">trend cap</div>` : ""}</td></tr>`).join("")}
    <tr><td colspan="5" class="total"><b>Total score</b></td><td class="num pts total ${cls(s.score)}">${scoreTxt(s.score)}</td></tr>
  </table></div>
  ${s.trend_cap ? `<p class="small ink2">🧢 ${esc(s.trend_cap)}</p>` : ""}`;
}
function workedBefore(s) {
  const tr = A.track_record.summary, live = A.track_record.live || {};
  const g = callGroup(s.score, s.key), gkey = g + "_days";
  // Under 10 days in the last year proves little - quote the whole-history replay instead.
  const thin = !(tr[gkey] && tr[gkey].days >= 10) && A.track_record.summary_all && A.track_record.summary_all[gkey];
  const grp = thin ? A.track_record.summary_all[gkey] : tr[gkey];
  const span = thin ? `since ${fmtDate(A.track_record.since)}` : "in the last year";
  const grpName = { buy: "BUY", sell: "SELL", hold: "HOLD", wait: "WAIT" }[g];
  const cost = C === "wheat" ? "the holding cost" : "bank interest";
  let line = "";
  if (grp) {
    line = g === "buy"
      ? `On the <b>${grp.days}</b> past days ${span} when these same rules said <b>${grpName}</b>, the price 30 days later was higher <b>${grp.rose_pct}%</b> of the time (average move <b class="${cls(grp.avg_move_pct)}">${pc(grp.avg_move_pct)}</b>; beat ${cost} ${grp.beat_holding_cost_pct}% of the time).`
      : g === "sell"
        ? `On the <b>${grp.days}</b> past days ${span} when these rules said <b>${grpName}</b>, the price 30 days later was lower <b>${(100 - grp.rose_pct).toFixed(1)}%</b> of the time (average move <b class="${cls(grp.avg_move_pct)}">${pc(grp.avg_move_pct)}</b>).`
        : g === "hold"
          ? `On the <b>${grp.days}</b> past HOLD days ${span}, keeping it beat ${cost} <b>${grp.beat_holding_cost_pct}%</b> of the time (price rose ${grp.rose_pct}% of the time, average move <b class="${cls(grp.avg_move_pct)}">${pc(grp.avg_move_pct)}</b>).`
          : `On the <b>${grp.days}</b> past WAIT days ${span}, the average 30-day move was <b class="${cls(grp.avg_move_pct)}">${pc(grp.avg_move_pct)}</b> - not enough to beat ${cost}.`;
  }
  return `<div class="card"><b>Has this worked before?</b> ${line || "Not enough history yet."}
    ${live.graded ? `<br>Live calls graded so far: <b>${live.graded}</b>, right <b>${live.right_pct}%</b>.` : `<br><span class="muted small">Live calls are graded automatically 30 days after each call (${live.calls || 0} logged so far).</span>`}
    <div class="small muted">See the "Agent track record" tab for every past call, and "Timeline" for each forecast against what really happened.</div></div>`;
}

/* ------------------------------------------------------------------ TODAY */
function renderToday() { (C === "wheat" ? renderTodayWheat : renderTodayMetal)(); }

function renderTodayWheat() {
  const s = A.signal, b = A.benchmark, f30 = A.forecast_points["30"], best = A.best_source;
  const brief = A.briefing.ai || A.briefing.rules;
  const lr = localRate();
  $("#today").innerHTML = `${signalCard(s, brief)}${proofTable(s)}${workedBefore(s)}
  <h2>Key numbers</h2>
  <div class="grid kn">
    <div class="tile"><div class="k">Benchmark wholesale price (${b.markets.map(x => x.replace(" APMC", "")).join(", ")} mandis)</div><div class="v">${rs(b.price)}</div>
      <div class="d">1 day <span class="${cls(b.chg_1d)}">${pc(b.chg_1d)}</span> · 7 days <span class="${cls(b.chg_7d)}">${pc(b.chg_7d)}</span> · 30 days <span class="${cls(b.chg_30d)}">${pc(b.chg_30d)}</span></div></div>
    <div class="tile"><div class="k">30-day forecast</div><div class="v">${f30 ? rs(f30.price) : "–"}</div>
      <div class="d">${f30 ? `Likely ${rs(f30.low)} – ${rs(f30.high)} (${pc((f30.price / b.price - 1) * 100)})` : ""}
        ${A.forecast_reason ? `<br>🔮 Why: ${esc(A.forecast_reason.biggest)} · <a href="#${C}/timeline">details</a>` : ""}</div></div>
    <div class="tile"><div class="k">Cheapest landed at Srikakulam</div><div class="v">${best ? rs(best.landed) : "–"}</div>
      <div class="d">${best ? `${esc(best.market)}, ${best.km} km · mandi ${rs(best.mandi_price)}` : ""}</div></div>
    <div class="tile"><div class="k">Govt floor (MSP)</div><div class="v">${rs(A.msp.floor)}</div>
      <div class="d">Price is ${pc((b.price / A.msp.floor - 1) * 100)} above · next MSP ${rs(A.msp.next_value)}</div></div>
    <div class="tile"><div class="k">Your Srikakulam selling rate</div><div class="v">${lr ? rs(lr) : "–"}</div>
      <div class="d">${lr && best ? `Margin vs cheapest landed: <b class="${cls(lr - best.landed)}">${rs(lr - best.landed)}</b>/qtl` : `<a href="#wheat/mandis">Enter it</a> to see your margin`}</div></div>
    <div class="tile"><div class="k">Cost of holding stock 30 days</div><div class="v">${pc(A.carrying_cost_30d_pct)}</div>
      <div class="d">Interest + godown + losses (≈ ${rs(b.price * A.carrying_cost_30d_pct / 100)}/qtl)</div></div>
  </div>

  <h2>Price - last 12 months and next 45 days</h2>
  <div class="card"><div id="todayChart"></div><div class="small"><a href="#wheat/timeline">Open the full timeline →</a></div></div>
  <p class="small muted">Generated ${esc(A.generated_at)} · latest mandi day in data ${esc(A.asof)} · all-India feed day ${esc(A.feed_day)}</p>`;
  wireBrief(brief);
  priceChart($("#todayChart"), 365);
}

function renderTodayMetal() {
  const s = A.signal, f30 = A.forecast_points["30"], ind = A.indicators, w = A.world, it = S.items[C];
  const brief = A.briefing.ai || A.briefing.rules;
  const now = nowPrice(C), lv = LIVE[C], gst = A.costs.gst_pct;
  const sinceCall = lv ? (now / A.price - 1) * 100 : null;
  $("#today").innerHTML = `${signalCard(s, brief)}${proofTable(s)}${workedBefore(s)}
  <h2>Key numbers</h2>
  <div class="grid kn">
    <div class="tile"><div class="k">${esc(A.label)} all-India import price now (${esc(A.purity)}, ${esc(unitTxt())}) ${liveNote(C)}</div><div class="v">${rs(now)}</div>
      <div class="d">1 day <span class="${cls(ind.chg_1d)}">${pc(ind.chg_1d)}</span> · 7 days <span class="${cls(ind.chg_7d)}">${pc(ind.chg_7d)}</span> · 30 days <span class="${cls(ind.chg_30d)}">${pc(ind.chg_30d)}</span>
      ${sinceCall != null ? `<br>The call used ${rs(A.price)} (${hm(A.generated_at)}) - <span class="${cls(sinceCall)}">${pc(sinceCall, 2)}</span> since` : ""}</div></div>
    <div class="tile"><div class="k">With ${gst}% GST (what a coin or bar costs)</div><div class="v">${rs(now * (1 + gst / 100))}</div>
      <div class="d">Plus the shop's making charge or premium - jewellery making is not paid back when you sell</div></div>
    <div class="tile"><div class="k">30-day forecast</div><div class="v">${f30 ? rs(f30.price) : "–"}</div>
      <div class="d">${f30 ? `Likely ${rs(f30.low)} – ${rs(f30.high)} (${pc((f30.price / A.price - 1) * 100)})` : ""}
        ${A.forecast_reason ? `<br>🔮 Why: ${esc(A.forecast_reason.biggest)} · <a href="#${C}/timeline">details</a>` : ""}</div></div>
    <div class="tile"><div class="k">World price</div><div class="v">US$${(lv ? lv.usd : w.usd_oz).toLocaleString("en-IN", { maximumFractionDigits: 2 })}<span class="u">/oz</span></div>
      <div class="d">× ₹${w.usdinr.toFixed(2)} per US$ (rupee ${pc(w.fx_chg_30d)} in 30 days) + ${A.costs.duty_pct}% import duty</div></div>
    <div class="tile"><div class="k">Last 12 months</div><div class="v">${Math.round(ind.pctile_52w)}%</div>
      <div class="d">Today is above ${Math.round(ind.pctile_52w)}% of the year's days · range ${rs(ind.low_52w)} – ${rs(ind.high_52w)}${A.ratio_gold_silver ? ` · gold/silver ratio ${A.ratio_gold_silver}` : ""}</div></div>
    <div class="tile"><div class="k">Cost of holding 30 days</div><div class="v">${pc(A.carrying_cost_30d_pct)}</div>
      <div class="d">The bank interest the money would earn (≈ ${rs(A.price * A.carrying_cost_30d_pct / 100)} ${esc(A.unit_short.replace("/", "per "))})</div></div>
  </div>

  <h2>Price - last 12 months and next 45 days</h2>
  <div class="card"><div id="todayChart"></div><div class="small"><a href="#${C}/timeline">Open the full timeline →</a></div></div>
  <p class="small muted">India price = world spot (${esc(w.spot_symbol)}, gold-api.com) × ₹ per US$ ÷ 31.1035 g × ${A.grams} g + ${A.costs.duty_pct}% import duty; history from COMEX ${esc(w.futures_symbol)} closes (Yahoo Finance) lined up with spot (${pc(w.basis_pct, 2)}).
    Your jeweller's rate can differ a little (local premium, purity) - compare with the IBJA rate (ibjarates.com).
    Agent ran ${hm(A.generated_at)} · prices day ${esc(A.asof)}.</p>`;
  wireBrief(brief);
  priceChart($("#todayChart"), 365);
}

function priceChart(el, days) {
  const start = addDays(A.asof, -days);
  const hist = A.series.filter(p => p.date >= start).map(p => ({ x: p.date, y: p.price }));
  const fc = A.forecast.map(p => ({ x: p.date, y: p.price }));
  if (hist.length) fc.unshift(hist[hist.length - 1]);
  const now = isMetal(C) && LIVE[C] ? [{ x: A.asof, y: LIVE[C].rs, color: css(COLOR[C]), label: "Now" }] : [];
  lineChart(el, {
    series: [
      { name: `${A.label} price (actual)`, short: "Actual", label: false, color: css(COLOR[C]), pts: hist },
      { name: "Forecast (shaded = likely range)", short: "Forecast", color: css("--ink-2"), dash: true, pts: fc,
        band: A.forecast.map(p => ({ x: p.date, lo: p.low, hi: p.high })) },
    ],
    refs: A.msp ? [{ y: A.msp.floor, label: "MSP " + rs(A.msp.floor) }] : [],
    dots: now, future: A.asof,
  });
}

/* ------------------------------------------------------------------ TIMELINE: past, present, future */
const RANGES = [["1M", 30], ["3M", 91], ["1Y", 365], ["3Y", 1095], ["All", null]];

function predictionsMap() {
  // target day -> what the agent forecast 30 days before it (replayed days + the latest calls)
  const out = {};
  (A.track_record.rows || []).forEach(r => { if (r.pred30) out[addDays(r.date, 30)] = { pred: r.pred30, made: r.date, price: r.price, actual: r.after30 }; });
  (A.predictions || []).forEach(p => { out[p.target] = { ...(out[p.target] || {}), pred: p.pred30, made: p.date }; });
  return out;
}

/* Why the forecast says what it says: the forecast's move split into its three parts
   (they add up in log terms), plus how far to trust it and what it can't see. */
function reasonCard(A) {
  const r = A.forecast_reason;
  if (!r) return "";
  const hz = ["7", "14", "30"].filter(h => r.horizons[h]);
  const col = (k, h) => { const v = r.horizons[h][k + "_pct"]; return `<td class="num"><span class="${cls(v)}">${pc(v)}</span></td>`; };
  return `<div class="card reason"><h3>🔮 Why the forecast says this · అంచనాకు కారణం</h3>
    <p><b>${esc(r.summary)}</b><br><span class="ink2 small">${esc(r.telugu)}</span></p>
    <div class="tablewrap"><table><tr><th>What moves it</th>${hz.map(h => `<th class="num">${h} days</th>`).join("")}</tr>
      ${r.drivers.map(d => `<tr><td>${esc(d.name)}</td>${hz.map(h => col(d.key, h)).join("")}</tr>`).join("")}
      <tr><td><b>= Expected move</b></td>${hz.map(h => `<td class="num"><b class="${cls(r.horizons[h].total_pct)}">${pc(r.horizons[h].total_pct)}</b></td>`).join("")}</tr>
      <tr><td class="ink2">Likely range (8 in 10)</td>${hz.map(h => `<td class="num ink2">${pc(r.horizons[h].low_pct)} to ${pc(r.horizons[h].high_pct)}</td>`).join("")}</tr></table></div>
    <ul class="why">${r.drivers.map(d => `<li><b>${esc(d.name)}</b> (${pc(d.pct)} at 30 days): ${esc(d.why)}</li>`).join("")}</ul>
    ${r.trust ? `<p class="small">🧪 ${esc(r.trust)}</p>` : ""}
    ${r.in_call ? `<p class="small">⚖️ In today's call, the rule "${esc(r.in_call.rule)}" gives <b>${signed(r.in_call.points)}</b> of ±${r.in_call.max} points${r.in_call.counted != null && r.in_call.counted !== r.in_call.points ? ` - counted as <b>${scoreTxt(r.in_call.counted)}</b> after its weight (×${r.in_call.weight}) and the trend cap` : ""}.</p>` : ""}
    <p class="small muted">🙈 ${esc(r.blind)}</p></div>`;
}

function renderTimeline() {
  const range = store.get("tlRange", "1Y");
  $("#timeline").innerHTML = `
  <h2>${A.emoji} ${esc(A.label)} - past, present and future</h2>
  <p class="ink2 small">Solid line = real prices. Dashed = the agent's forecast for the next 45 days (shaded = likely range, 8 times in 10).
    Dotted = what the agent predicted 30 days before each day, using only what it knew then - where it hugs the real line, the forecasts were good.
    The coloured strip under the chart = the call the agent gave that day.${isMetal(C) ? " The big dot is the live price, refreshed every 5 minutes." : ""}</p>
  <div class="card"><div class="row" id="tlRanges">${RANGES.map(([n]) => `<button data-tl="${n}" class="${n === range ? "primary" : ""}">${n === "All" ? "All years" : n}</button>`).join("")}
    <span class="legend" style="margin:0 0 0 auto">${Object.entries({ buy: "BUY days", hold: "HOLD", wait: "WAIT", sell: "SELL days" }).map(([k, n]) => `<span class="box" style="--c:${CALL_COLOR[k]}">${n}</span>`).join("")}</span></div>
    <div id="tlChart"></div><div id="tlTables"></div></div>
  <div class="grid ppf" id="ppf"></div>
  ${reasonCard(A)}`;
  document.querySelectorAll("[data-tl]").forEach(bt => bt.onclick = () => { store.set("tlRange", bt.dataset.tl); renderTimeline(); });
  drawTimeline(range);
}

function drawTimeline(range) {
  const days = (RANGES.find(r => r[0] === range) || RANGES[2])[1];
  const start = days ? addDays(A.asof, -days) : "0000";
  const src = days && days <= 1100 ? A.series : A.series_weekly || A.series;
  const hist = src.filter(p => p.date >= start && p.price != null).map(p => ({ x: p.date, y: p.price }));
  const fc = A.forecast.map(p => ({ x: p.date, y: p.price }));
  if (hist.length) fc.unshift(hist[hist.length - 1]);
  const pm = predictionsMap();
  let pred = Object.keys(pm).sort().filter(t => t >= (hist[0] || { x: start }).x).map(t => ({ x: t, y: pm[t].pred }));
  if (!days) pred = pred.filter((p, i) => i % 5 === 0 || p.x > A.asof);   // weekly-ish over many years
  const strip = Object.keys(SIG).sort().map(d => ({ x: d, color: CALL_COLOR[callGroup(SIG[d].score, SIG[d].key)] }));
  const color = css(COLOR[C]), now = isMetal(C) ? nowPrice(C) : priceOf(A);
  lineChart($("#tlChart"), {
    height: 340, marker: { x: A.asof, label: "Today" }, future: A.asof, strip,
    series: [
      { name: "Real price", short: "Actual", label: false, color, pts: hist },
      { name: "Predicted 30 days earlier", short: "Predicted", tipName: "Agent predicted (30 days before)", color: css("--s3"), dash: "2 3", width: 1.6, pts: pred, label: false },
      { name: "Forecast (shaded = likely range)", short: "Forecast", color: css("--ink-2"), dash: true, pts: fc,
        band: A.forecast.map(p => ({ x: p.date, lo: p.low, hi: p.high })) },
    ],
    dots: [{ x: A.asof, y: now, color, label: (isMetal(C) && LIVE[C] ? "Live " : "Today ") + rs(now) }],
    tipExtra: x => { const s = SIG[x]; return s ? `<div class="muted">Agent said: <b>${verdictWord(s.score, s.key)}</b> (${scoreTxt(s.score)})</div>` : ""; },
  });

  // Past / present / future, in numbers
  const first = hist[0], last = hist[hist.length - 1];
  const inRange = hist.filter(p => p.x <= A.asof);
  const hiP = inRange.reduce((a, p) => p.y > a.y ? p : a, inRange[0] || {}), loP = inRange.reduce((a, p) => p.y < a.y ? p : a, inRange[0] || {});
  const graded = (A.track_record.rows || []).filter(r => r.pred30 && r.after30 && addDays(r.date, 30) >= (first || {}).x);
  const err = graded.length ? graded.reduce((a, r) => a + Math.abs(r.pred30 / r.after30 - 1), 0) / graded.length * 100 : null;
  const dirOk = graded.filter(r => Math.sign(r.pred30 - r.price) === Math.sign(r.after30 - r.price)).length;
  const bt = A.backtest["30"] || {}, s = A.signal;
  const rangeName = days ? { 30: "last month", 91: "last 3 months", 365: "last 12 months", 1095: "last 3 years" }[days] : `since ${first ? fmtDate(first.x) : ""}`;
  $("#ppf").innerHTML = `
    <div class="tile"><div class="k">⏪ Past - ${rangeName}</div><div class="v">${first && last ? pc((last.y / first.y - 1) * 100) : "–"}</div>
      <div class="d">${first ? `${rs(first.y)} → ${rs(last.y)} · low ${rs(loP.y)} (${fmtDate(loP.x)}) · high ${rs(hiP.y)} (${fmtDate(hiP.x)})` : ""}
      ${err != null ? `<br>Agent's 30-day predictions here: off by <b>${err.toFixed(1)}%</b> on average, direction right <b>${Math.round(dirOk / graded.length * 100)}%</b> (${graded.length} checked)` : ""}</div></div>
    <div class="tile"><div class="k">⏺ Present - ${isMetal(C) && LIVE[C] ? "live " + hm(LIVE[C].updated) : fmtDate(A.asof)}</div><div class="v">${rs(now)}<span class="u">${esc(A.unit_short)}</span></div>
      <div class="d"><span class="pill ${s.key}">${esc(s.label)}</span> score ${scoreTxt(s.score)} of ±${absTxt(s.max_score)} · confidence ${esc(s.confidence)}</div></div>
    <div class="tile"><div class="k">⏩ Future - the agent's forecast</div><div class="v">${A.forecast_points["30"] ? rs(A.forecast_points["30"].price) : "–"} <span class="u">in 30 days</span></div>
      <div class="d">${["7", "14", "30"].filter(h => A.forecast_points[h]).map(h => { const f = A.forecast_points[h]; return `${h} days: <b>${rs(f.price)}</b> (${rs(f.low)} – ${rs(f.high)})`; }).join("<br>")}
      ${bt.mape_pct != null ? `<br>Tested on past dates: off by ${bt.mape_pct}% at 30 days (no-change guess: ${bt.naive_mape_pct}%)` : ""}
      ${A.forecast_reason ? `<br><b>Why:</b> biggest reason ${esc(A.forecast_reason.biggest)} - see below` : ""}</div></div>`;

  const recent = Object.keys(pm).sort().filter(t => t <= A.asof && PX[t]).slice(-30).reverse();
  $("#tlTables").innerHTML =
    tableToggle("tlFc", ["Day", "Forecast", "Likely low", "Likely high"], A.forecast.map(p => [fmtDate(p.date), rs(p.price), rs(p.low), rs(p.high)]), "Forecast day by day (table)") +
    tableToggle("tlPred", ["Day", "Predicted 30 days before", "Real price", "Miss"], recent.map(t => [fmtDate(t), rs(pm[t].pred), rs(PX[t]), `<span class="${cls(PX[t] - pm[t].pred)}">${pc((PX[t] / pm[t].pred - 1) * 100)}</span>`]), "Recent predictions vs what happened (table)");
}

/* ------------------------------------------------------------------ FORECAST */
function renderForecast() {
  const bt = A.backtest, se = A.seasonality, t = A.timing, nowM = new Date(A.asof).getMonth();
  const rows = ["7", "14", "30"].map(h => {
    const r = bt[h], f = A.forecast_points[h];
    return `<tr><td>${h} days</td><td class="num">${f ? rs(f.price) : "–"}</td><td class="num">${f ? rs(f.low) + " – " + rs(f.high) : "–"}</td>
      <td class="num">${r ? r.mape_pct + "%" : "–"}</td><td class="num">${r ? r.naive_mape_pct + "%" : "–"}</td>
      <td class="num">${r && r.direction_hit_pct != null ? r.direction_hit_pct + "%" : "–"}</td><td class="num">${r ? r.tests : 0}</td></tr>`;
  }).join("");
  const metal = isMetal(C);
  $("#forecast").innerHTML = `
  <h2>${A.emoji} ${esc(A.label)} forecast · ధర అంచనా</h2>
  <div class="card"><div class="row" style="margin-bottom:6px">
    ${[90, 365, 1095].map(d => `<button data-range="${d}" class="${d === 365 ? "primary" : ""}">${d === 90 ? "3 months" : d === 365 ? "1 year" : "3 years"}</button>`).join("")}</div>
    <div id="fcChart"></div></div>
  ${reasonCard(A)}
  <h3>How accurate has the forecast been? (proof)</h3>
  <p class="small ink2">We re-ran the forecast on past dates using only the data available then, and compared it with what really happened.
   "Naive" = assuming the price stays the same. If our error is smaller than naive, the forecast is adding value.</p>
  <div class="card tablewrap"><table><tr><th>Ahead</th><th class="num">Forecast</th><th class="num">Likely range (80%)</th>
    <th class="num">Avg error</th><th class="num">Naive error</th><th class="num">Direction right</th><th class="num">Tests</th></tr>${rows}</table></div>
  <h3>Seasonal pattern - when ${esc(A.label.toLowerCase())} is usually cheap or dear</h3>
  <p class="small ink2">Each bar = how far that month's price usually sits from the yearly average${metal ? " (after removing the long up/down trend)" : ""}.
    Built from ${se.years_used} full years of ${metal ? "prices" : "mandi data"} (${Math.round(se.weight_on_data * 100)}% weight) blended with ${metal ? "no seasonal effect (metals have no harvest, so the pattern must earn its place)" : "the typical Indian pattern"}.</p>
  <div class="card"><div id="seasonChart"></div>
    ${tableToggle("seasonTbl", ["Month", "vs year average"], se.months.map((mo, i) => [mo, pc((se.index[i] - 1) * 100)]))}</div>
  <div class="grid">
    <div class="tile"><div class="k">Usually cheapest (buy) months</div><div class="v">${t.cheapest_months.join(", ")}</div><div class="d">Next window starts ${fmtDate(t.next_buy_window)} (${t.days_to_buy_window} days)</div></div>
    <div class="tile"><div class="k">Usually dearest (sell) months</div><div class="v">${t.dearest_months.join(", ")}</div><div class="d">Typical swing low → high: ${t.seasonal_swing_pct}%</div></div>
    <div class="tile"><div class="k">Weekday effect (small)</div><div class="v small" style="font-size:15px">${t.weekday.length ? t.weekday.map(w => `${w.day} ${pc(w.avg_dev_pct, 2)}`).join(" · ") : "–"}</div><div class="d">Price vs its 2-week average, by day of week</div></div>
  </div>
  <p class="small muted">How the forecast works: today's price with the seasonal effect removed, plus the recent 30-day trend (slowly fading out), then the seasonal pattern added back. Ranges come from the real errors in the test above.</p>`;
  document.querySelectorAll("[data-range]").forEach(bt => bt.onclick = () => {
    document.querySelectorAll("[data-range]").forEach(x => x.classList.toggle("primary", x === bt));
    priceChart($("#fcChart"), +bt.dataset.range);
  });
  priceChart($("#fcChart"), 365);
  barChart($("#seasonChart"), {
    items: se.months.map((mo, i) => ({ label: mo, value: (se.index[i] - 1) * 100, tip: `<b>${mo}</b>: ${pc((se.index[i] - 1) * 100)} vs yearly average` })),
    fmt: v => (v > 0 ? "+" : "") + v.toFixed(1) + "%", colorPos: "#e34948", colorNeg: css("--s1"), highlight: nowM,
  });
}

/* ------------------------------------------------------------------ PRE-TRADE */
function renderPre() { (C === "wheat" ? renderPreWheat : renderPreMetal)(); }

function renderPreWheat() {
  const lt = A.landed, cfg = A.config, b = A.benchmark;
  const opts = lt.map((r, i) => `<option value="${i}">${esc(r.market)} (${esc(r.state)}) - ${rs(r.mandi_price)}, ${r.km} km</option>`).join("") + `<option value="custom">Other / custom</option>`;
  $("#pre").innerHTML = `
  <h2>Before you trade - pre-analysis</h2>
  <p class="ink2 small">Enter a planned purchase. The agent works out your all-in cost at Srikakulam, the price you must sell at to break even, and what the forecast says you are likely to make.</p>
  <div class="card"><form class="row" id="preForm" onsubmit="return false">
    <label>Buy from<select name="src">${opts}</select></label>
    <label>Mandi price ₹/qtl<input type="number" name="price" step="5"></label>
    <label>Quantity (qtl)<input type="number" name="qty" value="100" step="10"></label>
    <label>Freight ₹/qtl<input type="number" name="freight" step="5"></label>
    <label>Hold for (days)<input type="number" name="days" value="30" min="0" max="45"></label>
    <label>Planned sell ₹/qtl (optional)<input type="number" name="sell" step="5" placeholder="auto"></label>
  </form></div>
  <div id="preOut"></div>`;
  const f = $("#preForm");
  const fill = () => {
    const r = lt[+f.src.value];
    if (r) { f.price.value = r.mandi_price; f.freight.value = r.freight; }
  };
  f.src.onchange = () => { fill(); calc(); };
  f.oninput = calc; fill(); calc();
  function calc() {
    const c = cfg.costs, cr = cfg.carrying;
    const price = +f.price.value || 0, qty = +f.qty.value || 0, freight = +f.freight.value || 0, days = Math.min(45, Math.max(0, +f.days.value || 0));
    const fee = price * c.source_mandi_fee_pct / 100, extras = c.handling_per_qtl + c.bags_per_qtl + c.brokerage_per_qtl;
    const landed = price + fee + freight + extras;
    const months = days / 30, carry = landed * (cr.interest_pct_per_month + cr.loss_pct_per_month) / 100 * months + cr.storage_per_qtl_per_month * months;
    const breakeven = landed + carry;
    const fc = (days && forecastAt(days)) || { price: b.price, low: b.price, high: b.price };
    const lr = localRate();
    const scen = [["Pessimistic (low end)", fc.low], ["Most likely", fc.price], ["Optimistic (high end)", fc.high]].map(([n, p]) => {
      const sell = +f.sell.value || (lr ? lr * p / b.price : landed * p / b.price);
      return { n, sell, pl: (sell - breakeven) * qty, per: sell - breakeven };
    });
    const s = A.signal, edge = (fc.price / b.price - 1) * 100 - (carry / landed * 100);
    const checks = [
      [callGroup(s.score, s.key) === "buy", `Agent signal is ${s.label} (score ${scoreTxt(s.score)})`, "Agent signal supports buying", "Agent signal does not support buying now"],
      [edge > 0, `Forecast move ${pc((fc.price / b.price - 1) * 100)} vs holding cost ${pc(carry / landed * 100)} over ${days} days`, "Expected rise beats holding cost", "Expected rise does NOT beat holding cost"],
      [lt.length ? landed <= lt[0].landed * 1.02 : null, `This source lands at ${rs(landed)} vs cheapest ${rs(lt.length ? lt[0].landed : landed)}`, "Among the cheapest sources", "A cheaper source exists"],
      [b.price <= A.msp.floor * 1.08, `Benchmark ${rs(b.price)} vs MSP ${rs(A.msp.floor)}`, "Close to the MSP floor (limited downside)", "Well above MSP (more downside if prices fall)"],
      [lr ? lr > landed : null, lr ? `Your selling rate ${rs(lr)} vs landed ${rs(landed)}` : "Enter your Srikakulam rate in the Mandis tab", "Immediate resale margin is positive", "No margin at today's local rate"],
    ];
    $("#preOut").innerHTML = `
    <div class="grid">
      <div class="tile"><div class="k">Landed cost at Srikakulam</div><div class="v">${rs(landed)}</div><div class="d">mandi ${rs(price)} + fee ${rs(fee)} + freight ${rs(freight)} + handling/bags/brokerage ${rs(extras)}</div></div>
      <div class="tile"><div class="k">Total money needed</div><div class="v">${rs(landed * qty)}</div><div class="d">${qty} qtl (${(qty / 10).toFixed(1)} tonnes)</div></div>
      <div class="tile"><div class="k">Holding cost for ${days} days</div><div class="v">${rs(carry)}/qtl</div><div class="d">${rs(carry * qty)} in total</div></div>
      <div class="tile"><div class="k">Break-even sell price</div><div class="v">${rs(breakeven)}</div><div class="d">Sell above this to make money</div></div>
    </div>
    ${scenarioTable(days, scen, +f.sell.value ? "Using your planned sell price." : lr ? "Sell price = your Srikakulam rate moved in line with the forecast." : "Sell price = today's landed cost moved in line with the forecast (enter your local rate for a better estimate).", "Profit per qtl")}
    ${checklist(checks)}`;
  }
}

function renderPreMetal() {
  const c = A.costs, p0 = Math.round(nowPrice(C)), ind = A.indicators;
  $("#pre").innerHTML = `
  <h2>Before you buy ${esc(A.label.toLowerCase())} - pre-analysis</h2>
  <p class="ink2 small">Enter a planned purchase. The agent works out what it really costs (GST and making charge included), the bank interest you give up while you hold it, the market rate you need when you sell to break even, and what the forecast says.</p>
  <div class="card"><form class="row" id="preForm" onsubmit="return false">
    <label>Quantity (grams)<input type="number" name="qty" value="${C === "silver" ? 1000 : 10}" step="1" min="0"></label>
    <label>Rate ${esc(unitTxt())}<input type="number" name="rate" value="${p0}" step="1"></label>
    <label>Making charge / premium %<input type="number" name="mk" value="0" step="0.5" min="0" title="Coins and bars: about 1-3%. Jewellery: often 8-20%."></label>
    <label>GST %<input type="number" name="gst" value="${c.gst_pct}" step="0.5" min="0"></label>
    <label>Hold for (days)<input type="number" name="days" value="30" min="0" max="45"></label>
    <label>Buy-back cut when selling %<input type="number" name="disc" value="${c.sell_discount_pct}" step="0.5" min="0"></label>
    <label>Planned sell rate (optional)<input type="number" name="sell" step="1" placeholder="auto"></label>
  </form><p class="small muted">The rate starts at today's ${LIVE[C] ? "live " : ""}price. Coins and bars usually carry a 1–3% premium; jewellery making charges (often 8–20%) and GST are not paid back when you sell.</p></div>
  <div id="preOut"></div>`;
  const f = $("#preForm");
  f.oninput = calc; calc();
  function calc() {
    const qty = +f.qty.value || 0, rate = +f.rate.value || 0, mk = +f.mk.value || 0, g = +f.gst.value || 0, disc = +f.disc.value || 0;
    const days = Math.min(45, Math.max(0, +f.days.value || 0)), u = qty / A.grams;
    const base = u * rate, making = base * mk / 100, gst = (base + making) * g / 100, total = base + making + gst;
    const interest = total * c.interest_pct_per_month / 100 * days / 30;
    const breakeven = u ? (total + interest) / u / (1 - disc / 100) : 0;
    const fc = (days && forecastAt(days)) || { price: A.price, low: A.price, high: A.price };
    const scen = [["Pessimistic (low end)", fc.low], ["Most likely", fc.price], ["Optimistic (high end)", fc.high]].map(([n, p]) => {
      const sell = +f.sell.value || rate * p / A.price;
      const pl = u * sell * (1 - disc / 100) - total - interest;
      return { n, sell, pl, per: u ? pl / u : 0 };
    });
    const s = A.signal, move = (fc.price / A.price - 1) * 100, intPct = c.interest_pct_per_month * days / 30;
    const checks = [
      [callGroup(s.score, s.key) === "buy", `Agent signal is ${s.label} (score ${scoreTxt(s.score)})`, "Agent signal supports buying", "Agent signal does not support buying now"],
      [days ? move - intPct > 0 : null, `Forecast move ${pc(move)} vs bank interest ${pc(intPct)} over ${days} days`, "Expected rise beats bank interest", "Expected rise does NOT beat bank interest"],
      [ind.pctile_52w <= 50, `Today is above ${Math.round(ind.pctile_52w)}% of the last 12 months' prices`, "In the cheaper half of the year's range", "In the dearer half of the year's range"],
      [mk + g <= 6, `Making/premium ${mk}% + GST ${g}% = ${(mk + g).toFixed(1)}% lost on day one`, "Low entry cost (coin / bar level)", "High entry cost - the price must rise a lot just to break even"],
      [rate <= p0 * 1.01, `Your rate ${rs(rate)} vs today's ${rs(p0)}`, "Your rate is in line with the market", "Your rate is more than 1% above the market - ask for a better price"],
    ];
    $("#preOut").innerHTML = `
    <div class="grid">
      <div class="tile"><div class="k">Total you pay</div><div class="v">${rs(total)}</div><div class="d">metal ${rs(base)} + making ${rs(making)} + GST ${rs(gst)} · ${qty} g</div></div>
      <div class="tile"><div class="k">Bank interest given up (${days} days)</div><div class="v">${rs(interest)}</div><div class="d">${c.interest_pct_per_month}% a month - change it in config.json</div></div>
      <div class="tile"><div class="k">Break-even market rate</div><div class="v">${rs(breakeven)}</div><div class="d">${esc(unitTxt())}, after the ${disc}% buy-back cut - ${pc((breakeven / p0 - 1) * 100)} vs today</div></div>
      <div class="tile"><div class="k">Today's market rate</div><div class="v">${rs(p0)}</div><div class="d">${esc(unitTxt())} ${liveNote(C)}</div></div>
    </div>
    ${scenarioTable(days, scen, +f.sell.value ? "Using your planned sell rate." : "Sell rate = your buying rate moved in line with the forecast, less the buy-back cut.", "Profit per " + A.unit_short.replace("/", ""))}
    ${checklist(checks)}`;
  }
}

function scenarioTable(days, scen, note, perName) {
  return `<div class="card tablewrap"><h3 style="margin-top:0">If you sell after ${days} days</h3><table>
      <tr><th>Scenario</th><th class="num">Sell price</th><th class="num">${perName}</th><th class="num">Total profit</th></tr>
      ${scen.map(x => `<tr><td>${x.n}</td><td class="num">${rs(x.sell)}</td><td class="num ${cls(x.per)}">${rs(x.per)}</td><td class="num ${cls(x.pl)}"><b>${rs(x.pl)}</b></td></tr>`).join("")}
    </table><p class="small muted">${note}</p></div>`;
}
function checklist(checks) {
  const good = checks.filter(x => x[0] === true).length, total = checks.filter(x => x[0] !== null).length;
  return `<div class="card"><h3 style="margin-top:0">Checklist - ${good} of ${total} in your favour</h3>
      ${checks.map(([ok, detail, yes, no]) => `<div style="margin:6px 0"><span class="status ${ok === null ? "" : ok ? "good" : "critical"}">${ok === null ? "Unknown" : ok ? "Yes" : "No"}</span>
        <b>${ok === null ? "Not enough data" : ok ? yes : no}</b><div class="why">${esc(detail)}</div></div>`).join("")}
      <p><b>${good >= total - 1 && total >= 3 ? "✅ Looks like a good trade on today's numbers." : good >= Math.ceil(total / 2) ? "⚠️ Mixed - consider buying a smaller amount, or wait." : "❌ The numbers are against this trade today."}</b></p></div>`;
}

/* ------------------------------------------------------------------ MY TRADES (post-analysis) */
const tkey = () => C === "wheat" ? "trades" : "trades." + C;
const trades = () => store.get(tkey(), []);
// Same-day buys go before sells so a sale can match stock bought that morning.
const tradeOrder = (a, b) => a.date.localeCompare(b.date) || (a.type === b.type ? 0 : a.type === "buy" ? -1 : 1);
function saveTrades(t) { store.set(tkey(), t.sort(tradeOrder)); }
const units = q => C === "wheat" ? q : q / A.grams;   // quantity -> the units the price is quoted in
function holdCfg() {
  if (C === "wheat") { const cr = A.config.carrying; return { pct: cr.interest_pct_per_month + cr.loss_pct_per_month, fixed: cr.storage_per_qtl_per_month }; }
  return { pct: A.costs.interest_pct_per_month, fixed: 0 };
}

function timingScore(t) {
  // Where did this price sit among prices 30 days either side? Buys: lower = better.
  const win = [];
  for (let k = -30; k <= 30; k++) { const p = PX[addDays(t.date, k)]; if (p) win.push(p); }
  const p0 = PX[t.date] || PX[addDays(t.date, -1)] || PX[addDays(t.date, -2)] || PX[addDays(t.date, -3)];
  if (!p0 || win.length < 10) return null;
  const below = win.filter(p => p < p0).length / win.length * 100;
  return { score: Math.round(t.type === "buy" ? 100 - below : below), complete: dayDiff(t.date, A.asof) >= 30, bench: p0 };
}

function fifo(list) {
  const lots = [], sells = [], hc = holdCfg();
  for (const t of [...list].sort(tradeOrder)) {
    if (t.type === "buy") { lots.push({ ...t, left: +t.qty }); continue; }
    let q = +t.qty, cost = 0, carry = 0, matched = 0;
    while (q > 0 && lots.length) {
      const l = lots[0], take = Math.min(q, l.left), days = Math.max(0, dayDiff(l.date, t.date));
      cost += units(take) * l.price; matched += take;
      carry += units(take) * (l.price * hc.pct / 100 + hc.fixed) * days / 30;
      l.left -= take; q -= take; if (l.left <= 1e-9) lots.shift();
    }
    const gross = units(matched) * t.price - cost;
    sells.push({ ...t, matched, unmatched: q, avgCost: matched ? cost / units(matched) : 0, gross, carry, net: gross - carry });
  }
  return { lots, sells };
}

function renderTrades() {
  const wheat = C === "wheat", qu = qtyUnit(), pu = wheat ? "₹/qtl" : "₹" + A.unit_short;
  const list = trades(), { lots, sells } = fifo(list), lr = localRate();
  const stock = lots.reduce((s, l) => s + l.left, 0), stockCost = lots.reduce((s, l) => s + units(l.left) * l.price, 0);
  const mark = wheat ? lr || (A.best_source ? A.best_source.landed : null) : nowPrice(C) * (1 - A.costs.sell_discount_pct / 100);
  const realised = sells.reduce((s, x) => s + x.net, 0);
  const ts = list.map(timingScore).filter(Boolean);
  const avgTiming = ts.length ? ts.reduce((s, x) => s + x.score, 0) / ts.length : null;
  let agree = 0, judged = 0;
  const rows = list.map(t => {
    const tsc = timingScore(t), sg = SIG[t.date], sig = sg && sg.score;
    let ag = "–";
    if (sig != null) {
      judged++;
      const g = callGroup(sig, sg.key);
      const ok = t.type === "buy" ? g !== "sell" : g === "sell" || g === "wait";   // HOLD = keep it, so selling went against it
      if (ok) agree++;
      ag = `<span class="status ${ok ? "good" : "serious"}">${verdictWord(sig, sg.key)} (${scoreTxt(sig)})</span>`;
    }
    const s = sells.find(x => x.id === t.id);
    return `<tr><td>${fmtDate(t.date)}</td><td>${t.type === "buy" ? "Buy" : "Sell"}</td><td class="num">${t.qty}</td><td class="num">${rs(t.price)}</td>
      <td>${esc(t.place || "")}</td><td class="num">${tsc ? `${tsc.score}/100${tsc.complete ? "" : "*"}` : "–"}</td><td>${ag}</td>
      <td class="num ${s ? cls(s.net) : ""}">${s ? rs(s.net) : ""}${s && s.unmatched > 0 ? `<div class="small warnText">${s.unmatched} ${qu} sold with no recorded purchase - not in P&L</div>` : ""}</td><td class="small">${esc(t.notes || "")}</td>
      <td><button data-del="${t.id}" title="Delete">✕</button></td></tr>`;
  }).join("");
  const hc = holdCfg();
  $("#trades").innerHTML = `
  <h2>My ${esc(A.label.toLowerCase())} trades - post-analysis</h2>
  <p class="ink2 small">Record each purchase and sale. Stored only in this browser - export a CSV to back up or move to another phone.
    ${wheat ? "Buy price = your all-in cost per quintal at Srikakulam." : `Quantity in grams; price ${esc(unitTxt())} - what you actually paid or were paid (put making charges and GST into the buy price).`}</p>
  <div class="card"><form class="row" id="tradeForm">
    <label>Date<input type="date" name="date" required value="${A.asof}"></label>
    <label>Type<select name="type"><option value="buy">Buy</option><option value="sell">Sell</option></select></label>
    <label>Quantity (${wheat ? "qtl" : "grams"})<input type="number" name="qty" required step="${wheat ? "0.1" : "0.01"}" min="0"></label>
    <label>Price ${pu}<input type="number" name="price" required step="1" min="0"></label>
    <label>From / to<input name="place" placeholder="${wheat ? "e.g. Katni / local mill" : "e.g. jeweller / bank"}"></label>
    <label style="flex:1;min-width:160px">Notes<input name="notes"></label>
    <button class="primary">Add</button>
  </form>
  <div class="row" style="margin-top:10px"><button id="exp">Export CSV</button><label class="btn" style="flex-direction:row">Import CSV<input type="file" id="imp" accept=".csv" hidden></label></div></div>
  <div class="grid">
    <div class="tile"><div class="k">Realised profit (after holding cost)</div><div class="v ${cls(realised)}">${rs(realised)}</div><div class="d">${sells.length} sales matched first-in-first-out</div></div>
    <div class="tile"><div class="k">${wheat ? "Stock on hand" : "Holding now"}</div><div class="v">${stock.toFixed(wheat ? 1 : 2)} ${qu}</div><div class="d">Avg cost ${stock ? rs(stockCost / units(stock)) : "–"}${wheat ? "" : A.unit_short}</div></div>
    <div class="tile"><div class="k">Unrealised profit</div><div class="v ${cls(stock && mark ? units(stock) * mark - stockCost : 0)}">${stock && mark ? rs(units(stock) * mark - stockCost) : "–"}</div><div class="d">${wheat ? (lr ? "at your Srikakulam rate" : "at today's cheapest landed cost") : `at today's price less the ${A.costs.sell_discount_pct}% buy-back cut`} ${mark ? rs(mark) : ""}</div></div>
    <div class="tile"><div class="k">Your timing score</div><div class="v">${avgTiming != null ? Math.round(avgTiming) + "/100" : "–"}</div><div class="d">100 = bought at the lowest / sold at the highest price of the surrounding 2 months</div></div>
    <div class="tile"><div class="k">Followed the agent</div><div class="v">${judged ? Math.round(agree / judged * 100) + "%" : "–"}</div><div class="d">${judged} trades on days with a signal</div></div>
  </div>
  <div class="card tablewrap"><table><tr><th>Date</th><th>Type</th><th class="num">Qty (${qu})</th><th class="num">${pu}</th><th>From/to</th>
    <th class="num">Timing</th><th>Agent said that day</th><th class="num">Net P&L</th><th>Notes</th><th></th></tr>${rows || '<tr><td colspan="10" class="muted">No trades yet.</td></tr>'}</table>
    <p class="small muted">* timing score still settling (less than 30 days of prices after the trade). Holding cost uses your settings: ${wheat
      ? `${A.config.carrying.interest_pct_per_month}%/month interest, ₹${A.config.carrying.storage_per_qtl_per_month}/qtl/month godown, ${A.config.carrying.loss_pct_per_month}%/month losses`
      : `${hc.pct}%/month bank interest`}.</p></div>
  ${sells.length ? `<h3>Lessons from your sales</h3><div class="card">${lessons(sells, list)}</div>` : ""}`;
  $("#tradeForm").onsubmit = e => {
    e.preventDefault();
    const fd = Object.fromEntries(new FormData(e.target));
    const t = trades(); t.push({ id: Date.now().toString(36), ...fd, qty: +fd.qty, price: +fd.price }); saveTrades(t); renderTrades();
  };
  document.querySelectorAll("[data-del]").forEach(b => b.onclick = () => { if (confirm("Delete this trade?")) { saveTrades(trades().filter(t => t.id !== b.dataset.del)); renderTrades(); } });
  $("#exp").onclick = () => {
    const h = ["date", "type", "qty", "price", "place", "notes"];
    const csv = [h.join(",")].concat(trades().map(t => h.map(k => `"${String(t[k] ?? "").replace(/"/g, '""')}"`).join(","))).join("\n");
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); a.download = `dharalu-${C}-trades.csv`; a.click();
  };
  $("#imp").onchange = async e => {
    const text = await e.target.files[0].text(), lines = text.trim().split(/\r?\n/), h = lines.shift().split(",").map(s => s.replace(/"/g, "").trim());
    const parse = l => { const out = []; let cur = "", q = false; for (const ch of l) { if (ch === '"') q = !q; else if (ch === "," && !q) { out.push(cur); cur = ""; } else cur += ch; } out.push(cur); return out; };
    const add = lines.map((l, i) => { const v = parse(l), o = {}; h.forEach((k, j) => o[k] = v[j]); return { id: Date.now().toString(36) + i, ...o, qty: +o.qty, price: +o.price }; }).filter(t => t.date && t.qty);
    saveTrades(trades().concat(add)); renderTrades();
  };
}

function lessons(sells, list) {
  const out = [];
  const held = sells.map(s => { const buys = list.filter(t => t.type === "buy" && t.date <= s.date); const last = buys[buys.length - 1]; return last ? dayDiff(last.date, s.date) : null; }).filter(x => x != null);
  const carryShare = sells.reduce((a, s) => a + s.carry, 0), gross = sells.reduce((a, s) => a + s.gross, 0);
  if (gross > 0) out.push(`Holding costs ate <b>${Math.round(carryShare / gross * 100)}%</b> of your gross profit (${rs(carryShare)} of ${rs(gross)}).`);
  const losers = sells.filter(s => s.net < 0);
  if (losers.length) out.push(`<b>${losers.length}</b> of ${sells.length} sales lost money after holding costs - check whether those buys were made on SELL/WAIT days.`);
  if (held.length) out.push(`Average holding period about <b>${Math.round(held.reduce((a, b) => a + b, 0) / held.length)}</b> days.`);
  const sellTiming = sells.map(timingScore).filter(Boolean);
  if (sellTiming.length) out.push(`Your sales were made at a timing score of <b>${Math.round(sellTiming.reduce((a, s) => a + s.score, 0) / sellTiming.length)}</b>/100 (higher = closer to the local peak).`);
  return out.map(x => `<div style="margin:5px 0">• ${x}</div>`).join("") || '<span class="muted">Add more trades to see patterns.</span>';
}

/* ------------------------------------------------------------------ TRACK RECORD */
function compareTable(tr) {
  const cm = tr.compare, rules = tr.rules;
  if (!cm) return "";
  const nm = { buy: "BUY / STRONG BUY", hold: "HOLD", wait: "WAIT", sell: "SELL / STRONG SELL" };
  const cell = x => x && x.days ? `<td class="num">${x.days}</td><td class="num">${x.right_pct}%</td><td class="num pts ${cls(x.edge_pts)}">${signed(x.edge_pts)}</td>` : `<td class="num muted" colspan="3">no days</td>`;
  const rows = ["buy", "hold", "wait", "sell"].map(k => { const w = cm.weighted[k] || {}, e = cm.equal[k] || {}, ref = w.days ? w : e;
    return `<tr><td><b>${nm[k]}</b><div class="why">right = ${esc(ref.what || "")} 30 days later; any day: ${ref.base_pct ?? "–"}%</div></td>${cell(w)}${cell(e)}</tr>`; }).join("");
  const ev = Object.fromEntries((A.signal.evidence || []).map(e => [e.rule, e]));
  const rr = rules ? Object.entries(rules).map(([r, x]) => { const e = ev[r] || {};
    return `<tr><td><b>${esc(r)}</b></td><td class="num">${x.votes}</td><td class="num">${x.up} / ${x.down}</td><td class="num">${x.votes ? x.right_pct + "%" : "–"}</td><td class="num">${x.votes ? x.usual_pct + "%" : "–"}</td>
      <td class="num pts ${cls(x.edge_pts)}">${x.votes ? signed(x.edge_pts) : "–"}</td><td class="num">${e.weight != null ? "×" + e.weight : "–"}</td></tr>`; }).join("") : "";
  return `<h3>Learned weights vs every rule counting the same</h3>
  <p class="ink2 small">The same replay, done twice. <b>Weighted</b> (what Dharalu uses since 2.2): each day uses rule weights learned only from days whose result was already known.
    <b>Equal</b>: every rule counts the same (how it worked before 2.2). <b>Edge</b> = how many points more often the call was right than for any day - above 0 means the call adds something.</p>
  <div class="card tablewrap"><table><tr><th rowspan="2">Call</th><th colspan="3" class="c">Weighted (now)</th><th colspan="3" class="c">Equal (before 2.2)</th></tr>
    <tr><th class="num">Days</th><th class="num">Right</th><th class="num">Edge</th><th class="num">Days</th><th class="num">Right</th><th class="num">Edge</th></tr>${rows}</table></div>
  ${rr ? `<h3>Each rule's own record</h3>
  <p class="ink2 small">Every past day a rule said "up" or "down", graded on the price 30 days later (${tr.graded_days || "all"} graded days). Today's weight comes from this record: fewer than 60 votes = ×1 (too few to judge), edge 10+ with 120+ votes = ×2, 3+ = ×1, 0 to 3 = ×½, below 0 = ×0 (ignored).</p>
  <div class="card tablewrap"><table><tr><th>Rule</th><th class="num">Votes</th><th class="num">Up / down</th><th class="num">Right</th><th class="num">Usual</th><th class="num">Edge</th><th class="num">Weight today</th></tr>${rr}</table></div>` : ""}`;
}
function renderRecord() {
  const tr = A.track_record, s = tr.summary, live = tr.live || {};
  const cost = C === "wheat" ? "holding cost" : "bank interest";
  const g = (n, x) => x ? `<tr><td><b>${n}</b></td><td class="num">${x.days}</td><td class="num ${cls(x.avg_move_pct)}">${pc(x.avg_move_pct, 2)}</td><td class="num">${x.rose_pct}%</td><td class="num">${x.beat_holding_cost_pct}%</td></tr>` : "";
  const rec = x => `${g("BUY / STRONG BUY", x.buy_days)}${g("HOLD", x.hold_days)}${g("WAIT", x.wait_days)}${g("SELL / STRONG SELL", x.sell_days)}${g("All days (baseline)", x.all_days)}`;
  const head = `<tr><th>When the agent said</th><th class="num">Days</th><th class="num">Avg price move next 30 days</th><th class="num">Price rose</th><th class="num">Rise beat ${cost}</th></tr>`;
  $("#record").innerHTML = `
  <h2>${A.emoji} ${esc(A.label)} - agent track record: proof that the signal works (or doesn't)</h2>
  <p class="ink2 small">For every ${C === "wheat" ? "day" : "trading day"} in the last year we re-ran the same rules using only data available on that day, then checked the price 30 days later.
   A good BUY should be followed by rises, a good HOLD by rises that beat the ${cost}, and a good SELL by falls. Each day only sees the data known on that day (the seasonal pattern too), so this is a fair test - the live record below is graded on real calls.
   The rule weights are learned the same way: each day only uses past days whose 30-day result was already known.</p>
  <div class="card tablewrap"><table>${head}${rec(s)}</table></div>
  ${tr.summary_all ? `<h3>Whole history - since ${fmtDate(tr.since)}</h3>
  <p class="ink2 small">The same replay over every day we have data for. More days = stronger proof, but older years were a different market.</p>
  <div class="card tablewrap"><table>${head}${rec(tr.summary_all)}</table></div>` : ""}
  ${compareTable(tr)}
  <div class="card"><div id="recChart"></div></div>
  <h3>Live calls (graded 30 days later)</h3>
  <div class="card tablewrap">${live.graded ? `<p>Right <b>${live.right_pct}%</b> of ${live.graded} graded calls.</p>` : ""}
    <table><tr><th>Date</th><th>Call</th><th class="num">Price then</th><th class="num">30 days later</th><th class="num">Move</th><th>Right?</th></tr>
    ${(live.rows || []).slice().reverse().map(r => `<tr><td>${fmtDate(r.date)}</td><td>${verdictWord(+r.score, r.signal)} (${scoreTxt(r.score)})</td><td class="num">${rs(+r.price)}</td><td class="num">${rs(r.after30)}</td><td class="num ${cls(r.move_pct)}">${pc(r.move_pct)}</td><td>${r.right ? '<span class="status good">Yes</span>' : '<span class="status critical">No</span>'}</td></tr>`).join("")}
    ${!(live.rows || []).length && !(live.pending || []).length ? '<tr><td colspan="6" class="muted">No live calls yet - one is logged every prices day.</td></tr>' : ""}
    ${(live.pending || []).slice().reverse().slice(0, 10).map(r => `<tr><td>${fmtDate(r.date)}</td><td>${verdictWord(+r.score, r.signal)} (${scoreTxt(r.score)})</td><td class="num">${rs(+r.price)}</td><td colspan="3" class="muted">waiting - graded on ${fmtDate(addDays(r.date, 30))}</td></tr>`).join("")}
    </table></div>`;
  const cut = addDays(A.asof, -400);
  const rows = (tr.rows || []).filter(r => r.date >= cut);
  lineChart($("#recChart"), {
    height: 270,
    series: [{ name: `${A.label} price`, short: "Price", color: css(COLOR[C]), pts: rows.map(r => ({ x: r.date, y: r.price })) },
      { name: "Price 30 days later", short: "+30d", color: css("--ink-2"), dash: true, pts: rows.map(r => ({ x: r.date, y: r.after30 })) }],
    strip: rows.map(r => ({ x: r.date, color: CALL_COLOR[callGroup(r.score, r.signal)] })),
    tipExtra: x => { const r = rows.find(z => z.date === x); return r ? `<div class="muted">Agent said: <b>${verdictWord(r.score, r.signal)}</b> (${scoreTxt(r.score)})</div>` : ""; },
  });
  $("#recChart .legend").insertAdjacentHTML("beforeend", Object.entries({ buy: "BUY days", hold: "HOLD", wait: "WAIT", sell: "SELL days" }).map(([k, n]) => `<span class="box" style="--c:${CALL_COLOR[k]}">${n}</span>`).join(""));
}

/* ------------------------------------------------------------------ MANDIS (wheat) */
function renderMandis() {
  const lt = A.landed, lr = localRate(), cfg = A.config;
  $("#mandis").innerHTML = `
  <h2>Mandis & landed cost at Srikakulam</h2>
  <div class="card"><form class="row" onsubmit="return false">
    <label>Your Srikakulam selling rate ₹/qtl<input type="number" id="lr" value="${lr ?? ""}" step="5" placeholder="e.g. 3200"></label>
    <span class="small ink2" style="align-self:center">Saved in this browser. Used for margins, pre-trade and unrealised profit.</span></form></div>
  <p class="small ink2">Landed = mandi price + mandi fee (${cfg.costs.source_mandi_fee_pct}%) + freight (₹${cfg.freight.rate_per_qtl_per_km}/qtl/km) + handling ₹${cfg.costs.handling_per_qtl} + bags ₹${cfg.costs.bags_per_qtl} + brokerage ₹${cfg.costs.brokerage_per_qtl}. Change these in <code>config.json</code> to match your real costs.</p>
  <div class="card tablewrap"><table><tr><th>Mandi</th><th>State</th><th class="num">km</th><th class="num">Mandi price</th><th class="num">Fee</th><th class="num">Freight</th><th class="num">Other</th><th class="num">Landed</th><th class="num">${lr ? "Your margin" : ""}</th><th>Price date</th></tr>
    ${lt.map(r => `<tr data-mk="${esc(r.market)}" style="cursor:pointer"><td><b>${esc(r.market)}</b></td><td>${esc(r.state)}</td><td class="num">${r.km}</td><td class="num">${rs(r.mandi_price)}</td><td class="num">${rs(r.fee)}</td><td class="num">${rs(r.freight)}</td><td class="num">${rs(r.extras)}</td><td class="num"><b>${rs(r.landed)}</b></td><td class="num ${lr ? cls(lr - r.landed) : ""}">${lr ? rs(lr - r.landed) : ""}</td><td class="small">${fmtDate(r.date)}</td></tr>`).join("")}
  </table><p class="small muted">Click a mandi to see its last 6 months.</p></div>
  <div class="card"><h3 style="margin-top:0" id="mkTitle"></h3><div id="mkChart"></div></div>
  <h3>All-India today (${A.feed_day ? fmtDate(A.feed_day) : ""})</h3>
  <p class="small ink2">"Source" states grow wheat (where you buy). "Selling" states are deficit markets like yours - their prices are a reference for what wheat fetches in the south and east.
   Median selling-state price: <b>${rs(A.selling_reference)}</b>${A.margin_vs_selling_ref != null ? ` → gap vs cheapest landed: <b class="${cls(A.margin_vs_selling_ref)}">${rs(A.margin_vs_selling_ref)}</b>/qtl` : ""}.</p>
  <div class="card tablewrap"><table><tr><th>State</th><th>Role</th><th class="num">Mandis</th><th class="num">Median</th><th class="num">Low – high</th><th class="num">Landed at Srikakulam (approx.)</th></tr>
    ${A.states.map(s => `<tr><td>${esc(s.state)}</td><td><span class="chip">${s.role}</span></td><td class="num">${s.mandis}</td><td class="num">${rs(s.median)}</td><td class="num">${rs(s.low)} – ${rs(s.high)}</td><td class="num">${s.landed ? rs(s.landed) : ""}</td></tr>`).join("")}
  </table></div>`;
  $("#lr").oninput = e => { store.set("localRate", e.target.value ? +e.target.value : null); };
  $("#lr").onchange = () => renderMandis();
  const show = mk => {
    $("#mkTitle").textContent = mk + " - modal price, last 6 months";
    lineChart($("#mkChart"), { height: 240, series: [{ name: mk, short: mk.replace(" APMC", ""), color: css(COLOR.wheat), pts: (A.markets[mk] || []).map(p => ({ x: p.date, y: p.price })) }], refs: [{ y: A.msp.floor, label: "MSP" }] });
  };
  document.querySelectorAll("[data-mk]").forEach(tr => tr.onclick = () => show(tr.dataset.mk));
  if (lt.length) show(lt[0].market);
}

/* ------------------------------------------------------------------ WHAT TO WATCH */
function renderWatch() { (C === "wheat" ? renderWatchWheat : renderWatchMetal)(); }

function watchTable(items) {
  return `<div class="card tablewrap"><table><tr><th>Factor</th><th>Now</th><th>Where to check</th></tr>
    ${items.map(([n, st, now, src]) => `<tr><td><b>${esc(n)}</b></td><td>${st ? `<span class="status ${st}">${{ good: "Favourable", warning: "Watch", serious: "Important", critical: "Act / high impact" }[st]}</span> ` : ""}${esc(now)}</td><td class="small ink2">${esc(src)}</td></tr>`).join("")}
  </table></div>`;
}

function renderWatchWheat() {
  const b = A.benchmark, m = new Date(A.asof).getMonth() + 1, t = A.timing, omss = A.config.omss.reserve_price;
  const phase = m >= 3 && m <= 5 ? ["good", "Harvest & arrivals peak - the main buying window"] : m >= 6 && m <= 9 ? ["warning", "Post-harvest - stocks with FCI and traders; prices drift up slowly"]
    : m >= 10 && m <= 12 ? ["serious", "Sowing + festival/wedding demand - lean season starting, prices firm"] : ["critical", "Peak lean season - highest prices, FCI OMSS sales usually cap the top"];
  const items = [
    ["Season phase", phase[0], phase[1], "Seasonal index (Forecast tab)"],
    ["Mandi prices in MP / Rajasthan", b.chg_7d > 2 ? "serious" : b.chg_7d < -2 ? "good" : "", `Benchmark ${rs(b.price)}, 7 days ${pc(b.chg_7d)}, 30 days ${pc(b.chg_30d)}`, "Agmarknet - checked every 5 minutes here"],
    ["Landed cost vs your local rate", localRate() ? (localRate() - (A.best_source?.landed || 0) > 0 ? "good" : "critical") : "", localRate() ? (A.best_source ? `Margin ${rs(localRate() - A.best_source.landed)}/qtl` : "No recent source price") : "Enter your rate in the Mandis tab", "Your own selling rate"],
    ["MSP (govt floor)", b.price <= A.msp.floor * 1.04 ? "good" : "", `MSP ${rs(A.msp.floor)} (${A.msp.season}); next ${rs(A.msp.next_value)} (${A.msp.next_season})`, "Announced each Sep/Oct by the Cabinet (CCEA) - pib.gov.in"],
    ["FCI OMSS wheat sales (govt ceiling)", omss ? (b.price >= omss ? "critical" : "warning") : "", omss ? `Reserve price ${rs(omss)}` : "Not running / not set - set omss.reserve_price in config.json when FCI announces sales", "fci.gov.in → OMSS e-auctions (weekly, usually Aug–Mar)"],
    ["Central pool wheat stock vs buffer norm", "", "Low stock = govt sells less in OMSS = prices can run up. Norms: 1 Apr 74.6, 1 Jul 275.8, 1 Oct 205.2, 1 Jan 138 lakh tonnes", "FCI stock position (monthly) - fci.gov.in"],
    ["Stock limits on traders", "", "When imposed, traders must declare stock on the portal and keep under the limit - plan purchase size accordingly", "DFPD stock-limit orders - evegoils.nic.in/wheat"],
    ["Procurement & arrivals (Mar–Jun)", m >= 3 && m <= 6 ? "warning" : "", "High govt procurement + slow arrivals keep mandi prices firm even at harvest", "FCI / state procurement daily figures"],
    ["Weather: heatwave in Feb–Mar, rain at harvest", m >= 1 && m <= 4 ? "warning" : "", "Heat during grain filling cuts yield → higher prices later in the year", "IMD - mausam.imd.gov.in"],
    ["Sowing area (Oct–Dec)", m >= 10 || m <= 1 ? "warning" : "", "Lower rabi wheat area than last year = bullish for next year", "Agriculture ministry weekly rabi sowing report (PIB)"],
    ["Trade policy", "", "Export ban since May 2022; import duty 40%. Any change in either moves prices quickly", "DGFT notifications; Finance ministry"],
    ["Local demand", m === 1 || m >= 10 ? "serious" : "", "Sankranti (Jan), Dussehra/Diwali, wedding seasons, flour mills, PDS/PMGKAY supply", "Your buyers + local mills"],
    ["Diesel / truck freight", "", `Freight assumption ₹${A.config.freight.rate_per_qtl_per_km}/qtl/km - update when your transporter's rate changes`, "Your transporter"],
  ];
  $("#watch").innerHTML = `
  <h2>What to watch - and why it matters</h2>
  <p class="ink2 small">These move wheat prices. The agent tracks the first few automatically; the rest are announcements to check (links given). Colour = how much attention it needs right now.</p>
  ${watchTable(items)}
  <h3>Wheat year at a glance (for a Srikakulam trader)</h3>
  <div class="card"><div class="cal">${MON.map((mo, i) => `<div class="${t.cheapest_months.includes(mo) || (i >= 2 && i <= 4) ? "buy" : t.dearest_months.includes(mo) || i >= 9 || i <= 1 ? "sell" : ""} ${i === m - 1 ? "now" : ""}">${mo}</div>`).join("")}</div>
  <div class="small" style="margin-top:8px">
    <div>• <b>Mar–May</b>: new crop arrives in MP/Rajasthan → <b>buy & stock</b> (ధర తక్కువ - కొనండి).</div>
    <div>• <b>Jun–Sep</b>: hold; buy only on dips near MSP.</div>
    <div>• <b>Oct–Feb</b>: prices firm with festivals and the lean season → <b>sell stock in parts</b> (అమ్మండి). Watch FCI OMSS sales which cap prices.</div>
    <div>• Always compare: <i>expected price rise</i> vs <i>holding cost</i> (${pc(A.carrying_cost_30d_pct)} per month at your settings).</div>
  </div></div>`;
}

function renderWatchMetal() {
  const ind = A.indicators, w = A.world, m = new Date(A.asof).getMonth() + 1, t = A.timing;
  const festive = m >= 10 && m <= 11 ? ["serious", "Dhanteras / Diwali and the wedding season - Indian buying is strongest, local premiums rise"]
    : m === 12 || m <= 2 ? ["warning", "Wedding season (to Feb); world demand peaks before Chinese New Year"]
      : m >= 4 && m <= 5 ? ["warning", "Akshaya Tritiya and summer weddings - a short burst of Indian buying"]
        : ["good", "Quieter months for Indian demand (monsoon, Shraadh) - shops often discount"];
  const trend = ind.chg_30d > 3 ? "serious" : ind.chg_30d < -3 ? "good" : "";
  const fx = w.fx_chg_30d >= 1 ? "serious" : w.fx_chg_30d <= -1 ? "good" : "";
  const common = [
    ["Indian festival / wedding demand", festive[0], festive[1], "Seasonal index (Forecast tab); your jeweller"],
    [`World ${A.label.toLowerCase()} price`, trend, `US$${w.usd_oz.toLocaleString("en-IN")}/oz · India ${rs(A.price)}${A.unit_short}, 30 days ${pc(ind.chg_30d)}`, "gold-api.com live spot + COMEX futures - checked every 5 minutes here"],
    ["Rupee vs US dollar", fx, `₹${w.usdinr.toFixed(2)} per US$, ${pc(w.fx_chg_30d)} in 30 days - a weaker rupee makes metal dearer in India`, "RBI reference rate - rbi.org.in"],
    ["US interest rates & the dollar", "", "Rate cuts and a weaker dollar usually lift precious metals; rate hikes and a strong dollar push them down", "US Federal Reserve meeting calendar; CME FedWatch"],
    ["Import duty & GST", "", `Import duty ${A.costs.duty_pct}% (already in the price); GST ${A.costs.gst_pct}% on top when you buy. Duty is usually changed in the Union Budget (1 Feb)`, "Union Budget speech; CBIC notifications"],
  ];
  const own = {
    gold: [
      ["Central-bank buying", "", "Central banks (RBI, China, others) buying tonnes of gold has been a big support for prices", "World Gold Council - gold.org (monthly)"],
      ["War, crises, stock-market falls", "", "Gold is the safe haven - fear sends it up, calm can bring it down", "News"],
      ["Gold ETF flows", "", "Big money moving into or out of gold funds moves the price for weeks", "World Gold Council ETF flows; AMFI (India)"],
      ["Indian benchmark rate", "", "Compare the shop's rate with the day's IBJA rate before you buy or sell", "ibjarates.com; MCX gold"],
    ],
    silver: [
      ["Gold / silver ratio", A.ratio_gold_silver >= 85 ? "good" : A.ratio_gold_silver <= 65 ? "serious" : "", `1 oz of gold = ${A.ratio_gold_silver} oz of silver (long-run band ~65-85)`, "Worked out here from COMEX closes"],
      ["Industrial demand", "", "Over half of silver goes to industry - solar panels, electronics, EVs. Factory slowdowns hit silver harder than gold", "The Silver Institute - silverinstitute.org"],
      ["Bigger swings than gold", "", "Silver moves about 1.5-2 times as much as gold, both up and down - buy in parts", "Price history (Timeline tab)"],
      ["Indian benchmark rate", "", "Compare the shop's rate with the day's IBJA rate before you buy or sell", "ibjarates.com; MCX silver"],
    ],
    platinum: [
      ["Car-catalyst demand", "", "Most platinum goes into exhaust catalysts (diesel and hybrid cars); a shift to electric cars lowers demand", "World Platinum Investment Council - platinuminvestment.com (quarterly)"],
      ["Mine supply", "", "About 70% is mined in South Africa, the rest mostly Russia - strikes, power cuts or sanctions move the price fast", "WPIC; mining news"],
      ["Selling it back in India", "warning", "Few shops buy platinum back; buy-back cuts are often much bigger than for gold - ask before you buy", "Your jeweller"],
      ["Thin market", "", "Platinum swings more and trades less than gold - the forecast range is wider", "Forecast tab"],
    ],
  }[C] || [];
  $("#watch").innerHTML = `
  <h2>What to watch - ${esc(A.label.toLowerCase())}</h2>
  <p class="ink2 small">These move ${esc(A.label.toLowerCase())} prices in India. The agent tracks the first three automatically; the rest are things to check. Colour = how much attention it needs right now.</p>
  ${watchTable(common.slice(0, 3).concat(own, common.slice(3)))}
  <h3>${esc(A.label)} year at a glance</h3>
  <div class="card"><div class="cal">${MON.map((mo, i) => `<div class="${t.cheapest_months.includes(mo) ? "buy" : t.dearest_months.includes(mo) ? "sell" : ""} ${i === m - 1 ? "now" : ""}">${mo}</div>`).join("")}</div>
  <div class="small" style="margin-top:8px">
    <div>• Usually cheapest: <b>${t.cheapest_months.join(", ")}</b> · usually dearest: <b>${t.dearest_months.join(", ")}</b> (from ${A.seasonality.years_used} years of prices, swing about ${t.seasonal_swing_pct}%) - a weak pattern next to world news.</div>
    <div>• Buy in parts rather than all at once; for investment, coins and bars beat jewellery (making charges aren't paid back).</div>
    <div>• Always compare: <i>expected price rise</i> vs <i>bank interest</i> (${pc(A.carrying_cost_30d_pct)} a month at your settings).</div>
  </div></div>`;
}

/* ------------------------------------------------------------------ ALL (overview) */
function renderOverview() {
  const order = S.order;
  const card = k => {
    const it = S.items[k], s = it.signal, now = nowPrice(k), f = it.forecast30, rec = it.record.same_call || {};
    const grp = { buy: "BUY", sell: "SELL", hold: "HOLD", wait: "WAIT" }[callGroup(s.score, s.key)];
    const recLine = s.record_line || !rec.days ? s.record_line || "" : (grp === "SELL"
      ? `Past ${grp} days (${rec.scope}): lower 30 days later ${(100 - rec.rose_pct).toFixed(0)}% of ${rec.days}`
      : `Past ${grp} days (${rec.scope}): higher 30 days later ${rec.rose_pct.toFixed(0)}% of ${rec.days}`);
    return `<a class="ccard" href="#${k}/today" style="--c:${css(COLOR[k])}">
      <div class="top"><span class="em">${it.emoji}</span><b>${esc(it.label)}</b><span class="te">${esc(it.telugu_name)}</span><span class="pill ${s.key}">${esc(s.label)}</span></div>
      <div class="v">${rs(now)}<span class="u">${esc(it.unit_short)}</span> ${liveNote(k)}</div>
      <div class="d">1 day <span class="${cls(it.chg_1d)}">${pc(it.chg_1d)}</span> · 7 days <span class="${cls(it.chg_7d)}">${pc(it.chg_7d)}</span> · 30 days <span class="${cls(it.chg_30d)}">${pc(it.chg_30d)}</span></div>
      <div class="spark" id="sp-${k}"></div>
      <div class="d">${f ? `30-day forecast <b>${rs(f.price)}</b> (${pc((f.price / it.price - 1) * 100)})` : ""} · score ${scoreTxt(s.score)} of ±${absTxt(s.max_score)} · ${esc(s.confidence)} confidence</div>
      ${s.plain ? `<div class="d"><b>${esc(s.plain)}</b></div>` : ""}
      ${it.where ? `<div class="d where" title="${esc(it.where.detail)}">📍 ${esc(it.where.short)}</div>` : ""}
      ${s.change_line ? `<div class="d">🎯 ${esc(s.change_line)}</div>` : ""}
      ${s.pending ? `<div class="d">⏳ ${esc(s.pending)}</div>` : ""}
      ${it.long_term ? `<div class="d">📅 Saving for years: <b>${esc(it.long_term.label)}</b></div>` : ""}
      ${it.forecast_why ? `<div class="d">🔮 Why: ${esc(it.forecast_why.biggest)}</div>` : ""}
      <div class="d muted">${esc(s.telugu)} · ${esc(recLine)}</div>
    </a>`;
  };
  $("#all").innerHTML = `
  <h2>Today's prices and calls · ఈరోజు ధరలు</h2>
  <p class="ink2 small">One card per commodity: the agent's call, its price and the 30-day forecast (dashed, shaded side of each little chart). Click a card for the proof, the timeline and your trades.
    Gold, silver and platinum refresh live every 5 minutes; wheat when the mandis report.</p>
  <p class="ink2 small">📍 <b>Where the prices are from:</b> wheat is the wholesale mandi price at ${esc(S.items.wheat?.where?.short.split("· ")[1] || "Jabalpur, Indore & Kota")} - Andhra Pradesh publishes no wheat mandi prices, so the Srikakulam figure is that price plus fee, freight and handling.
    Gold, silver and platinum are the all-India import price (world spot × ₹ rate + import duty), before GST - a Srikakulam jeweller adds their own premium, making charges and GST.</p>
  <div class="cards">${order.map(card).join("")}</div>
  <h2>Last 12 months side by side</h2>
  <p class="ink2 small">Each line starts at 100 a year ago, so you can compare how much each has risen or fallen (110 = up 10%).</p>
  <div class="card"><div id="idxChart"></div>
    ${tableToggle("allTbl", ["", "Price", "Call", "Score", "30-day forecast", "Past record of this call"], order.map(k => { const it = S.items[k], r = it.record.same_call || {}; return [`${it.emoji} ${esc(it.label)}`, rs(nowPrice(k)) + esc(it.unit_short), esc(it.signal.label), scoreTxt(it.signal.score), it.forecast30 ? rs(it.forecast30.price) : "–", r.days ? `${r.days} days, rose ${r.rose_pct}% of the time (${esc(r.scope)})` : "–"]; }))}</div>`;
  const ser = [];
  for (const k of order) {
    const a = D[k];
    if (!a || !a.series) continue;
    const start = addDays(a.asof, -365), hist = a.series.filter(p => p.date >= start && p.price);
    const color = css(COLOR[k]);
    spark($(`#sp-${k}`), a.series.filter(p => p.date >= addDays(a.asof, -90) && p.price).map(p => ({ x: p.date, y: p.price })),
      a.forecast.slice(0, 30).map(p => ({ x: p.date, y: p.price })), color);
    if (hist.length) ser.push({ name: S.items[k].label, label: false, color, pts: hist.map(p => ({ x: p.date, y: p.price / hist[0].price * 100 })) });
  }
  if (ser.length) lineChart($("#idxChart"), { series: ser, yfmt: v => v.toFixed(0), height: 280, refs: [{ y: 100, label: "100 = a year ago" }] });
  else $("#idxChart").innerHTML = '<p class="muted">Loading…</p>';
}

/* ------------------------------------------------------------------ data */
const bucket = () => Math.floor(Date.now() / EVERY);   // a new URL every 5 minutes skips stale caches
async function getJSON(p) {
  const r = await fetch(`${p}?t=${bucket()}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${p}: HTTP ${r.status}`);
  return r.json();
}

async function load(k, refresh = false) {
  const it = S.items[k], have = D[k];
  if (have && have.generated_at === it.generated_at) return have;
  let a;
  if (k === "wheat") {
    a = await getJSON("data/latest.json");
  } else {
    const light = await getJSON(`data/${k}.json`);
    const h = have && have.asof === light.asof && have.series ? { series: have.series, series_weekly: have.series_weekly, predictions: have.predictions, track_rows: have.track_record.rows }
      : await getJSON(`data/${k}-history.json`);
    a = { ...light, series: h.series, series_weekly: h.series_weekly, predictions: h.predictions, track_record: { ...light.track_record, rows: h.track_rows } };
  }
  Object.assign(a, { label: it.label, telugu_name: it.telugu_name, emoji: it.emoji, unit_short: it.unit_short, unit: a.unit || it.unit });
  const px = {}, sig = {};
  a.series.forEach(p => { if (p.price) px[p.date] = p.price; });
  (a.track_record.rows || []).forEach(r => sig[r.date] = { score: r.score, key: r.signal });
  const live = a.track_record.live || {};
  (live.rows || []).concat(live.pending || []).forEach(r => sig[r.date] = { score: +r.score, key: r.signal });
  a._px = px; a._sig = sig;
  D[k] = a;
  return a;
}

async function pollLive() {
  await Promise.all((S.order || []).filter(isMetal).map(async k => {
    const lv = S.items[k].live;
    if (!lv || !lv.symbol || !lv.factor) return;
    try {
      const r = await fetch(LIVE_URL + lv.symbol, { cache: "no-store" });
      const j = await r.json(), usd = +j.price, inr = usd * lv.factor;
      // Ignore a bad tick: a real move of 15% in minutes would show up in the agent's own run.
      if (usd > 0 && Math.abs(inr / S.items[k].price - 1) < 0.15) LIVE[k] = { usd, rs: inr, updated: j.updatedAt || new Date().toISOString(), at: Date.now() };
    } catch { }
  }));
}

/* ------------------------------------------------------------------ navigation */
function parseHash() {
  const [c, v] = location.hash.slice(1).split("/");
  if (S && S.order.includes(c)) return [c, VIEWS.some(x => x[0] === v) ? v : "today"];
  if (VIEWS.some(x => x[0] === c)) return ["wheat", c];   // WheatWise 1.x links (#today, #mandis…)
  return ["all", "today"];
}

function header() {
  const g = S.generated_at, age = (Date.now() - Date.parse(g)) / 36e5;
  const stale = age >= 3 ? ` · ⚠︎ agent last ran ${Math.round(age)} h ago` : "";
  let t;
  if (C === "all") {
    t = `For Srikakulam, AP · 📍 wheat: MP & Rajasthan mandis · metals: all-India import price · checked every 5 minutes · agent ran ${hm(g)}${stale}`;
  } else if (C === "wheat") {
    const oldDays = Math.floor((Date.now() - new Date(A.asof + "T00:00:00+05:30")) / 864e5), best = A.best_source;
    t = `Wheat · ${fmtDate(A.asof)}${oldDays >= 3 ? ` ⚠︎ ${oldDays} days old` : ""} · 📍 ${A.benchmark.markets.map(x => x.replace(" APMC", "")).join(", ")} mandis ${rs(A.benchmark.price)}/qtl` + (best ? ` · landed at Srikakulam ${rs(best.landed)}/qtl` : "") + stale;
  } else {
    t = `${A.label} ${rs(nowPrice(C))}${A.unit_short} · 📍 all-India import price, before GST${LIVE[C] ? ` · live ${hm(LIVE[C].updated)}` : ""} · call ${A.signal.label} (${fmtDate(A.asof)})${stale}`;
  }
  $("#asof").textContent = t;
  document.querySelectorAll("#commodities button").forEach(b => b.setAttribute("aria-selected", b.dataset.c === C));
  document.querySelectorAll("#commodities .px").forEach(el => {
    const k = el.dataset.k, it = S.items[k];
    el.textContent = it ? `${rs(nowPrice(k))}` : "";
    el.className = "px " + (it ? it.signal.key : "");
    el.title = it ? `${it.signal.label} · score ${scoreTxt(it.signal.score)}` : "";
  });
}

function renderView() {
  header();
  const tabs = $("#tabs");
  tabs.hidden = C === "all";
  tabs.innerHTML = C === "all" ? "" : VIEWS.filter(v => !v[2] || v[2] === C)
    .map(([id, name]) => `<button role="tab" data-tab="${id}" aria-selected="${id === V}">${name}</button>`).join("");
  tabs.querySelectorAll("button").forEach(b => b.onclick = () => go(C, b.dataset.tab));
  const id = C === "all" ? "all" : V;
  document.querySelectorAll("main section").forEach(s => s.hidden = s.id !== id);
  const fn = C === "all" ? renderOverview : { today: renderToday, timeline: renderTimeline, forecast: renderForecast, pre: renderPre, trades: renderTrades, record: renderRecord, mandis: renderMandis, watch: renderWatch }[V];
  try { fn(); } catch (e) { $("#" + id).innerHTML = `<div class="card">Couldn't show this view: ${esc(e.message)}</div>`; console.error(e); }
  document.title = C === "all" ? "Dharalu · ధరలు - wheat, gold, silver, platinum" : `${A.emoji} ${A.label} ${A.signal.label} - Dharalu`;
}
window.renderAll = renderView;   // the Mac app calls this after a theme change

async function go(c, v = "today", push = true) {
  if (c !== "wheat" && v === "mandis") v = "today";   // only wheat has mandis
  if (c !== "all") {
    if (!D[c]) $("#" + (v || "today")).innerHTML = '<div class="card muted">Loading…</div>';
    try { await load(c); } catch (e) {
      document.querySelectorAll("main section").forEach(s => s.hidden = s.id !== "today");
      $("#today").innerHTML = `<div class="card">Could not load ${esc(c)} data (${esc(e.message)}).</div>`; return;
    }
    A = D[c]; PX = A._px; SIG = A._sig;
  }
  C = c; V = v;
  const h = "#" + (c === "all" ? "all" : `${c}/${v}`);
  if (push && location.hash !== h) history.replaceState(null, "", h);
  renderView();
  if (push) window.scrollTo(0, 0);
}

async function tick() {
  lastTick = Date.now();
  try {
    const s = await getJSON("data/summary.json");
    const changed = s.generated_at !== S.generated_at;
    S = s;
    if (changed) await Promise.all(Object.keys(D).map(k => load(k).catch(() => null)));
    if (C !== "all") { A = D[C]; PX = A._px; SIG = A._sig; }
  } catch { }
  await pollLive();
  // Forms (pre-trade, trades, mandis) keep what you typed; the rest re-draws with the new prices.
  if (C === "all" || ["today", "timeline", "record", "forecast", "watch"].includes(V)) renderView(); else header();
}

async function boot() {
  // Theme: "system" (default, follows prefers-color-scheme), "light" or "dark". The Mac app may set dh.theme.
  const MODES = ["system", "light", "dark"], LABEL = { system: "◐ System", light: "☀ Light", dark: "☾ Dark" };
  const applyTheme = () => {
    let m = store.get("theme", "system"); if (!MODES.includes(m)) m = "system";
    if (m === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = m;
    $("#theme").textContent = LABEL[m]; $("#theme").title = `Theme: ${m} (click to change)`; $("#theme").setAttribute("aria-label", `Theme: ${m}`);
    return m;
  };
  applyTheme();
  $("#theme").onclick = () => {
    const cur = applyTheme(); store.set("theme", MODES[(MODES.indexOf(cur) + 1) % 3]); applyTheme(); if (S) renderView();
  };
  $("#share").onclick = async () => {
    const url = location.href;
    const text = C === "all"
      ? "Dharalu today: " + S.order.map(k => `${S.items[k].emoji} ${S.items[k].label} ${S.items[k].signal.label} ${rs(nowPrice(k))}${S.items[k].unit_short}`).join(" · ")
      : `Dharalu ${A.emoji} ${A.label} ${A.asof}: ${A.signal.label} (${A.signal.telugu}) - score ${scoreTxt(A.signal.score)}. ${A.signal.plain ? A.signal.plain + " " : ""}${rs(C === "wheat" ? A.benchmark.price : nowPrice(C))}${A.unit_short}.`;
    if (navigator.share) { try { await navigator.share({ title: "Dharalu", text, url }); } catch { } }
    else { await navigator.clipboard.writeText(text + " " + url); alert("Copied - paste it in WhatsApp."); }
  };
  try {
    S = await getJSON("data/summary.json");
  } catch (e) {
    $("#all").hidden = false;
    $("#all").innerHTML = `<div class="card">Could not load data/summary.json - the agent has not run yet (${esc(e.message)}).</div>`; return;
  }
  $("#commodities").innerHTML = `<button data-c="all">📊 All</button>` + S.order.map(k =>
    `<button data-c="${k}">${S.items[k].emoji} ${esc(S.items[k].label)} <span class="px" data-k="${k}"></span></button>`).join("");
  $("#commodities").querySelectorAll("button").forEach(b => b.onclick = () => go(b.dataset.c, b.dataset.c === C ? V : (b.dataset.c === "wheat" || V !== "mandis" ? V : "today")));
  window.addEventListener("hashchange", () => { const [c, v] = parseHash(); if (c !== C || v !== V) go(c, v, false); });
  document.addEventListener("click", e => { const a = e.target.closest("a[href^='#']"); if (a) { e.preventDefault(); const h = a.getAttribute("href").slice(1).split("/"); go(h[0], h[1] || "today"); } });
  const [c, v] = parseHash();
  pollLive().then(() => { if (S) renderView(); });
  await go(c, v);
  // The overview's little charts need every commodity: load the rest in the background.
  Promise.all(S.order.map(k => load(k).catch(() => null))).then(() => { if (C === "all") renderView(); });
  setInterval(tick, EVERY);
  document.addEventListener("visibilitychange", () => { if (!document.hidden && Date.now() - lastTick > EVERY) tick(); });
  lastTick = Date.now();
}
boot();
