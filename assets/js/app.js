/* 蓄电池热榜 · 前端渲染 */
(function () {
  "use strict";

  const D = window.BATTERY_NEWS;
  if (!D) return;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const BADGE_COLORS = [
    "#dd5a2a", "#0f9d76", "#2f6bd8", "#7a5cd6", "#2b8a8a",
    "#b4802a", "#4a7a2f", "#a8456b", "#465a8a", "#8a5a2f",
  ];
  function hashCode(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) & 0xffffffff;
    return Math.abs(h);
  }
  function badge(name) {
    const color = BADGE_COLORS[hashCode(name) % BADGE_COLORS.length];
    const ch = name.replace(/[^\u4e00-\u9fa5A-Za-z0-9]/g, "").slice(0, 1) || "·";
    return `<span class="src-badge" style="background:${color}">${ch}</span>`;
  }
  function esc(s = "") {
    return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }
  function sparkPath(seedStr) {
    let s = hashCode(seedStr);
    const pts = [];
    const n = 24;
    for (let i = 0; i < n; i++) {
      s = (s * 1103515245 + 12345) & 0x7fffffff;
      const r = (s % 1000) / 1000;
      pts.push(0.18 + r * 0.55 + i / n * 0.22);
    }
    return pts.map((v, i) => `${(i / (n - 1)) * 100},${100 - v * 100}`).join(" ");
  }
  function spark(seedStr) {
    const pts = sparkPath(seedStr);
    return `<svg class="spark" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <defs><linearGradient id="g${hashCode(seedStr)}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="var(--hot)" stop-opacity=".22"/>
        <stop offset="100%" stop-color="var(--hot)" stop-opacity="0"/>
      </linearGradient></defs>
      <polyline points="${pts}" fill="none" stroke="var(--hot)" stroke-width="1.4" stroke-opacity=".55" vector-effect="non-scaling-stroke"/>
      <polygon points="${pts} 100,100 0,100" fill="url(#g${hashCode(seedStr)})"/>
    </svg>`;
  }

  /* header / meta */
  $("#issueLine").textContent = `${D.issue} · ${D.dateCN} ${D.weekday}`;
  $("#headline").textContent = D.headline;
  $("#lead").textContent = D.lead;
  $("#stats").innerHTML = D.stats
    .map((s) => `<div class="stat"><div class="n">${esc(s.n)}</div><div class="l">${esc(s.l)}</div></div>`)
    .join("");
  $("#hotDate").textContent = `${D.dateCN} ${D.weekday}`;
  $("#footIssue").textContent = `${D.issue} · ${D.dateCN}`;
  document.title = `蓄电池热榜 ${D.dateCN} | 储能与电池每日情报`;

  const ticker = $("#ticker");
  if (!D.prices || !D.prices.length) {
    ticker.parentElement.style.display = "none";
  } else {
    ticker.innerHTML = D.prices
      .map(
        (p) => `<span class="tick">${esc(p.name)} <span class="v">${esc(p.value)}<em style="font-style:normal;font-size:10px"> ${esc(p.unit)}</em></span>
        <span class="${p.dir === "up" ? "up" : "down"}">${p.dir === "up" ? "▲" : "▼"} ${esc(p.chg)}</span></span>`
      )
      .join("");
  }

  /* 精选 */
  const [feat, ...rest] = D.picked;

  function renderFeature(p) {
    const src = (p.sources || [])
      .map((s) => `<span class="src">${badge(s.name)}${esc(s.name)}</span>`)
      .join("");
    return `<article class="feature" data-id="${esc(p.id)}">
      <div class="feature-main">
        <div class="feature-badge">${esc(p.kicker || "精选")}</div>
        <h2>${esc(p.title)}</h2>
        <p class="feature-sum">${esc(p.summary)}</p>
        <p class="feature-why"><b>多源情况</b>　${esc(p.why)}</p>
        <div class="meta-row">
          ${(p.tags || []).map((t) => `<span class="chip tag">#${esc(t)}</span>`).join("")}
          <span class="chip">${esc(p.time)}</span>
        </div>
      </div>
      <div class="feature-side">
        <div class="heat-block">
          <span class="heat-label">独立信源报道数</span>
          <span class="heat-num">${esc(p.heat)}<small>源</small></span>
        </div>
        ${spark(p.id + p.title)}
        <div class="side-meta">
          <span>信源 <em>${esc((p.sources || []).map((s) => s.name).join(" / "))}</em></span>
          <span>标签 <em>${esc((p.tags || []).join(" · "))}</em></span>
        </div>
        <div class="meta-row">${src}</div>
      </div>
    </article>`;
  }

  function renderCard(p) {
    return `<article class="card" data-id="${esc(p.id)}">
      <div class="card-top">
        <span class="card-tag">${esc(p.kicker || "精选")}</span>
        <span class="card-heat">
          <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M12 3c2.6 3.2 1.4 5 1.4 6.2 0 1-.6 1.6-1.3 1.6-1 0-1.5-.8-1.4-2.1C9.2 10 8 11.4 8 13.4A4 4 0 0 0 16 13.4C16 9.6 13.6 6.2 12 3z" fill="currentColor" opacity=".9"/><path d="M12 13.2v5" stroke="currentColor" stroke-width="1.5"/></svg>
          ${esc(p.heat)} 源
        </span>
      </div>
      <h3>${esc(p.title)}</h3>
      ${p.summary && p.summary !== "点击查看原文与报道来源。" ? `<p class="card-sum">${esc(p.summary)}</p>` : ""}
      <div class="card-foot">
        <div class="src-list">${(p.sources || []).map((s) => `<span class="src">${badge(s.name)}${esc(s.name)}</span>`).join("")}</div>
        <span class="time">${esc(p.time)}</span>
      </div>
    </article>`;
  }

  $("#pickedBody").innerHTML =
    renderFeature(feat) + `<div class="grid">${rest.map(renderCard).join("")}</div>`;

  /* 热点榜 */
  function trendMark(t) {
    if (t === "up") return `<span class="trend up">▲ 上升</span>`;
    if (t === "down") return `<span class="trend down">▼ 回落</span>`;
    return `<span class="trend">— 持平</span>`;
  }
  $("#hotList").innerHTML = D.hot
    .map((h) => {
      const srcs = (h.sources || [])
        .map((s) => `<span class="src">${badge(s.name)}${esc(s.name)}</span>`)
        .join("");
      return `<div class="hot-item" data-id="h${h.rank}">
        <div class="rank">${String(h.rank).padStart(2, "0")}</div>
        <div class="hot-body">
          <h3 class="hot-title">${esc(h.title)}${h.isNew ? '<span class="new">NEW</span>' : ""}</h3>
          <div class="hot-meta">
            <span class="chip tag">${esc(h.category)}</span>
            <span>${esc(h.time)}</span>
            ${srcs}
          </div>
        </div>
        <div class="hot-right">
          <span class="hot-heat">
            <svg viewBox="0 0 24 24" width="11" height="11" aria-hidden="true"><path d="M12 3c2.6 3.2 1.4 5 1.4 6.2 0 1-.6 1.6-1.3 1.6-1 0-1.5-.8-1.4-2.1C9.2 10 8 11.4 8 13.4A4 4 0 0 0 16 13.4C16 9.6 13.6 6.2 12 3z" fill="currentColor" opacity=".9"/></svg>
            ${h.heat} 源
          </span>
          ${trendMark(h.trend)}
        </div>
      </div>`;
    })
    .join("");

  /* 侧栏 */
  const maxCat = Math.max(...D.categories.map((c) => c.count));
  const pricePanel = D.prices && D.prices.length
    ? `<div class="panel">
        <h4>价格快照</h4>
        <div class="price-list">
          ${D.prices
            .map(
              (p) => `<div class="price-row">
              <span class="name">${esc(p.name)}</span>
              <span class="val">${esc(p.value)}<em>${esc(p.unit)}</em><span class="chg ${p.dir}">${esc(p.chg)}</span></span>
            </div>`
            )
            .join("")}
        </div>
      </div>`
    : "";
  const srcNames = (D.picked || []).concat(D.hot || []).flatMap((x) => (x.sources || []).map((s) => s.name));
  const srcCount = new Set(srcNames).size;
  $("#rail").innerHTML = `
    <div class="panel">
      <h4>分类分布</h4>
      <div class="bars">
        ${D.categories
          .map(
            (c) => `<div class="bar-row">
            <span>${esc(c.name)}</span>
            <span class="bar-track"><span class="bar-fill" data-w="${Math.round((c.count / maxCat) * 100)}"></span></span>
            <span class="cnt">${c.count}</span>
          </div>`
          )
          .join("")}
      </div>
    </div>
    ${pricePanel}
    <div class="panel">
      <h4>榜单说明</h4>
      <p class="note">
        <b>热度 = 独立信源报道数</b>：同一事件被多少家不同机构报道，就记多少分；同分时按重要性与时效排序。
        本期覆盖 ${srcCount || D.stats[1].n} 个信源：中国电池工业协会、北极星储能网、中国储能网、OFweek 锂电网、电池网。
        每一条都保留原文链接，可逐条核对。
      </p>
    </div>
  `;
  requestAnimationFrame(() => {
    $$(".bar-fill").forEach((b) => (b.style.width = b.dataset.w + "%"));
  });

  /* 日报 */
  const dl = D.daily;
  function sectionHTML(s, i) {
    const strip = s.points
      ? `<div class="data-strip">${s.points
          .map(
            (p) => `<div class="data-cell">
            <div class="k">${esc(p.k)}</div>
            <div class="v ${esc(p.tone || "")}">${p.v}</div>
            <div class="s">${esc(p.s || "")}</div>
          </div>`
          )
          .join("")}</div>`
      : "";
    return `<section class="daily-section">
      <div class="sec-title"><span class="sec-no">${esc(s.no || String(i + 1).padStart(2, "0"))}</span><h3>${esc(s.title)}</h3></div>
      ${strip}
      ${(s.paras || []).map((p) => `<p>${p}</p>`).join("")}
      ${s.judge ? `<div class="judge">${s.judge}</div>` : ""}
    </section>`;
  }
  function tableHTML(t) {
    return `<table class="data">
      <caption>${esc(t.caption)}</caption>
      <thead><tr>${t.head.map((h, i) => `<th${i > 0 ? ' style="text-align:right"' : ""}>${esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${t.rows
        .map(
          (r) =>
            `<tr>${r
              .map((c, i) => `<td${i > 0 ? ' class="num"' : ""} style="${i > 0 ? "text-align:right" : ""}">${c}</td>`)
              .join("")}</tr>`
        )
        .join("")}</tbody>
    </table>`;
  }

  $("#dailyBody").innerHTML = `
    <header class="daily-head">
      <div class="daily-kicker">${esc(D.issue)} · ${esc(D.dateCN)} ${esc(D.weekday)}</div>
      <h1>${esc(dl.title)}</h1>
      <p class="daily-dek">${esc(dl.dek)}</p>
      <div class="daily-sign">
        ${D.categories.map((c) => `<span class="chip tag">${esc(c.name)} ${c.count}</span>`).join("")}
        <span>更新 ${esc(D.updatedAt || "")}</span>
      </div>
    </header>
    ${dl.sections.map(sectionHTML).join("")}
    ${
      dl.tables && dl.tables.length
        ? `<div class="daily-section">
        <div class="sec-title"><span class="sec-no">${String(dl.sections.length + 1).padStart(2, "0")}</span><h3>数据附录</h3></div>
        ${dl.tables.map(tableHTML).join("")}
        <p class="note" style="margin-top:12px">
          注：以上数字由标题自动抽取，可能与正文口径存在差异，引用前请点开原文核对。
        </p>
      </div>`
        : ""
    }
    <div class="end-mark">${esc(dl.end || "")}</div>
  `;

  /* tabs */
  const tabs = $$(".tab");
  const sections = $$(".section");
  function activate(target, push = true) {
    tabs.forEach((t) => t.classList.toggle("is-active", t.dataset.target === target));
    sections.forEach((s) => s.classList.toggle("is-visible", s.id === target));
    if (push && location.hash !== "#" + target) history.replaceState(null, "", "#" + target);
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
  }
  tabs.forEach((t) => t.addEventListener("click", () => activate(t.dataset.target)));
  if (location.hash) {
    const target = location.hash.slice(1);
    if (["picked", "hot", "daily"].includes(target)) activate(target, false);
  }

  /* drawer */
  const drawer = $("#drawer");
  const backdrop = $("#backdrop");
  let lastFocus = null;

  function openDrawer(id) {
    let item = D.picked.find((p) => p.id === id);
    if (!item && id.startsWith("h")) {
      const h = D.hot.find((x) => "h" + x.rank === id);
      if (h) item = Object.assign({ kicker: h.category, tags: [h.category] }, h);
    }
    if (!item) return;
    const srcLinks = (item.sources || [])
      .map(
        (s) => `<a class="src-link" href="${esc(s.url)}" target="_blank" rel="noopener">
          ${badge(s.name)}<span>${esc(s.name)} · 阅读原文</span><span class="arrow">↗</span></a>`
      )
      .join("");
    $("#drawerBody").innerHTML = `
      <div class="meta-row">
        <span class="chip hot">${esc(item.kicker || "精选")}</span>
        ${item.heat ? `<span class="chip">${esc(String(item.heat))} 源报道</span>` : ""}
        <span class="chip">${esc(item.time || "")}</span>
      </div>
      <h2>${esc(item.title)}</h2>
      <div class="d-sec">
        <div class="d-label">摘要</div>
        <p>${esc(item.summary || "")}</p>
      </div>
      ${item.why ? `<div class="d-sec"><div class="d-label">多源情况</div><p class="d-why">${esc(item.why)}</p></div>` : ""}
      <div class="d-sec">
        <div class="d-label">信息来源</div>
        <div class="src-list">${srcLinks}</div>
      </div>
      <div class="d-foot">内容为公开信息整理，热度为独立信源报道数，仅供行业信息参考。</div>
    `;
    drawer.hidden = false;
    backdrop.hidden = false;
    document.body.style.overflow = "hidden";
    lastFocus = document.activeElement;
    $("#drawerClose").focus();
  }
  function closeDrawer() {
    drawer.hidden = true;
    backdrop.hidden = true;
    document.body.style.overflow = "";
    if (lastFocus) lastFocus.focus();
  }
  document.addEventListener("click", (e) => {
    const t = e.target.closest(".card, .feature, .hot-item");
    if (t) openDrawer(t.dataset.id);
  });
  $("#drawerClose").addEventListener("click", closeDrawer);
  backdrop.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !drawer.hidden) closeDrawer();
  });

  /* search */
  const search = $("#search");
  search.addEventListener("input", () => {
    const q = search.value.trim().toLowerCase();
    const active = $(".section.is-visible");
    if (!active) return;
    const nodes = $$(".card, .feature, .hot-item", active);
    let hits = 0;
    nodes.forEach((n) => {
      const ok = !q || n.textContent.toLowerCase().includes(q);
      n.style.display = ok ? "" : "none";
      if (ok) hits++;
    });
    const tip = $("#emptyTip");
    if (tip) tip.hidden = !(active.id === "picked" && q && hits === 0);
  });

  /* theme */
  const themeKey = "batteryhot-theme";
  const saved = localStorage.getItem(themeKey);
  if (saved) document.documentElement.dataset.theme = saved;
  else if (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches)
    document.documentElement.dataset.theme = "dark";
  $("#themeBtn").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = cur;
    localStorage.setItem(themeKey, cur);
  });
})();
