/* WheatWise dashboard - reads data/latest.json written by the agent.
   Trades and local rates live only in this browser (localStorage). */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const rs = v => v == null || isNaN(v) ? "–" : "₹" + Math.round(v).toLocaleString("en-IN");
const pc = (v, d = 1) => v == null || isNaN(v) ? "–" : (v > 0 ? "+" : "") + v.toFixed(d) + "%";
const cls = v => v > 0 ? "pos" : v < 0 ? "neg" : "zero";
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const fmtDate = s => { const d = new Date(s + "T00:00:00"); return d.getDate() + " " + MON[d.getMonth()] + " " + d.getFullYear(); };
const dayDiff = (a, b) => Math.round((new Date(b) - new Date(a)) / 864e5);
const addDays = (s, n) => { const d = new Date(s + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const store = {
  get: (k, dflt) => { try { return JSON.parse(localStorage.getItem("ww." + k)) ?? dflt; } catch { return dflt; } },
  set: (k, v) => localStorage.setItem("ww." + k, JSON.stringify(v)),
};
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

let A = null;          // analysis
let PX = {};           // date -> benchmark price
let SIG = {};          // date -> { score, key } (replayed + live)

/* ------------------------------------------------------------------ charts */
function niceTicks(lo, hi, n = 5) {
  const span = hi - lo || 1, step0 = span / n, mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= step0);
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(v);
  return out;
}

/* Line chart: series [{name, color, dash, pts:[{x:"YYYY-MM-DD", y}], band:[{x, lo, hi}]}], refs [{y, label}] */
function lineChart(el, { series, refs = [], height = 300, yfmt = rs }) {
  const W = 1000, H = height, m = { l: 62, r: 92, t: 12, b: 28 };
  const all = series.flatMap(s => s.pts.map(p => p.x).concat((s.band || []).map(p => p.x)));
  const xs = [...new Set(all)].sort();
  if (!xs.length) { el.innerHTML = '<p class="muted">No data yet.</p>'; return; }
  const t0 = Date.parse(xs[0]), t1 = Date.parse(xs[xs.length - 1]) || t0 + 1;
  let ys = series.flatMap(s => s.pts.map(p => p.y).concat((s.band || []).flatMap(b => [b.lo, b.hi]))).filter(v => v != null);
  ys = ys.concat(refs.map(r => r.y));
  let lo = Math.min(...ys), hi = Math.max(...ys); const pad = (hi - lo) * 0.08 || 50; lo -= pad; hi += pad;
  const X = s => m.l + (Date.parse(s) - t0) / (t1 - t0 || 1) * (W - m.l - m.r);
  const Y = v => m.t + (hi - v) / (hi - lo) * (H - m.t - m.b);
  let g = "";
  for (const v of niceTicks(lo, hi)) g += `<line class="gridline" x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${m.l - 8}" y="${Y(v) + 4}" text-anchor="end">${yfmt(v)}</text>`;
  const months = Math.max(1, Math.round((t1 - t0) / 2.6e9));
  const every = months > 30 ? 6 : months > 14 ? 3 : months > 6 ? 2 : 1;
  const d0 = new Date(t0); d0.setDate(1);
  for (let d = new Date(d0), k = 0; d <= new Date(t1); d.setMonth(d.getMonth() + 1), k++) {
    if (d < new Date(t0) || d.getMonth() % every) continue;
    const s = d.toISOString().slice(0, 10), lbl = d.getMonth() === 0 || every >= 3 ? MON[d.getMonth()] + " " + String(d.getFullYear()).slice(2) : MON[d.getMonth()];
    g += `<text x="${X(s)}" y="${H - 8}" text-anchor="middle">${lbl}</text>`;
  }
  g += `<line class="axis" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/>`;
  for (const r of refs) g += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(r.y)}" y2="${Y(r.y)}" stroke="${css("--muted")}" stroke-dasharray="3 4"/><text class="lbl" x="${W - m.r + 6}" y="${Y(r.y) + 4}">${esc(r.label)}</text>`;
  for (const s of series) {
    if (s.band && s.band.length) {
      const up = s.band.map(b => `${X(b.x)},${Y(b.hi)}`), dn = s.band.slice().reverse().map(b => `${X(b.x)},${Y(b.lo)}`);
      g += `<polygon points="${up.concat(dn).join(" ")}" fill="${s.color}" opacity=".16"/>`;
    }
    let path = "", pen = false;
    for (const p of s.pts) { if (p.y == null) { pen = false; continue; } path += (pen ? "L" : "M") + X(p.x).toFixed(1) + "," + Y(p.y).toFixed(1); pen = true; }
    g += `<path d="${path}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linejoin="round" ${s.dash ? 'stroke-dasharray="6 4"' : ""}/>`;
    const last = s.pts.filter(p => p.y != null).pop();
    if (last && s.label !== false) g += `<text class="lbl" x="${X(last.x) + 6}" y="${Y(last.y) + 4}">${esc(s.short || s.name)}</text>`;
  }
  g += `<line id="xh" y1="${m.t}" y2="${H - m.b}" stroke="${css("--axis")}" visibility="hidden"/><g id="dots"></g>`;
  g += `<rect x="${m.l}" y="${m.t}" width="${W - m.l - m.r}" height="${H - m.t - m.b}" fill="transparent" id="hit"/>`;
  el.classList.add("chart");
  el.innerHTML = `<div class="legend">${series.length > 1 ? series.map(s => `<span class="${s.dash ? "dash" : ""}" style="--c:${s.color}">${esc(s.name)}</span>`).join("") : ""}</div>
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(series.map(s => s.name).join(", "))}">${g}</svg><div class="tip"></div>`;
  const svg = $("svg", el), tip = $(".tip", el), xh = $("#xh", el), dots = $("#dots", el);
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
      rows += `<div><span class="sw" style="background:${s.color}"></span>${esc(s.name)}: <b>${yfmt(y)}</b>${b ? ` <span class="muted">(${yfmt(b.lo)}–${yfmt(b.hi)})</span>` : ""}</div>`;
    });
    dots.innerHTML = dd;
    if (!rows) { tip.style.display = "none"; return; }
    tip.innerHTML = `<div class="muted">${fmtDate(best)}</div>${rows}`;
    tip.style.display = "block";
    const px = X(best) / W * r.width, left = px > r.width * 0.6 ? px - tip.offsetWidth - 12 : px + 12;
    tip.style.left = left + "px"; tip.style.top = "26px";
  };
  $("#hit", el).addEventListener("mousemove", move);
  $("#hit", el).addEventListener("mouseleave", () => { tip.style.display = "none"; xh.setAttribute("visibility", "hidden"); dots.innerHTML = ""; });
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

/* ------------------------------------------------------------------ helpers */
const localRate = () => store.get("localRate", null);
function forecastAt(days) {
  const f = A.forecast || [];
  return f[Math.min(f.length, Math.max(1, days)) - 1];
}
function verdictWord(score, key) {
  if (key) return key.replace("_", " ");
  return score >= 3 ? "STRONG BUY" : score >= 1 ? "BUY" : score >= 0 ? "WAIT" : score >= -2 ? "SELL" : "STRONG SELL";
}
function tableToggle(id, head, rows) {
  return `<details><summary>Show as table</summary><div class="tablewrap"><table id="${id}"><tr>${head.map(h => `<th>${h}</th>`).join("")}</tr>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("")}</table></div></details>`;
}

/* ------------------------------------------------------------------ TODAY */
function renderToday() {
  const s = A.signal, b = A.benchmark, f30 = A.forecast_points["30"], best = A.best_source, tr = A.track_record.summary;
  const brief = A.briefing.ai || A.briefing.rules;
  const bars = Array.from({ length: s.max_score * 2 + 1 }, (_, i) => i - s.max_score)
    .map(v => `<i class="${(s.score > 0 && v > 0 && v <= s.score) || (s.score < 0 && v < 0 && v >= s.score) || (v === 0 && s.score === 0) ? "on" : ""}"></i>`).join("");
  const lr = localRate();
  const gkey = s.score >= 1 ? "buy_days" : s.score <= -1 ? "sell_days" : s.key === "HOLD" ? "hold_days" : "wait_days";
  // Under 10 days in the last year proves little - quote the whole-history replay instead.
  const thin = !(tr[gkey] && tr[gkey].days >= 10) && A.track_record.summary_all && A.track_record.summary_all[gkey];
  const grp = thin ? A.track_record.summary_all[gkey] : tr[gkey];
  const span = thin ? `since ${fmtDate(A.track_record.since)}` : "in the last year";
  const grpName = s.score >= 1 ? "BUY" : s.score <= -1 ? "SELL" : s.key;
  const live = A.track_record.live || {};
  let proofLine = "";
  if (grp) {
    proofLine = s.score >= 1
      ? `On the <b>${grp.days}</b> past days ${span} when these same rules said <b>${grpName}</b>, the price 30 days later was higher <b>${grp.rose_pct}%</b> of the time (average move <b class="${cls(grp.avg_move_pct)}">${pc(grp.avg_move_pct)}</b>; beat the holding cost ${grp.beat_holding_cost_pct}% of the time).`
      : s.score <= -1
        ? `On the <b>${grp.days}</b> past days ${span} when these rules said <b>${grpName}</b>, the price 30 days later was lower <b>${(100 - grp.rose_pct).toFixed(1)}%</b> of the time (average move <b class="${cls(grp.avg_move_pct)}">${pc(grp.avg_move_pct)}</b>).`
        : s.key === "HOLD"
          ? `On the <b>${grp.days}</b> past HOLD days ${span}, keeping the stock beat the holding cost <b>${grp.beat_holding_cost_pct}%</b> of the time (price rose ${grp.rose_pct}% of the time, average move <b class="${cls(grp.avg_move_pct)}">${pc(grp.avg_move_pct)}</b>).`
          : `On the <b>${grp.days}</b> past WAIT days ${span}, the average 30-day move was <b class="${cls(grp.avg_move_pct)}">${pc(grp.avg_move_pct)}</b> - not enough to beat holding costs.`;
  }
  $("#today").innerHTML = `
  <div class="card signal">
    <div class="badge ${s.key}">
      <div class="big">${esc(s.label)}</div><div class="te">${esc(s.telugu)}</div>
      <div class="scorebar" title="Score ${s.score} of ±${s.max_score}">${bars}</div>
      <div class="meta">Score ${s.score > 0 ? "+" : ""}${s.score} of ±${s.max_score} · Confidence ${esc(s.confidence)}</div>
      <div class="meta">${fmtDate(A.asof)}</div>
    </div>
    <div>
      <div class="advice"><div><b>If you are buying</b>${esc(s.buyer)}</div><div><b>If you are holding stock</b>${esc(s.holder)}</div></div>
      <div class="tabs2"><button data-lang="en" class="primary">English</button><button data-lang="te">తెలుగు</button>
        <span class="muted small" style="align-self:center">Briefing by ${esc(brief.source)}</span></div>
      <div class="pre" id="brief">${esc(brief.english)}</div>
    </div>
  </div>

  <h2>Why this call - the proof</h2>
  <p class="ink2 small">Each rule below looks at real data and adds or removes points. Total score ≥ +3 = strong buy, +1 to +2 = buy, 0 = hold (if the forecast + season rules still point up) or wait, −1 to −2 = sell, ≤ −3 = strong sell.</p>
  <div class="card tablewrap"><table>
    <tr><th>Rule</th><th>What the data shows today</th><th>Test used</th><th class="num">Points</th></tr>
    ${s.evidence.map(e => `<tr><td><b>${esc(e.rule)}</b><div class="why">${esc(e.why)}</div></td>
      <td>${esc(e.value)}<div class="why">Source: ${esc(e.source)}</div></td><td class="small ink2">${esc(e.test)}</td>
      <td class="num pts ${cls(e.points)}">${e.points > 0 ? "+" : ""}${e.points}</td></tr>`).join("")}
    <tr><td colspan="3"><b>Total score</b></td><td class="num pts ${cls(s.score)}">${s.score > 0 ? "+" : ""}${s.score}</td></tr>
  </table></div>
  <div class="card"><b>Has this worked before?</b> ${proofLine || "Not enough history yet."}
    ${live.graded ? `<br>Live calls graded so far: <b>${live.graded}</b>, right <b>${live.right_pct}%</b>.` : `<br><span class="muted small">Live calls are graded automatically 30 days after each call (${live.calls || 0} logged so far).</span>`}
    <div class="small muted">See the "Agent track record" tab for every past call.</div></div>

  <h2>Key numbers</h2>
  <div class="grid">
    <div class="tile"><div class="k">Benchmark price (${b.markets.map(x => x.replace(" APMC", "")).join(", ")})</div><div class="v">${rs(b.price)}</div>
      <div class="d">1 day <span class="${cls(b.chg_1d)}">${pc(b.chg_1d)}</span> · 7 days <span class="${cls(b.chg_7d)}">${pc(b.chg_7d)}</span> · 30 days <span class="${cls(b.chg_30d)}">${pc(b.chg_30d)}</span></div></div>
    <div class="tile"><div class="k">30-day forecast</div><div class="v">${f30 ? rs(f30.price) : "–"}</div>
      <div class="d">${f30 ? `Likely ${rs(f30.low)} – ${rs(f30.high)} (${pc((f30.price / b.price - 1) * 100)})` : ""}</div></div>
    <div class="tile"><div class="k">Cheapest landed at Srikakulam</div><div class="v">${best ? rs(best.landed) : "–"}</div>
      <div class="d">${best ? `${esc(best.market)}, ${best.km} km · mandi ${rs(best.mandi_price)}` : ""}</div></div>
    <div class="tile"><div class="k">Govt floor (MSP)</div><div class="v">${rs(A.msp.floor)}</div>
      <div class="d">Price is ${pc((b.price / A.msp.floor - 1) * 100)} above · next MSP ${rs(A.msp.next_value)}</div></div>
    <div class="tile"><div class="k">Your Srikakulam selling rate</div><div class="v">${lr ? rs(lr) : "–"}</div>
      <div class="d">${lr && best ? `Margin vs cheapest landed: <b class="${cls(lr - best.landed)}">${rs(lr - best.landed)}</b>/qtl` : `<a href="#" data-goto="mandis">Enter it</a> to see your margin`}</div></div>
    <div class="tile"><div class="k">Cost of holding stock 30 days</div><div class="v">${pc(A.carrying_cost_30d_pct)}</div>
      <div class="d">Interest + godown + losses (≈ ${rs(b.price * A.carrying_cost_30d_pct / 100)}/qtl)</div></div>
  </div>

  <h2>Price - last 12 months and next 45 days</h2>
  <div class="card"><div id="todayChart"></div></div>
  <p class="small muted">Generated ${esc(A.generated_at)} · latest mandi day in data ${esc(A.asof)} · all-India feed day ${esc(A.feed_day)}</p>`;
  document.querySelectorAll("[data-lang]").forEach(bt => bt.onclick = () => {
    document.querySelectorAll("[data-lang]").forEach(x => x.classList.toggle("primary", x === bt));
    $("#brief").textContent = bt.dataset.lang === "te" ? brief.telugu : brief.english;
  });
  priceChart($("#todayChart"), 365);
}

function priceChart(el, days) {
  const hist = A.series.slice(-days).map(p => ({ x: p.date, y: p.price }));
  const fc = A.forecast.map(p => ({ x: p.date, y: p.price }));
  if (hist.length) fc.unshift(hist[hist.length - 1]);
  lineChart(el, {
    series: [
      { name: "Benchmark price (actual)", short: "Actual", label: false, color: css("--s1"), pts: hist },
      { name: "Forecast (shaded = likely range)", short: "Forecast", color: css("--s2"), dash: true, pts: fc,
        band: A.forecast.map(p => ({ x: p.date, lo: p.low, hi: p.high })) },
    ],
    refs: [{ y: A.msp.floor, label: "MSP " + rs(A.msp.floor) }],
  });
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
  $("#forecast").innerHTML = `
  <h2>Forecast · ధర అంచనా</h2>
  <div class="card"><div class="row" style="margin-bottom:6px">
    ${[90, 365, 1095].map(d => `<button data-range="${d}" class="${d === 365 ? "primary" : ""}">${d === 90 ? "3 months" : d === 365 ? "1 year" : "3 years"}</button>`).join("")}</div>
    <div id="fcChart"></div></div>
  <h3>How accurate has the forecast been? (proof)</h3>
  <p class="small ink2">We re-ran the forecast on past dates using only the data available then, and compared it with what really happened.
   "Naive" = assuming the price stays the same. If our error is smaller than naive, the forecast is adding value.</p>
  <div class="card tablewrap"><table><tr><th>Ahead</th><th class="num">Forecast</th><th class="num">Likely range (80%)</th>
    <th class="num">Avg error</th><th class="num">Naive error</th><th class="num">Direction right</th><th class="num">Tests</th></tr>${rows}</table></div>
  <h3>Seasonal pattern - when wheat is usually cheap or dear</h3>
  <p class="small ink2">Each bar = how far that month's price usually sits from the yearly average.
    Built from ${se.years_used} full years of mandi data (${Math.round(se.weight_on_data * 100)}% weight) blended with the typical Indian pattern.</p>
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
function renderPre() {
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
      [s.score >= 1, `Agent signal is ${s.label} (score ${s.score > 0 ? "+" : ""}${s.score})`, "Agent signal supports buying", "Agent signal does not support buying now"],
      [edge > 0, `Forecast move ${pc((fc.price / b.price - 1) * 100)} vs holding cost ${pc(carry / landed * 100)} over ${days} days`, "Expected rise beats holding cost", "Expected rise does NOT beat holding cost"],
      [lt.length ? landed <= lt[0].landed * 1.02 : null, `This source lands at ${rs(landed)} vs cheapest ${rs(lt.length ? lt[0].landed : landed)}`, "Among the cheapest sources", "A cheaper source exists"],
      [b.price <= A.msp.floor * 1.08, `Benchmark ${rs(b.price)} vs MSP ${rs(A.msp.floor)}`, "Close to the MSP floor (limited downside)", "Well above MSP (more downside if prices fall)"],
      [lr ? lr > landed : null, lr ? `Your selling rate ${rs(lr)} vs landed ${rs(landed)}` : "Enter your Srikakulam rate in the Mandis tab", "Immediate resale margin is positive", "No margin at today's local rate"],
    ];
    const good = checks.filter(x => x[0] === true).length, total = checks.filter(x => x[0] !== null).length;
    $("#preOut").innerHTML = `
    <div class="grid">
      <div class="tile"><div class="k">Landed cost at Srikakulam</div><div class="v">${rs(landed)}</div><div class="d">mandi ${rs(price)} + fee ${rs(fee)} + freight ${rs(freight)} + handling/bags/brokerage ${rs(extras)}</div></div>
      <div class="tile"><div class="k">Total money needed</div><div class="v">${rs(landed * qty)}</div><div class="d">${qty} qtl (${(qty / 10).toFixed(1)} tonnes)</div></div>
      <div class="tile"><div class="k">Holding cost for ${days} days</div><div class="v">${rs(carry)}/qtl</div><div class="d">${rs(carry * qty)} in total</div></div>
      <div class="tile"><div class="k">Break-even sell price</div><div class="v">${rs(breakeven)}</div><div class="d">Sell above this to make money</div></div>
    </div>
    <div class="card tablewrap"><h3 style="margin-top:0">If you sell after ${days} days</h3><table>
      <tr><th>Scenario</th><th class="num">Sell price</th><th class="num">Profit per qtl</th><th class="num">Total profit</th></tr>
      ${scen.map(x => `<tr><td>${x.n}</td><td class="num">${rs(x.sell)}</td><td class="num ${cls(x.per)}">${rs(x.per)}</td><td class="num ${cls(x.pl)}"><b>${rs(x.pl)}</b></td></tr>`).join("")}
    </table><p class="small muted">${+f.sell.value ? "Using your planned sell price." : lr ? "Sell price = your Srikakulam rate moved in line with the forecast." : "Sell price = today's landed cost moved in line with the forecast (enter your local rate for a better estimate)."}</p></div>
    <div class="card"><h3 style="margin-top:0">Checklist - ${good} of ${total} in your favour</h3>
      ${checks.map(([ok, detail, yes, no]) => `<div style="margin:6px 0"><span class="status ${ok === null ? "" : ok ? "good" : "critical"}">${ok === null ? "Unknown" : ok ? "Yes" : "No"}</span>
        <b>${ok === null ? "Not enough data" : ok ? yes : no}</b><div class="why">${esc(detail)}</div></div>`).join("")}
      <p><b>${good >= total - 1 && total >= 3 ? "✅ Looks like a good trade on today's numbers." : good >= Math.ceil(total / 2) ? "⚠️ Mixed - consider buying a smaller lot, or wait." : "❌ The numbers are against this trade today."}</b></p></div>`;
  }
}

/* ------------------------------------------------------------------ MY TRADES (post-analysis) */
const trades = () => store.get("trades", []);
// Same-day buys go before sells so a sale can match stock bought that morning.
const tradeOrder = (a, b) => a.date.localeCompare(b.date) || (a.type === b.type ? 0 : a.type === "buy" ? -1 : 1);
function saveTrades(t) { store.set("trades", t.sort(tradeOrder)); }

function timingScore(t) {
  // Where did this price sit among benchmark prices 30 days either side? Buys: lower = better.
  const win = [];
  for (let k = -30; k <= 30; k++) { const p = PX[addDays(t.date, k)]; if (p) win.push(p); }
  const p0 = PX[t.date] || PX[addDays(t.date, -1)] || PX[addDays(t.date, -2)];
  if (!p0 || win.length < 10) return null;
  const below = win.filter(p => p < p0).length / win.length * 100;
  return { score: Math.round(t.type === "buy" ? 100 - below : below), complete: dayDiff(t.date, A.asof) >= 30, bench: p0 };
}

function fifo(list) {
  const lots = [], sells = [];
  const cr = A.config.carrying;
  for (const t of [...list].sort(tradeOrder)) {
    if (t.type === "buy") { lots.push({ ...t, left: +t.qty }); continue; }
    let q = +t.qty, cost = 0, carry = 0, matched = 0;
    while (q > 0 && lots.length) {
      const l = lots[0], take = Math.min(q, l.left), days = Math.max(0, dayDiff(l.date, t.date));
      cost += take * l.price; matched += take;
      carry += take * (l.price * (cr.interest_pct_per_month + cr.loss_pct_per_month) / 100 + cr.storage_per_qtl_per_month) * days / 30;
      l.left -= take; q -= take; if (l.left <= 1e-9) lots.shift();
    }
    const gross = matched * t.price - cost;
    sells.push({ ...t, matched, unmatched: q, avgCost: matched ? cost / matched : 0, gross, carry, net: gross - carry });
  }
  return { lots, sells };
}

function renderTrades() {
  const list = trades(), { lots, sells } = fifo(list), lr = localRate();
  const stock = lots.reduce((s, l) => s + l.left, 0), stockCost = lots.reduce((s, l) => s + l.left * l.price, 0);
  const mark = lr || (A.best_source ? A.best_source.landed : null);
  const realised = sells.reduce((s, x) => s + x.net, 0);
  const ts = list.map(timingScore).filter(Boolean);
  const avgTiming = ts.length ? ts.reduce((s, x) => s + x.score, 0) / ts.length : null;
  let agree = 0, judged = 0;
  const rows = list.map(t => {
    const tsc = timingScore(t), sg = SIG[t.date], sig = sg && sg.score;
    let ag = "–";
    if (sig != null) {
      judged++;
      const ok = t.type === "buy" ? sig >= 0 : sig <= 0 && sg.key !== "HOLD";   // HOLD = keep stock, so selling went against it
      if (ok) agree++;
      ag = `<span class="status ${ok ? "good" : "serious"}">${verdictWord(sig, sg.key)} (${sig > 0 ? "+" : ""}${sig})</span>`;
    }
    const s = sells.find(x => x.id === t.id);
    return `<tr><td>${fmtDate(t.date)}</td><td>${t.type === "buy" ? "Buy" : "Sell"}</td><td class="num">${t.qty}</td><td class="num">${rs(t.price)}</td>
      <td>${esc(t.place || "")}</td><td class="num">${tsc ? `${tsc.score}/100${tsc.complete ? "" : "*"}` : "–"}</td><td>${ag}</td>
      <td class="num ${s ? cls(s.net) : ""}">${s ? rs(s.net) : ""}${s && s.unmatched > 0 ? `<div class="small warnText">${s.unmatched} qtl sold with no recorded purchase - not in P&L</div>` : ""}</td><td class="small">${esc(t.notes || "")}</td>
      <td><button data-del="${t.id}" title="Delete">✕</button></td></tr>`;
  }).join("");
  $("#trades").innerHTML = `
  <h2>My trades - post-analysis</h2>
  <p class="ink2 small">Record each purchase and sale. Stored only in this browser - export a CSV to back up or move to another phone. Buy price = your all-in cost per quintal at Srikakulam.</p>
  <div class="card"><form class="row" id="tradeForm">
    <label>Date<input type="date" name="date" required value="${A.asof}"></label>
    <label>Type<select name="type"><option value="buy">Buy</option><option value="sell">Sell</option></select></label>
    <label>Quantity (qtl)<input type="number" name="qty" required step="0.1" min="0"></label>
    <label>Price ₹/qtl<input type="number" name="price" required step="1" min="0"></label>
    <label>From / to<input name="place" placeholder="e.g. Katni / local mill"></label>
    <label style="flex:1;min-width:160px">Notes<input name="notes"></label>
    <button class="primary">Add</button>
  </form>
  <div class="row" style="margin-top:10px"><button id="exp">Export CSV</button><label class="btn" style="flex-direction:row">Import CSV<input type="file" id="imp" accept=".csv" hidden></label></div></div>
  <div class="grid">
    <div class="tile"><div class="k">Realised profit (after holding cost)</div><div class="v ${cls(realised)}">${rs(realised)}</div><div class="d">${sells.length} sales matched first-in-first-out</div></div>
    <div class="tile"><div class="k">Stock on hand</div><div class="v">${stock.toFixed(1)} qtl</div><div class="d">Avg cost ${stock ? rs(stockCost / stock) : "–"}</div></div>
    <div class="tile"><div class="k">Unrealised profit</div><div class="v ${cls(stock && mark ? stock * mark - stockCost : 0)}">${stock && mark ? rs(stock * mark - stockCost) : "–"}</div><div class="d">${lr ? "at your Srikakulam rate" : "at today's cheapest landed cost"} ${mark ? rs(mark) : ""}</div></div>
    <div class="tile"><div class="k">Your timing score</div><div class="v">${avgTiming != null ? Math.round(avgTiming) + "/100" : "–"}</div><div class="d">100 = bought at the lowest / sold at the highest price of the surrounding 2 months</div></div>
    <div class="tile"><div class="k">Followed the agent</div><div class="v">${judged ? Math.round(agree / judged * 100) + "%" : "–"}</div><div class="d">${judged} trades on days with a signal</div></div>
  </div>
  <div class="card tablewrap"><table><tr><th>Date</th><th>Type</th><th class="num">Qty</th><th class="num">₹/qtl</th><th>From/to</th>
    <th class="num">Timing</th><th>Agent said that day</th><th class="num">Net P&L</th><th>Notes</th><th></th></tr>${rows || '<tr><td colspan="10" class="muted">No trades yet.</td></tr>'}</table>
    <p class="small muted">* timing score still settling (less than 30 days of prices after the trade). Holding cost uses your settings: ${A.config.carrying.interest_pct_per_month}%/month interest, ₹${A.config.carrying.storage_per_qtl_per_month}/qtl/month godown, ${A.config.carrying.loss_pct_per_month}%/month losses.</p></div>
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
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); a.download = "wheatwise-trades.csv"; a.click();
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
function renderRecord() {
  const tr = A.track_record, s = tr.summary, live = tr.live || {};
  const g = (n, x) => x ? `<tr><td><b>${n}</b></td><td class="num">${x.days}</td><td class="num ${cls(x.avg_move_pct)}">${pc(x.avg_move_pct, 2)}</td><td class="num">${x.rose_pct}%</td><td class="num">${x.beat_holding_cost_pct}%</td></tr>` : "";
  const rec = x => `${g("BUY / STRONG BUY", x.buy_days)}${g("HOLD", x.hold_days)}${g("WAIT", x.wait_days)}${g("SELL / STRONG SELL", x.sell_days)}${g("All days (baseline)", x.all_days)}`;
  $("#record").innerHTML = `
  <h2>Agent track record - proof that the signal works (or doesn't)</h2>
  <p class="ink2 small">For every day in the last year we re-ran the same rules using only data available on that day, then checked the price 30 days later.
   A good BUY should be followed by rises, a good HOLD by rises that beat the holding cost, and a good SELL by falls. Each day only sees the data known on that day (the seasonal pattern too), so this is a fair test - the live record below is graded on real calls.</p>
  <div class="card tablewrap"><table><tr><th>When the agent said</th><th class="num">Days</th><th class="num">Avg price move next 30 days</th><th class="num">Price rose</th><th class="num">Rise beat holding cost</th></tr>
    ${rec(s)}</table></div>
  ${tr.summary_all ? `<h3>Whole history - since ${fmtDate(tr.since)}</h3>
  <p class="ink2 small">The same replay over every day we have data for. More days = stronger proof, but older years were a different market.</p>
  <div class="card tablewrap"><table><tr><th>When the agent said</th><th class="num">Days</th><th class="num">Avg price move next 30 days</th><th class="num">Price rose</th><th class="num">Rise beat holding cost</th></tr>
    ${rec(tr.summary_all)}</table></div>` : ""}
  <div class="card"><div id="recChart"></div></div>
  <h3>Live calls (graded 30 days later)</h3>
  <div class="card tablewrap">${live.graded ? `<p>Right <b>${live.right_pct}%</b> of ${live.graded} graded calls.</p>` : ""}
    <table><tr><th>Date</th><th>Call</th><th class="num">Price then</th><th class="num">30 days later</th><th class="num">Move</th><th>Right?</th></tr>
    ${(live.rows || []).slice().reverse().map(r => `<tr><td>${fmtDate(r.date)}</td><td>${verdictWord(+r.score, r.signal)} (${r.score})</td><td class="num">${rs(+r.price)}</td><td class="num">${rs(r.after30)}</td><td class="num ${cls(r.move_pct)}">${pc(r.move_pct)}</td><td>${r.right ? '<span class="status good">Yes</span>' : '<span class="status critical">No</span>'}</td></tr>`).join("")}
    ${!(live.rows || []).length && !(live.pending || []).length ? '<tr><td colspan="6" class="muted">No live calls yet - one is logged on every run.</td></tr>' : ""}
    ${(live.pending || []).slice().reverse().slice(0, 10).map(r => `<tr><td>${fmtDate(r.date)}</td><td>${verdictWord(+r.score, r.signal)} (${r.score})</td><td class="num">${rs(+r.price)}</td><td colspan="3" class="muted">waiting - graded on ${fmtDate(addDays(r.date, 30))}</td></tr>`).join("")}
    </table></div>`;
  const rows = tr.rows || [];
  lineChart($("#recChart"), {
    height: 260,
    series: [{ name: "Benchmark price", short: "Price", color: css("--s1"), pts: rows.map(r => ({ x: r.date, y: r.price })) },
      { name: "Price 30 days later", short: "+30d", color: css("--s3"), pts: rows.map(r => ({ x: r.date, y: r.after30 })) }],
  });
  const svg = $("#recChart svg");
  if (svg && rows.length) {
    // tint each day by the signal it gave: green = buy, red = sell
    const W = 1000, m = { l: 62, r: 92 }, t0 = Date.parse(rows[0].date), t1 = Date.parse(rows[rows.length - 1].date);
    const X = s => m.l + (Date.parse(s) - t0) / (t1 - t0 || 1) * (W - m.l - m.r), w = (W - m.l - m.r) / rows.length + 0.5;
    const tint = r => r.score > 0 ? "#0ca30c" : r.score < 0 ? "#d03b3b" : r.signal === "HOLD" ? "#c98500" : null;
    const bg = rows.filter(tint).map(r => `<rect x="${X(r.date)}" y="12" width="${w}" height="220" fill="${tint(r)}" opacity=".08"/>`).join("");
    svg.insertAdjacentHTML("afterbegin", bg);
    $("#recChart .legend").insertAdjacentHTML("beforeend", `<span class="box" style="--c:#0ca30c">BUY days</span><span class="box" style="--c:#c98500">HOLD days</span><span class="box" style="--c:#d03b3b">SELL days</span>`);
  }
}

/* ------------------------------------------------------------------ MANDIS */
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
  $("#lr").onchange = () => { renderMandis(); renderToday(); };
  const show = mk => {
    $("#mkTitle").textContent = mk + " - modal price, last 6 months";
    lineChart($("#mkChart"), { height: 240, series: [{ name: mk, short: mk.replace(" APMC", ""), color: css("--s1"), pts: (A.markets[mk] || []).map(p => ({ x: p.date, y: p.price })) }], refs: [{ y: A.msp.floor, label: "MSP" }] });
  };
  document.querySelectorAll("[data-mk]").forEach(tr => tr.onclick = () => show(tr.dataset.mk));
  if (lt.length) show(lt[0].market);
}

/* ------------------------------------------------------------------ WHAT TO WATCH */
function renderWatch() {
  const b = A.benchmark, m = new Date(A.asof).getMonth() + 1, t = A.timing, omss = A.config.omss.reserve_price;
  const phase = m >= 3 && m <= 5 ? ["good", "Harvest & arrivals peak - the main buying window"] : m >= 6 && m <= 9 ? ["warning", "Post-harvest - stocks with FCI and traders; prices drift up slowly"]
    : m >= 10 && m <= 12 ? ["serious", "Sowing + festival/wedding demand - lean season starting, prices firm"] : ["critical", "Peak lean season - highest prices, FCI OMSS sales usually cap the top"];
  const items = [
    ["Season phase", phase[0], phase[1], "Seasonal index (Forecast tab)"],
    ["Mandi prices in MP / Rajasthan", b.chg_7d > 2 ? "serious" : b.chg_7d < -2 ? "good" : "", `Benchmark ${rs(b.price)}, 7 days ${pc(b.chg_7d)}, 30 days ${pc(b.chg_30d)}`, "Agmarknet - updated twice a day here"],
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
  <div class="card tablewrap"><table><tr><th>Factor</th><th>Now</th><th>Where to check</th></tr>
    ${items.map(([n, st, now, src]) => `<tr><td><b>${esc(n)}</b></td><td>${st ? `<span class="status ${st}">${{ good: "Favourable", warning: "Watch", serious: "Important", critical: "Act / high impact" }[st]}</span> ` : ""}${esc(now)}</td><td class="small ink2">${esc(src)}</td></tr>`).join("")}
  </table></div>
  <h3>Wheat year at a glance (for a Srikakulam trader)</h3>
  <div class="card"><div class="cal">${MON.map((mo, i) => `<div class="${t.cheapest_months.includes(mo) || (i >= 2 && i <= 4) ? "buy" : t.dearest_months.includes(mo) || i >= 9 || i <= 1 ? "sell" : ""} ${i === m - 1 ? "now" : ""}">${mo}</div>`).join("")}</div>
  <div class="small" style="margin-top:8px">
    <div>• <b>Mar–May</b>: new crop arrives in MP/Rajasthan → <b>buy & stock</b> (ధర తక్కువ - కొనండి).</div>
    <div>• <b>Jun–Sep</b>: hold; buy only on dips near MSP.</div>
    <div>• <b>Oct–Feb</b>: prices firm with festivals and the lean season → <b>sell stock in parts</b> (అమ్మండి). Watch FCI OMSS sales which cap prices.</div>
    <div>• Always compare: <i>expected price rise</i> vs <i>holding cost</i> (${pc(A.carrying_cost_30d_pct)} per month at your settings).</div>
  </div></div>`;
}

/* ------------------------------------------------------------------ boot */
function show(tab) {
  document.querySelectorAll("nav button").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === tab));
  document.querySelectorAll("main section").forEach(s => s.hidden = s.id !== tab);
  history.replaceState(null, "", "#" + tab);
}

async function boot() {
  const th = store.get("theme", null); if (th) document.documentElement.dataset.theme = th;
  $("#theme").onclick = () => {
    const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = dark ? "light" : "dark"; store.set("theme", document.documentElement.dataset.theme); renderAll();
  };
  $("#share").onclick = async () => {
    const s = A.signal, text = `WheatWise ${A.asof}: ${s.label} (${s.telugu}) - score ${s.score}. Benchmark ${rs(A.benchmark.price)}/qtl.`;
    if (navigator.share) { try { await navigator.share({ title: "WheatWise", text, url: location.href.split("#")[0] }); } catch { } }
    else { await navigator.clipboard.writeText(text + " " + location.href.split("#")[0]); alert("Copied - paste it in WhatsApp."); }
  };
  document.querySelectorAll("nav button").forEach(b => b.onclick = () => show(b.dataset.tab));
  document.addEventListener("click", e => { const g = e.target.closest("[data-goto]"); if (g) { e.preventDefault(); show(g.dataset.goto); } });
  try {
    A = await (await fetch("data/latest.json", { cache: "no-store" })).json();
  } catch (e) {
    $("#today").innerHTML = `<div class="card">Could not load data/latest.json - the agent has not run yet.</div>`; return;
  }
  A.series.forEach(p => { if (p.price) PX[p.date] = p.price; });
  (A.track_record.rows || []).forEach(r => SIG[r.date] = { score: r.score, key: r.signal });
  const live = A.track_record.live || {};
  (live.rows || []).concat(live.pending || []).forEach(r => SIG[r.date] = { score: +r.score, key: r.signal });
  $("#asof").textContent = `Srikakulam, AP · prices up to ${fmtDate(A.asof)} · ₹ per quintal`;
  renderAll();
  show(location.hash.slice(1) || "today");
}
function renderAll() { renderToday(); renderForecast(); renderPre(); renderTrades(); renderRecord(); renderMandis(); renderWatch(); }
boot();
