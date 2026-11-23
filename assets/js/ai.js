/* =========================================================
   AI 评分层：评分角标、真实 7 日热度折线、抽屉里的 AI 判断
   ========================================================= */
(function () {
  "use strict";
  const D = window.BATTERY_NEWS;
  if (!D) return;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (s = "") =>
    String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const map = {};
  (D.picked || []).forEach((p) => (map[p.id] = p));
  (D.hot || []).forEach((h) => (map["h" + h.rank] = h));
  const hasAI = (D.picked || []).some((p) => typeof p.score === "number") ||
                (D.hot || []).some((h) => typeof h.score === "number");
  if (!hasAI) return;

  const level = (s) => (s >= 75 ? "high" : s >= 55 ? "mid" : "low");
  function badgeHTML(it) {
    if (!it || typeof it.score !== "number") return "";
    const n = (it.caveats || []).length;
    return `<span class="ai-badge ai-${level(it.score)}" title="${esc((it.importance || "") + (n ? "｜注意 " + n + " 条" : ""))}">AI ${it.score}${n ? `<i class="ai-flag">${n}</i>` : ""}</span>`;
  }

  /* ---------- 真实 7 日热度折线 ---------- */
  function trendSVG(series, heat) {
    const pts = (series || []).filter((p) => typeof p.h === "number");
    if (pts.length < 2) {
      return `<div class="trend-empty"><span>近 7 日</span><b>${esc(heat)}</b> 源 · 历史不足两天，明日起画趋势</div>`;
    }
    const w = 100, h = 56, pad = 4;
    const max = Math.max(...pts.map((p) => p.h), 1);
    const step = pts.length > 1 ? (w - pad * 2) / (pts.length - 1) : 0;
    const coords = pts.map((p, i) => {
      const x = pad + i * step;
      const y = h - pad - (p.h / max) * (h - pad * 2);
      return [x.toFixed(1), y.toFixed(1)];
    });
    const line = coords.map((c) => c.join(",")).join(" ");
    const dots = coords
      .map((c) => `<circle cx="${c[0]}" cy="${c[1]}" r="2.2" fill="var(--hot)"/>`)
      .join("");
    const labels = pts
      .map((p, i) => `<span class="tl${i === pts.length - 1 ? " on" : ""}">${esc(p.d)}</span>`)
      .join("");
    return `<div class="trend-chart">
      <div class="trend-cap">近 7 日独立信源报道数</div>
      <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
        <polyline points="${line}" fill="none" stroke="var(--hot)" stroke-width="1.6" stroke-opacity=".8" vector-effect="non-scaling-stroke"/>
        ${dots}
      </svg>
      <div class="trend-labels">${labels}</div>
    </div>`;
  }

  const feat = (D.picked || [])[0];
  const holder = $(".feature-side .spark");
  if (feat && holder) {
    const box = document.createElement("div");
    box.className = "trend-box";
    box.innerHTML = trendSVG(feat.trend, feat.heat);
    holder.replaceWith(box);
  }

  /* ---------- 角标 ---------- */
  $$(".card").forEach((el) => {
    const it = map[el.dataset.id];
    const top = $(".card-top", el);
    if (it && top) top.insertAdjacentHTML("beforeend", badgeHTML(it));
  });
  $$(".hot-item").forEach((el) => {
    const it = map[el.dataset.id];
    const meta = $(".hot-meta", el);
    if (it && meta) meta.insertAdjacentHTML("beforeend", badgeHTML(it));
  });
  const featEl = $(".feature");
  if (featEl && feat) {
    const badge = $(".feature-badge", featEl);
    if (badge) badge.insertAdjacentHTML("afterend", badgeHTML(feat));
  }

  /* ---------- 抽屉增强 ---------- */
  function aiBlock(it) {
    if (!it || typeof it.score !== "number") return null;
    const lv = level(it.score);
    const cav = (it.caveats || []).length
      ? `<ul class="ai-cav">${it.caveats.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>`
      : `<p class="ai-cav-none">未发现明显的口径问题或通稿痕迹。</p>`;
    const div = document.createElement("div");
    div.className = "ai-block ai-" + lv;
    div.innerHTML = `
      <div class="ai-score-wrap">
        <div class="ai-score-num">${it.score}<small>/100</small></div>
        <div class="ai-score-label">AI 信息成色</div>
      </div>
      <div class="ai-text">
        <div class="ai-k">重要程度</div>
        <div class="ai-v">${esc(it.importance || "—")}</div>
        <div class="ai-k">需要注意</div>
        ${cav}
      </div>`;
    return div;
  }

  document.addEventListener("click", (e) => {
    const t = e.target.closest(".card, .feature, .hot-item");
    if (!t) return;
    const it = map[t.dataset.id];
    setTimeout(() => {
      const body = $("#drawerBody");
      if (!body || !it || body.querySelector(".ai-block")) return;
      const blk = aiBlock(it);
      if (!blk) return;
      const h2 = $("h2", body);
      if (h2) h2.insertAdjacentElement("afterend", blk);
      else body.insertBefore(blk, body.firstChild);
    }, 0);
  });
})();
