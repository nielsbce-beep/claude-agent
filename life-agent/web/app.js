/* ═══════════════════════════════════════════════════════════════════════
   LIFE OS — frontend
   ═══════════════════════════════════════════════════════════════════════ */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const eur = (n) => "€" + Math.round(n).toLocaleString("nl-NL");
const ICON = {
  check: '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
};
const DAGEN = ["zondag", "maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag"];
const MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"];
const ROLLEN = {
  Planning: "Tijd & prioriteiten", Sport: "Training & herstel", Geld: "Financiën",
  Kansen: "Groei & kansen", Criticus: "Advocaat van de duivel", Motivatie: "Mindset & drive",
};

let state = null;           // laatste /api/overview
let boardAgents = [];
let chat = loadLS("lifeos.chat", []);

/* ── utils ──────────────────────────────────────────────────────────── */
function loadLS(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }
function saveLS(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { } }

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  checkAuth(res);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

/* Sessie verlopen of uitgelogd → naar het inlogscherm */
function checkAuth(res) {
  if (res.status === 401) { location.href = "/login"; throw new Error("Niet ingelogd"); }
}

function toast(msg, err = false) {
  const t = document.createElement("div");
  t.className = "toast" + (err ? " err" : "");
  t.textContent = msg;
  $("#toasts").append(t);
  setTimeout(() => t.remove(), 2700);
}

/* Minimale, veilige markdown → HTML (eerst escapen) */
function md(src) {
  const lines = esc(src).split("\n");
  let html = "", list = null, code = false, para = [];
  const inline = (s) => s
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/(^|\W)_([^_\n]+)_(?=\W|$)/g, "$1<em>$2</em>");
  const flushP = () => { if (para.length) { html += `<p>${inline(para.join("<br>"))}</p>`; para = []; } };
  const flushL = () => { if (list) { html += `</${list}>`; list = null; } };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith("```")) { flushP(); flushL(); html += code ? "</code></pre>" : "<pre><code>"; code = !code; continue; }
    if (code) { html += line + "\n"; continue; }
    let m;
    if ((m = line.match(/^#{1,6}\s+(.*)/))) { flushP(); flushL(); html += `<h4>${inline(m[1])}</h4>`; }
    else if ((m = line.match(/^\s*[-*•]\s+(.*)/))) { flushP(); if (list !== "ul") { flushL(); html += "<ul>"; list = "ul"; } html += `<li>${inline(m[1])}</li>`; }
    else if ((m = line.match(/^\s*\d+[.)]\s+(.*)/))) { flushP(); if (list !== "ol") { flushL(); html += "<ol>"; list = "ol"; } html += `<li>${inline(m[1])}</li>`; }
    else if (!line.trim()) { flushP(); flushL(); }
    else { flushL(); para.push(line); }
  }
  flushP(); flushL(); if (code) html += "</code></pre>";
  return html;
}

/* ── tabs ───────────────────────────────────────────────────────────── */
function setView(name) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === name));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + name));
  moveGlider();
  history.replaceState(null, "", "#" + name);
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (name === "journal") loadJournal();
}
function moveGlider() {
  const a = $(".tab.active"), g = $(".tab-glider");
  if (!a) return;
  g.style.width = a.offsetWidth + "px";
  g.style.transform = `translateX(${a.offsetLeft - 4}px)`;
}
$$(".tab").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
window.addEventListener("resize", moveGlider);

/* ── klok & begroeting ─────────────────────────────────────────────── */
function tick() {
  const n = new Date();
  $("#clock").textContent = n.toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" });
}
setInterval(tick, 10_000); tick();

function datumStr(d = new Date()) { return `${DAGEN[d.getDay()]} ${d.getDate()} ${MAANDEN[d.getMonth()]}`; }

/* ═══ Rendering — Vandaag ════════════════════════════════════════════ */
function render() {
  const s = state, h = new Date().getHours();
  const groet = h < 6 ? "Goedenacht" : h < 12 ? "Goedemorgen" : h < 18 ? "Goedemiddag" : "Goedenavond";
  $("#hero-date").textContent = datumStr();
  $("#journal-date").textContent = datumStr();
  $("#hero-greeting").innerHTML = `${groet}, <span class="grad-text">Niels</span>.`;

  const bits = [];
  if (s.whoop) bits.push(`herstel <b>${s.whoop.recovery}%</b>`);
  bits.push(`<b>${s.agenda.today.length}</b> ${s.agenda.today.length === 1 ? "afspraak" : "afspraken"}`);
  bits.push(`<b>${s.todos.length}</b> open todo's`);
  if (s.streak) bits.push(`<b>${s.streak}</b> dagen streak 🔥`);
  $("#hero-sub").innerHTML = bits.join(" · ");

  $("#logout").hidden = !s.auth;
  renderRecovery(); renderAgenda(); renderCommitment(); renderGoals();
  renderTodos(); renderPortfolio(); renderFood(); renderJournalMini(); renderBooks();
}

function recZone(p) {
  if (p >= 67) return { c: "#34d399", t: "Groen licht", s: "Je lichaam is klaar voor een zware sessie." };
  if (p >= 50) return { c: "#fbbf24", t: "Matig trainen", s: "Train, maar houd de intensiteit beheerst." };
  if (p >= 34) return { c: "#fb923c", t: "Lichte beweging", s: "Wandelen, mobiliteit of rustig cardio." };
  return { c: "#f87171", t: "Rustdag", s: "Prioriteit: slaap, voeding en herstel." };
}

function renderRecovery() {
  const w = state.whoop, el = $("#recovery");
  if (!w) {
    el.innerHTML = `<div class="empty">Geen Whoop-data beschikbaar.<br>Koppel opnieuw met <code>python cli.py whoop-login</code></div>`;
    $("#rec-source").textContent = "offline";
    return;
  }
  const z = recZone(w.recovery), C = 2 * Math.PI * 64;
  $("#rec-source").textContent = "Whoop · live";
  el.innerHTML = `
    <div class="ring-wrap">
      <div class="ring" style="--glow:${z.c}">
        <svg viewBox="0 0 150 150">
          <defs><linearGradient id="rg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="${z.c}" stop-opacity=".55"/><stop offset="1" stop-color="${z.c}"/></linearGradient></defs>
          <circle class="track" cx="75" cy="75" r="64"/>
          <circle class="val" cx="75" cy="75" r="64" stroke="url(#rg)" stroke-dasharray="${C}" stroke-dashoffset="${C}"/>
        </svg>
        <div class="center"><div><div class="num">${w.recovery}<small>%</small></div><div class="lbl">recovery</div></div></div>
      </div>
      <div style="flex:1;min-width:0">
        <div class="advice" style="color:${z.c}">${z.t}</div>
        <div class="advice-sub">${z.s}</div>
        <div class="stats">
          <div class="stat"><b>${w.hrv}<small>ms</small></b><span>HRV</span></div>
          <div class="stat"><b>${w.rhr}<small>bpm</small></b><span>Rust-HF</span></div>
          <div class="stat"><b>${w.sleep_hours}<small>u</small></b><span>Slaap</span></div>
          <div class="stat"><b>${w.sleep_quality}<small>%</small></b><span>Kwaliteit</span></div>
        </div>
      </div>
    </div>`;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    $(".ring .val", el).style.strokeDashoffset = C * (1 - w.recovery / 100);
  }));
}

function renderAgenda() {
  const { today, tomorrow } = state.agenda, el = $("#agenda");
  $("#agenda-count").textContent = `${today.length} vandaag`;
  const nu = new Date().toTimeString().slice(0, 5);
  let html = "";
  if (!today.length) html += `<div class="empty">Niets gepland vandaag — ruimte voor deep work.</div>`;
  else {
    html += `<ul class="timeline">`;
    let lijn = false;
    for (const e of today) {
      const start = e.start || "00:00", eind = e.end || start;
      const voorbij = !e.allday && eind <= nu, bezig = !e.allday && start <= nu && nu < eind;
      if (!lijn && !e.allday && start > nu) { html += `<li class="now-line"><span>NU</span></li>`; lijn = true; }
      html += `<li class="ev ${voorbij ? "past" : ""} ${bezig ? "now" : ""}">
        <time>${e.allday ? "dag" : e.start}</time><span class="dot"></span>
        <div style="min-width:0"><div class="t">${esc(e.title)}</div>${e.end && !e.allday ? `<div class="d">tot ${e.end}</div>` : ""}</div></li>`;
      if (bezig) lijn = true;
    }
    html += `</ul>`;
  }
  html += `<div class="sub-h">Morgen</div>`;
  html += tomorrow.length
    ? tomorrow.slice(0, 4).map((e) => `<div class="mini-ev"><time>${e.allday ? "dag" : e.start}</time><span>${esc(e.title)}</span></div>`).join("")
      + (tomorrow.length > 4 ? `<div class="mini-ev"><time></time><span class="muted">+${tomorrow.length - 4} meer</span></div>` : "")
    : `<div class="mini-ev"><time></time><span class="muted">Vrij</span></div>`;
  el.innerHTML = html;
}

function renderCommitment() {
  const c = state.commitment, el = $("#commitment"), tag = $("#commit-state");
  const dots = state.commit_history.map((d, i, a) =>
    `<i class="${d.state} ${i === a.length - 1 ? "today" : ""}" title="${d.date}"></i>`).join("");
  const streak = `
    <div class="streak-row">
      <div class="streak"><span class="flame">🔥</span><b>${state.streak}</b><span>${state.streak === 1 ? "dag" : "dagen"} streak</span></div>
      <div class="dots" title="Laatste 14 dagen">${dots}</div>
    </div>`;
  if (!c) {
    tag.textContent = "nog niet gezet"; tag.className = "tag warn";
    el.innerHTML = `
      <p class="muted small" style="margin:0 0 4px">Eén ding dat je vandaag zéker gaat doen.</p>
      <form class="inline-form" id="commit-form"><input id="commit-input" placeholder="Vandaag ga ik…" autocomplete="off">
      <button class="btn primary" type="submit">Zet</button></form>${streak}`;
    $("#commit-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = $("#commit-input").value.trim();
      if (!text) return;
      await api("/api/commitment", { method: "POST", body: { text } });
      toast("Commitment vastgelegd"); reload();
    });
    return;
  }
  tag.textContent = c.achieved ? "nagekomen" : "open"; tag.className = "tag " + (c.achieved ? "good" : "");
  el.innerHTML = `
    <p class="quote editable ${c.achieved ? "done" : ""}" id="commit-quote" title="Klik om te wijzigen">“${esc(c.commitment)}”</p>
    <button class="commit-btn ${c.achieved ? "done" : ""}" id="commit-toggle">
      ${ICON.check}<span>${c.achieved ? "Nagekomen — goed bezig" : "Markeer als nagekomen"}</span></button>${streak}`;
  $("#commit-quote").addEventListener("click", () => openCommitEdit(c.commitment));
  $("#commit-toggle").addEventListener("click", async () => {
    await api("/api/commitment/toggle", { method: "POST" });
    if (!c.achieved) toast("💪 Commitment nagekomen");
    reload();
  });
}

function urgentie(d) {
  if (d == null) return "#60a5fa";
  if (d < 0) return "#71717a";
  if (d <= 7) return "#f87171";
  if (d <= 14) return "#fb923c";
  if (d <= 30) return "#fbbf24";
  return "#60a5fa";
}
let goalsAll = false;
function renderGoals() {
  const g = state.goals, el = $("#goals");
  $("#goals-count").textContent = `${g.length} actief`;
  if (!g.length) { el.innerHTML = `<div class="empty">Geen actieve doelen.</div>`; return; }
  const shown = goalsAll ? g : g.slice(0, 5);
  el.innerHTML = shown.map((x) => {
    const c = urgentie(x.days_left);
    const dl = x.days_left == null ? "" : x.days_left < 0 ? "verlopen" : x.days_left === 0 ? "vandaag" : `${x.days_left}d`;
    return `<div class="goal" style="--c:${c}" data-id="${esc(x.id)}" title="Klik om te bewerken">
      <div class="goal-top"><span class="goal-title" title="${esc(x.title)}">${esc(x.title)}</span>
        ${dl ? `<span class="days">${dl}</span>` : ""}<span class="goal-pct">${x.progress}%</span></div>
      <div class="bar"><i style="width:0" data-w="${Math.max(2, Math.min(100, x.progress))}%"></i></div>
      ${x.next_milestone ? `<div class="goal-next"><b>Volgende:</b> ${esc(x.next_milestone)} · ${x.milestones_done}/${x.milestones_total}</div>` : ""}
    </div>`;
  }).join("") + `<div class="links-row">
      ${g.length > 5 ? `<button class="more" id="goals-more">${goalsAll ? "Minder tonen" : `Alle ${g.length} doelen tonen →`}</button>` : "<span></span>"}
      ${state.goals_completed ? `<button class="more" id="goals-done">🏆 ${state.goals_completed} behaald</button>` : ""}</div>`;
  requestAnimationFrame(() => $$(".bar > i", el).forEach((b) => (b.style.width = b.dataset.w)));
  $("#goals-more")?.addEventListener("click", () => { goalsAll = !goalsAll; renderGoals(); });
  $("#goals-done")?.addEventListener("click", openCompletedGoals);
  $$(".goal", el).forEach((r) => r.addEventListener("click", () => openGoal(r.dataset.id)));
}

let todoPrio = "medium";
function renderTodos() {
  const t = state.todos, el = $("#todos");
  $("#todos-count").textContent = `${t.length} open`;
  const list = t.length ? t.slice(0, 7).map((x) => `
    <div class="todo" data-id="${esc(x.id)}">
      <button class="check" aria-label="Afvinken">${ICON.check}</button>
      <div class="todo-main"><div class="todo-t">${esc(x.title)}</div>
        ${x.description ? `<div class="todo-d" title="${esc(x.description)}">${esc(x.description)}</div>` : ""}</div>
      <span class="prio ${esc(x.priority)}" title="${esc(x.priority)}"></span>
    </div>`).join("") + (t.length > 7 ? `<div class="empty">+${t.length - 7} meer</div>` : "")
    : `<div class="empty">Alles af. Lekker bezig 🎉</div>`;
  const pick = ["high", "medium", "low"].map((p) =>
    `<button type="button" data-p="${p}" class="${p === todoPrio ? "on" : ""}" title="${p}"><i class="prio ${p}" style="margin:0"></i></button>`).join("");
  el.innerHTML = `${list}
    <form class="todo-add" id="todo-form"><input id="todo-input" placeholder="Nieuwe todo…" autocomplete="off">
      <div class="prio-pick">${pick}</div><button class="btn" type="submit" aria-label="Toevoegen">${ICON.plus}</button></form>`;

  $$(".todo .check", el).forEach((b) => b.addEventListener("click", async () => {
    const row = b.closest(".todo");
    b.classList.add("on"); row.classList.add("leaving");
    await api(`/api/todos/${encodeURIComponent(row.dataset.id)}/toggle`, { method: "POST" });
    toast("✓ " + $(".todo-t", row).textContent);
    setTimeout(reload, 300);
  }));
  $$(".todo-main", el).forEach((m) => m.addEventListener("click", () => {
    const id = m.closest(".todo").dataset.id;
    openTodo(state.todos.find((x) => x.id === id));
  }));
  $$(".prio-pick button", el).forEach((b) => b.addEventListener("click", () => {
    todoPrio = b.dataset.p;
    $$(".prio-pick button", el).forEach((x) => x.classList.toggle("on", x === b));
  }));
  $("#todo-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = $("#todo-input").value.trim();
    if (!title) return;
    await api("/api/todos", { method: "POST", body: { title, priority: todoPrio } });
    reload();
  });
}

function renderBooks() {
  const books = state.books || [], el = $("#books");
  const teLezen = books.filter((b) => !b.gelezen);
  const gelezen = books.filter((b) => b.gelezen);
  $("#books-count").textContent = `${teLezen.length} te lezen`;
  const row = (b) => `<div class="book" data-id="${esc(b.id)}">
      <button class="check ${b.gelezen ? "on" : ""}" aria-label="Gelezen">${ICON.check}</button>
      <div class="book-main"><div class="book-t">${esc(b.titel)}</div>
        ${b.notities ? `<div class="book-n" title="${esc(b.notities)}">${esc(b.notities)}</div>` : ""}</div>
      <button class="x" type="button" aria-label="Verwijderen">${ICON.x}</button></div>`;
  const list = books.length
    ? teLezen.map(row).join("") + (gelezen.length ? `<div class="book-sep">Gelezen — ${gelezen.length}</div>${gelezen.map(row).join("")}` : "")
    : `<div class="empty">Nog geen boeken toegevoegd.</div>`;
  el.innerHTML = `${list}
    <form class="todo-add" id="book-form"><input id="book-input" placeholder="Nieuw boek…" autocomplete="off">
      <button class="btn" type="submit" aria-label="Toevoegen">${ICON.plus}</button></form>`;

  $$(".book .check", el).forEach((b) => b.addEventListener("click", async () => {
    const row = b.closest(".book");
    await api(`/api/books/${encodeURIComponent(row.dataset.id)}/toggle`, { method: "POST" });
    reload();
  }));
  $$(".book-main", el).forEach((m) => m.addEventListener("click", () => {
    const id = m.closest(".book").dataset.id;
    openBook(books.find((x) => x.id === id));
  }));
  $$(".book .x", el).forEach((b) => b.addEventListener("click", async (e) => {
    e.stopPropagation();
    const row = b.closest(".book");
    await api(`/api/books/${encodeURIComponent(row.dataset.id)}`, { method: "DELETE" });
    reload();
  }));
  $("#book-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const titel = $("#book-input").value.trim();
    if (!titel) return;
    await api("/api/books", { method: "POST", body: { titel } });
    reload();
  });
}

function openBook(b) {
  if (!b) return;
  const m = modal({
    title: "Boek bewerken", width: 480, onClose: () => reload(),
    body: `<input class="title-input" id="bk-titel" value="${esc(b.titel)}" maxlength="200">
      <label class="f"><span>Notities</span><textarea id="bk-notities" rows="4" placeholder="Wat nam je mee uit dit boek?">${esc(b.notities || "")}</textarea></label>`,
    foot: `<button class="btn danger" id="bk-del" type="button">Verwijderen</button><span class="spacer"></span>
      <button class="btn primary" id="bk-save" type="button">Opslaan</button>`,
  });
  m.$("#bk-save").addEventListener("click", async () => {
    await api(`/api/books/${encodeURIComponent(b.id)}`, { method: "PATCH", body: { titel: m.$("#bk-titel").value, notities: m.$("#bk-notities").value } });
    toast("Boek opgeslagen"); m.close();
  });
  m.$("#bk-del").addEventListener("click", async () => {
    await api(`/api/books/${encodeURIComponent(b.id)}`, { method: "DELETE" });
    toast("Boek verwijderd"); m.close();
  });
}

function renderPortfolio() {
  const p = state.portfolio, el = $("#portfolio");
  $("#pf-updated").textContent = p.updated;
  const pct = Math.min(100, (p.total / p.goal) * 100);
  const kleuren = { BND: "#a78bfa", Aandelen: "#22d3ee", Vanguard: "#34d399", Goud: "#fbbf24", Bitcoin: "#fb923c" };
  const parts = Object.entries(p.parts).filter(([, v]) => v > 0);
  const tot = parts.reduce((a, [, v]) => a + v, 0) || 1;
  const onSchema = p.projection >= p.goal;
  const hist = p.history || [];
  const delta = hist.length > 1 ? p.total - hist[hist.length - 2].totaal : null;
  el.innerHTML = `
    <div class="big-num">${eur(p.total)}</div>
    ${delta !== null && Math.abs(delta) >= 1 ? `<div class="small" style="margin-top:6px;color:${delta >= 0 ? "var(--good)" : "var(--bad)"}">
      ${delta >= 0 ? "▲" : "▼"} ${eur(Math.abs(delta))} sinds ${esc(hist[hist.length - 2].datum)}</div>` : ""}
    ${sparkline(hist.map((h) => h.totaal))}
    <div class="goal-line"><span>${pct.toFixed(1)}% van doel</span><b>${eur(p.goal)}</b></div>
    <div class="bar" style="--c:#a78bfa;height:6px"><i style="width:0" data-w="${pct}%"></i></div>
    <div class="alloc">${parts.map(([k, v]) => `<i style="width:${(v / tot) * 100}%;background:${kleuren[k]}" title="${k}"></i>`).join("")}</div>
    <div class="alloc-legend">${parts.map(([k, v]) => `<span><i style="background:${kleuren[k]}"></i>${k}<em>${Math.round((v / tot) * 100)}%</em></span>`).join("")}</div>
    <div class="proj">Met <b>${eur(p.monthly)}/mnd</b> inleg: <b style="color:${onSchema ? "var(--good)" : "var(--warn)"}">${eur(p.projection)}</b> in ${esc(p.deadline.slice(0, 4))} ${onSchema ? "— op schema" : "zonder rendement"}</div>`;
  requestAnimationFrame(() => $$(".bar > i", el).forEach((b) => (b.style.width = b.dataset.w)));
}

function sparkline(vals) {
  if (vals.length < 2) return "";
  const W = 260, H = 44, min = Math.min(...vals), max = Math.max(...vals), span = max - min || 1;
  const pts = vals.map((v, i) => [(i / (vals.length - 1)) * W, H - 4 - ((v - min) / span) * (H - 8)]);
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [lx, ly] = pts[pts.length - 1];
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-label="Verloop vermogen">
    <defs><linearGradient id="sparkg" x1="0" x2="1"><stop offset="0" stop-color="#a78bfa"/><stop offset="1" stop-color="#22d3ee"/></linearGradient>
    <linearGradient id="sparka" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#818cf8" stop-opacity=".25"/><stop offset="1" stop-color="#818cf8" stop-opacity="0"/></linearGradient></defs>
    <path class="area" d="${line} L${W},${H} L0,${H} Z"/><path class="line" d="${line}"/><circle cx="${lx}" cy="${ly}" r="3"/></svg>`;
}

function scoreColor(v) {
  if (v == null) return "var(--faint)";
  if (v >= 75) return "var(--good)";
  if (v >= 50) return "var(--warn)";
  return "var(--bad)";
}

const PROFIEL_LABEL = { rustig: "rustdag", gemiddeld: "normale dag", zwaar: "zware trainingsdag", onbekend: "" };

function macroRow(label, val, target, unit = "g") {
  const pct = target ? Math.min(100, (val / target) * 100) : 0;
  return `<div class="macro-row"><span>${label}</span>
    <div class="macro-bar"><i style="width:${pct}%"></i></div>
    <b>${Math.round(val || 0)}<small>/${Math.round(target || 0)}${unit}</small></b></div>`;
}

function renderFood() {
  const c = state.calories, el = $("#food"), t = c.targets || {}, s = c.scores || {};
  const doelKcal = t.kcal ?? c.goal;
  $("#food-goal").textContent = `doel ${doelKcal}`;
  const over = c.total > doelKcal, pct = Math.min(100, (c.total / doelKcal) * 100);
  const items = c.items.map((x, i) => ({ ...x, i })).reverse().slice(0, 5);
  const profielLabel = PROFIEL_LABEL[t.profiel] || "";
  el.innerHTML = `
    <div class="kcal-top"><div class="big-num" style="${over ? "color:var(--bad)" : ""}">${c.total.toLocaleString("nl-NL")}<small> kcal</small></div>
      <span class="muted small">${over ? `${c.total - doelKcal} over` : `${doelKcal - c.total} te gaan`}${profielLabel ? ` · ${profielLabel}` : ""}</span></div>
    <div class="kcal-bar ${over ? "over" : ""}"><i style="width:${pct}%"></i></div>
    <div class="macros">
      ${macroRow("Eiwit", c.eiwit_g, t.eiwit_g)}
      ${macroRow("Koolhydr.", c.koolhydraten_g, t.koolhydraten_g)}
      ${macroRow("Vet", c.vet_g, t.vet_g)}
    </div>
    ${s.micro_score != null ? `<div class="score-chips">
      <button type="button" class="score-chip" id="chip-micro"><span>Micro</span><b style="color:${scoreColor(s.micro_score)}">${s.micro_score}%</b></button>
      <button type="button" class="score-chip" id="chip-whole"><span>Puur</span><b style="color:${scoreColor(s.whole_food_score)}">${s.whole_food_score}%</b></button>
    </div>` : ""}
    <form class="food-form" id="food-form">
      <input id="food-item" placeholder="Wat at je? bv. 2 eieren, havermout, banaan" autocomplete="off">
      <button class="btn" type="submit" aria-label="Loggen met AI">${ICON.plus}</button></form>
    ${items.length ? items.map((x) => `<div class="food-item" data-i="${x.i}"><time>${esc(x.time)}</time><span>${esc(x.item)}</span><b>${x.kcal}</b>
      <button class="x" data-i="${x.i}" aria-label="Verwijderen">${ICON.x}</button></div>`).join("") : `<div class="empty">Nog niets gelogd vandaag.</div>`}`;

  $("#food-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const beschrijving = $("#food-item").value.trim();
    if (!beschrijving) return;
    const btn = $("#food-form button[type=submit]");
    btn.disabled = true; btn.classList.add("spin");
    try {
      state.calories = await api("/api/food/ai", { method: "POST", body: { beschrijving } });
      renderFood(); $("#food-item").focus();
    } catch (err) {
      toast("Voedingsanalyse mislukt: " + err.message, true);
    } finally { btn.disabled = false; btn.classList.remove("spin"); }
  });
  $$(".food-item", el).forEach((row) => row.addEventListener("click", (e) => {
    if (e.target.closest(".x")) return;
    openFoodItem(c.items[parseInt(row.dataset.i, 10)]);
  }));
  $$(".x", el).forEach((b) => b.addEventListener("click", async (e) => {
    e.stopPropagation();
    state.calories = await api(`/api/calories/${b.dataset.i}`, { method: "DELETE" });
    renderFood();
  }));
  if ($("#chip-micro")) $("#chip-micro").addEventListener("click", openVoedingDetail);
  if ($("#chip-whole")) $("#chip-whole").addEventListener("click", openVoedingDetail);
}

function openFoodItem(item) {
  if (!item) return;
  const labels = state.calories.micro_labels || {};
  const micros = item.micros || {};
  const microList = Object.entries(labels)
    .map(([k, label]) => `<div class="macro-row"><span>${esc(label)}</span><b>${fmtNum(micros[k])}</b></div>`).join("");
  const m = modal({
    title: "Maaltijd", width: 480, onClose: () => reload(),
    body: `<div class="title-input" style="font-size:19px;margin-bottom:4px">${esc(item.item)}</div>
      ${item.toelichting ? `<p class="muted small" style="margin-bottom:14px">${esc(item.toelichting)}</p>` : ""}
      <div class="macros">
        <div class="macro-row"><span>Kcal</span><b>${Math.round(item.kcal)}</b></div>
        <div class="macro-row"><span>Eiwit</span><b>${fmtNum(item.eiwit_g)} g</b></div>
        <div class="macro-row"><span>Koolhydraten</span><b>${fmtNum(item.koolhydraten_g)} g</b></div>
        <div class="macro-row"><span>Vet</span><b>${fmtNum(item.vet_g)} g</b></div>
        <div class="macro-row"><span>Vezels</span><b>${fmtNum(item.vezels_g)} g</b></div>
      </div>
      ${item.verwerkt_score != null ? `<div class="hint">Verwerkingsgraad: ${Math.round(item.verwerkt_score * 100)}%</div>` : ""}
      ${microList ? `<h4 class="sub-h">Micronutriënten</h4><div class="macros">${microList}</div>` : ""}`,
    foot: `<button class="btn danger" id="fi-del" type="button">Verwijderen</button>`,
  });
  m.$("#fi-del").addEventListener("click", async () => {
    const idx = state.calories.items.indexOf(item);
    if (idx < 0) return m.close();
    state.calories = await api(`/api/calories/${idx}`, { method: "DELETE" });
    toast("Verwijderd"); m.close();
  });
}

function openVoedingDetail() {
  const c = state.calories, t = c.targets || {}, s = c.scores || {};
  const labels = c.micro_labels || {}, rda = c.micro_rda || {};
  const pct = s.micros_pct || {}, totalen = s.micro_totalen || {};
  const microRows = Object.entries(labels).map(([k, label]) => `
    <div class="macro-row"><span>${esc(label)}</span>
      <div class="macro-bar"><i style="width:${Math.min(100, pct[k] || 0)}%;background:${scoreColor(pct[k])}"></i></div>
      <b>${fmtNum(totalen[k])}<small>/${fmtNum(rda[k])}</small></b></div>`).join("");
  const uitleg = {
    rustig: "Rustige dag qua inspanning — minder koolhydraten nodig, iets meer ruimte voor vet.",
    gemiddeld: "Gemiddelde trainingsdag — gebalanceerde verdeling.",
    zwaar: "Zware trainingsdag (hoge strain) — extra koolhydraten voor herstel en energie.",
    onbekend: "Geen Whoop-data voor vandaag — standaardverdeling gebruikt.",
  }[t.profiel] || "";
  const m = modal({
    title: "Voedingsoverzicht vandaag", width: 560,
    body: `
      <div class="sec"><div class="sec-h"><h4>Dagdoel</h4><span>${t.strain != null ? `strain ${t.strain}` : ""}</span></div>
        <p class="muted small">${esc(uitleg)}</p>
        <div class="macros">
          ${macroRow("Kcal", c.total, t.kcal, "")}
          ${macroRow("Eiwit", c.eiwit_g, t.eiwit_g)}
          ${macroRow("Koolhydraten", c.koolhydraten_g, t.koolhydraten_g)}
          ${macroRow("Vet", c.vet_g, t.vet_g)}
        </div>
      </div>
      <div class="sec"><div class="sec-h"><h4>Micronutriënten</h4><span style="color:${scoreColor(s.micro_score)}">${s.micro_score ?? "–"}%</span></div>
        <div class="macros">${microRows || '<p class="muted small">Nog niets gelogd vandaag.</p>'}</div>
      </div>
      <div class="sec"><div class="sec-h"><h4>Puur vs. bewerkt</h4><span style="color:${scoreColor(s.whole_food_score)}">${s.whole_food_score ?? "–"}%</span></div>
        <p class="muted small">Onbewerkte voeding (groente, fruit, vlees, vis, volkoren) telt onbeperkt mee — alleen
          bewerkte en ultrabewerkte calorieën drukken deze score.</p>
      </div>`,
    foot: `<span class="spacer"></span><button class="btn primary" id="vd-close" type="button">Sluiten</button>`,
  });
  m.$("#vd-close").addEventListener("click", () => m.close());
}

function moodStrip(moods, dagen) {
  const map = Object.fromEntries(moods.map((m) => [m.date, m.mood]));
  const out = [];
  for (let i = dagen - 1; i >= 0; i--) {
    const d = new Date(); d.setDate(d.getDate() - i);
    const k = d.toLocaleDateString("sv-SE");
    out.push({ date: k, mood: map[k], today: i === 0 });
  }
  return out;
}

function renderJournalMini() {
  const j = state.journal, el = $("#journal-mini"), tag = $("#jm-tag");
  const strip = moodStrip(j.moods, 14).map((d) => `<i class="m-${d.mood || "none"}" title="${d.date}"></i>`).join("");
  tag.textContent = j.today_written ? "vandaag geschreven" : "nog niet geschreven";
  tag.className = "tag " + (j.today_written ? "good" : "");
  if (j.latest) {
    const l = j.latest;
    el.innerHTML = `<p class="jm-kern">${esc(l.kern || "—")}</p>
      <div class="pills"><span class="pill ${esc(l.mood)}">mood: ${esc(l.mood)}</span><span class="pill">energie: ${esc(l.energie)}</span>
      ${(l.tags || []).slice(0, 3).map((t) => `<span class="pill">#${esc(t)}</span>`).join("")}</div>
      <div class="mood-strip">${strip}</div>
      <button class="btn sm" style="margin-top:14px" id="jm-go">${j.today_written ? "Aanvullen" : "Schrijf over vandaag"} →</button>`;
  } else {
    el.innerHTML = `<p class="muted small" style="margin:0">Nog geen entries. Twee minuten schrijven per dag laat na een week al patronen zien.</p>
      <div class="mood-strip">${strip}</div><button class="btn sm" style="margin-top:14px" id="jm-go">Eerste entry schrijven →</button>`;
  }
  $("#jm-go").addEventListener("click", () => { setView("journal"); setTimeout(() => $("#journal-text").focus(), 300); });
}

/* ═══ Modals ═════════════════════════════════════════════════════════ */
let openModals = [];

function modal({ title, body, foot = "", width, onClose }) {
  const root = document.createElement("div");
  root.className = "modal-root";
  root.innerHTML = `<div class="modal-scrim"></div>
    <div class="modal" role="dialog" aria-modal="true" ${width ? `style="--mw:${width}px"` : ""}>
      <div class="modal-head"><h3>${title}</h3><button class="icon-btn" data-close title="Sluiten (Esc)">${ICON.x}</button></div>
      <div class="modal-body">${body}</div>
      ${foot ? `<div class="modal-foot">${foot}</div>` : ""}
    </div>`;
  document.body.append(root);
  document.body.style.overflow = "hidden";
  const m = {
    el: root,
    $: (s) => root.querySelector(s),
    $$: (s) => [...root.querySelectorAll(s)],
    close() {
      root.remove();
      openModals = openModals.filter((x) => x !== m);
      if (!openModals.length) document.body.style.overflow = "";
      onClose?.();
    },
  };
  root.querySelector(".modal-scrim").addEventListener("click", () => m.close());
  root.querySelector("[data-close]").addEventListener("click", () => m.close());
  openModals.push(m);
  setTimeout(() => root.querySelector("[autofocus]")?.focus(), 60);
  return m;
}

/* Twee keer klikken om te bevestigen (geen confirm()-popup) */
function confirmClick(btn, label, fn) {
  const orig = btn.innerHTML;
  btn.addEventListener("click", () => {
    if (btn.classList.contains("armed")) return fn();
    btn.classList.add("armed"); btn.textContent = label;
    setTimeout(() => { btn.classList.remove("armed"); btn.innerHTML = orig; }, 3000);
  });
}

/* "2.815,46" / "2815,46" / "2815.46" → 2815.46 */
const num = (v) => {
  let s = String(v ?? "").replace(/[\s€]/g, "");
  if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
  const n = parseFloat(s);
  return isFinite(n) ? n : 0;
};
const fmtNum = (n) => (n == null ? "" : String(Math.round(n * 100) / 100).replace(".", ","));
const fmtAantal = (n) => (n == null ? "" : String(Math.round(n * 1e6) / 1e6).replace(".", ","));
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);

/* ── Doelen ─────────────────────────────────────────────────────────── */
let goalCats = null;
async function categories() {
  if (!goalCats) goalCats = (await api("/api/goals/meta")).categories;
  return goalCats;
}
function catOptions(cur) {
  const all = cur && !goalCats.includes(cur) ? [...goalCats, cur] : goalCats;
  return all.map((c) => `<option value="${esc(c)}" ${c === cur ? "selected" : ""}>${esc(cap(c))}</option>`).join("");
}

async function openGoal(id) {
  const gid = encodeURIComponent(id);
  let g;
  try { [g] = await Promise.all([api(`/api/goals/${gid}`), categories()]); }
  catch (e) { return toast("Doel laden mislukt", true); }

  const m = modal({
    title: "Doel bewerken", width: 680, onClose: () => reload(),
    body: `
      <input class="title-input" id="g-title" value="${esc(g.title)}" maxlength="200" aria-label="Titel">
      <div class="f2">
        <label class="f"><span>Categorie</span><select id="g-cat">${catOptions(g.category)}</select></label>
        <label class="f"><span>Deadline</span><input type="date" id="g-deadline" value="${esc(g.deadline || "")}"></label>
      </div>
      <div class="progress-box">
        <div class="progress-top"><span class="muted small">Voortgang</span><b id="g-pct"></b></div>
        <input type="range" id="g-range" min="0" max="100" step="5" aria-label="Voortgang">
        <div class="checkin-row">
          <input id="g-note" placeholder="Check-in: wat heb je gedaan?" maxlength="2000" autocomplete="off">
          <button class="btn" id="g-checkin" type="button">Check-in</button>
        </div>
        <div class="hint" id="g-hint"></div>
      </div>
      <div class="sec">
        <div class="sec-h"><h4>Mijlpalen</h4><span id="g-ms-count"></span></div>
        <div id="g-ms"></div>
        <form class="ms-add" id="g-ms-form"><input id="g-ms-input" placeholder="Nieuwe mijlpaal…" maxlength="300" autocomplete="off">
          <button class="btn" type="submit" aria-label="Toevoegen">${ICON.plus}</button></form>
      </div>
      <div class="sec"><label class="f"><span>Beschrijving</span><textarea id="g-desc" rows="3" maxlength="3000">${esc(g.description || "")}</textarea></label></div>
      <div class="sec"><div class="sec-h"><h4>Laatste check-ins</h4></div><div id="g-ci"></div></div>`,
    foot: `<button class="btn danger" id="g-archive" type="button">Archiveren</button>
      <button class="btn good" id="g-complete" type="button">🏆 Behaald</button><span class="spacer"></span>
      <button class="btn primary" id="g-save" type="button">Opslaan</button>`,
  });

  const draw = () => {
    m.$("#g-pct").textContent = g.progress + "%";
    const r = m.$("#g-range"); r.value = g.progress; r.style.setProperty("--p", g.progress + "%");
    const done = g.milestones.filter((x) => x.done).length;
    m.$("#g-ms-count").textContent = g.milestones.length ? `${done}/${g.milestones.length}` : "";
    m.$("#g-hint").textContent = g.milestones.length ? "Mijlpalen afvinken zet de voortgang automatisch bij." : "";
    m.$("#g-ms").innerHTML = g.milestones.length
      ? g.milestones.map((x, i) => `<div class="ms ${x.done ? "done" : ""}" data-i="${i}">
          <button class="check ${x.done ? "on" : ""}" aria-label="Afvinken">${ICON.check}</button><span>${esc(x.text)}</span>
          <button class="x" aria-label="Verwijderen">${ICON.x}</button></div>`).join("")
      : `<div class="empty">Nog geen mijlpalen — breek je doel op in concrete stappen.</div>`;
    m.$$(".ms .check").forEach((b) => b.addEventListener("click", async () => {
      g = await api(`/api/goals/${gid}/milestones/${b.closest(".ms").dataset.i}/toggle`, { method: "POST" }); draw();
    }));
    m.$$(".ms .x").forEach((b) => b.addEventListener("click", async () => {
      g = await api(`/api/goals/${gid}/milestones/${b.closest(".ms").dataset.i}`, { method: "DELETE" }); draw();
    }));
    m.$("#g-ci").innerHTML = g.check_ins.length
      ? g.check_ins.map((c) => `<div class="ci"><time>${esc(String(c.date).slice(0, 10))} · <b>${c.progress}%</b></time>${esc(c.note)}</div>`).join("")
      : `<div class="empty">Nog geen check-ins.</div>`;
  };
  draw();

  m.$("#g-range").addEventListener("input", (e) => {
    m.$("#g-pct").textContent = e.target.value + "%";
    e.target.style.setProperty("--p", e.target.value + "%");
  });
  const checkin = async () => {
    const progress = +m.$("#g-range").value, note = m.$("#g-note").value.trim();
    g = await api(`/api/goals/${gid}/checkin`, { method: "POST", body: { progress, note } });
    m.$("#g-note").value = ""; draw(); toast(`Check-in opgeslagen · ${progress}%`);
  };
  m.$("#g-checkin").addEventListener("click", checkin);
  m.$("#g-note").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); checkin(); } });
  m.$("#g-ms-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = m.$("#g-ms-input").value.trim(); if (!text) return;
    g = await api(`/api/goals/${gid}/milestones`, { method: "POST", body: { text } });
    m.$("#g-ms-input").value = ""; draw(); m.$("#g-ms-input").focus();
  });
  m.$("#g-save").addEventListener("click", async () => {
    const title = m.$("#g-title").value.trim();
    if (!title) return toast("Titel mag niet leeg zijn", true);
    const deadline = m.$("#g-deadline").value || null;
    await api(`/api/goals/${gid}`, { method: "PATCH", body: {
      title, description: m.$("#g-desc").value, category: m.$("#g-cat").value, deadline } });
    toast("Doel opgeslagen"); m.close();
  });
  m.$("#g-complete").addEventListener("click", async () => {
    await api(`/api/goals/${gid}`, { method: "PATCH", body: { status: "completed" } });
    toast("🏆 Doel behaald — sterk!"); m.close();
  });
  confirmClick(m.$("#g-archive"), "Zeker weten?", async () => {
    await api(`/api/goals/${gid}`, { method: "PATCH", body: { status: "archived" } });
    toast("Doel gearchiveerd"); m.close();
  });
}

async function openNewGoal() {
  await categories();
  const d = new Date(); d.setMonth(d.getMonth() + 3);
  const m = modal({
    title: "Nieuw doel", width: 600, onClose: () => reload(),
    body: `
      <input class="title-input" id="n-title" placeholder="Wat wil je bereiken?" maxlength="200" autofocus>
      <div class="f2">
        <label class="f"><span>Categorie</span><select id="n-cat">${catOptions("persoonlijk")}</select></label>
        <label class="f"><span>Deadline</span><input type="date" id="n-deadline" value="${d.toLocaleDateString("sv-SE")}"></label>
      </div>
      <label class="f"><span>Waarom / beschrijving</span><textarea id="n-desc" rows="3" maxlength="3000" placeholder="Waarom is dit belangrijk? Hoe meet je het?"></textarea></label>
      <label class="f"><span>Mijlpalen — één per regel</span><textarea id="n-ms" rows="4" placeholder="Eerste stap…&#10;Tweede stap…"></textarea>
        <div class="hint">Voortgang wordt automatisch berekend uit afgevinkte mijlpalen.</div></label>`,
    foot: `<span class="spacer"></span><button class="btn primary" id="n-save" type="button">Doel aanmaken</button>`,
  });
  m.$("#n-save").addEventListener("click", async () => {
    const title = m.$("#n-title").value.trim(), deadline = m.$("#n-deadline").value;
    if (!title) return toast("Geef je doel een titel", true);
    if (!deadline) return toast("Kies een deadline", true);
    await api("/api/goals", { method: "POST", body: {
      title, deadline, category: m.$("#n-cat").value, description: m.$("#n-desc").value,
      milestones: m.$("#n-ms").value.split("\n").map((s) => s.trim()).filter(Boolean) } });
    toast("Doel aangemaakt 🎯"); m.close();
  });
}

async function openCompletedGoals() {
  const [done, archived] = await Promise.all([api("/api/goals?status=completed"), api("/api/goals?status=archived")]);
  const row = (g, label) => `<div class="done-goal" data-id="${esc(g.id)}">
      <div class="t">${esc(g.title)}<small>${esc(cap(g.category || ""))} · ${esc((g.completed_at || g.deadline || "").slice(0, 10))}</small></div>
      <button class="btn sm" data-reopen>${label}</button></div>`;
  const m = modal({
    title: "Behaalde & gearchiveerde doelen", width: 560, onClose: () => reload(),
    body: `<div class="sec"><div class="sec-h"><h4>🏆 Behaald</h4><span>${done.length}</span></div>
        ${done.length ? done.map((g) => row(g, "Heropenen")).join("") : '<div class="empty">Nog niets — komt eraan.</div>'}</div>
      ${archived.length ? `<div class="sec"><div class="sec-h"><h4>Gearchiveerd</h4><span>${archived.length}</span></div>
        ${archived.map((g) => row(g, "Terugzetten")).join("")}</div>` : ""}`,
  });
  m.$$("[data-reopen]").forEach((b) => b.addEventListener("click", async () => {
    const r = b.closest(".done-goal");
    await api(`/api/goals/${encodeURIComponent(r.dataset.id)}`, { method: "PATCH", body: { status: "active" } });
    r.remove(); toast("Doel weer actief");
  }));
}

/* ── Portfolio ──────────────────────────────────────────────────────── */
const INLEG_LABEL = { bnd_maand: "BND per maand", goud_maand: "Goud per maand", aandelen_week: "Aandelen per week", vanguard_week: "Vanguard ETF per week", bitcoin_week: "Bitcoin per week" };

async function openPortfolio() {
  let p;
  try { p = await api("/api/portfolio/raw"); } catch { return toast("Portfolio laden mislukt", true); }
  const h = p.holdings || {};
  const vg = h.vanguard || {};
  const money = (id, v, label) => `<label class="f"><span>${label}</span><div class="euro">
      <input id="${id}" inputmode="decimal" value="${fmtNum(v)}" autocomplete="off"></div></label>`;
  const stockRow = (s = {}) => `<div class="stock">
      <input data-k="ticker" value="${esc(s.ticker || "")}" placeholder="TICK" maxlength="12">
      <input data-k="naam" value="${esc(s.naam || "")}" placeholder="Naam" maxlength="80">
      <input data-k="aantal" inputmode="decimal" value="${fmtAantal(s.aantal)}" placeholder="aantal">
      <div class="euro"><input data-k="waarde" inputmode="decimal" value="${fmtNum(s.waarde)}" placeholder="0"></div>
      <input data-k="rendement_pct" inputmode="decimal" value="${fmtNum(s.rendement_pct)}" placeholder="% rend.">
      <button class="x" type="button" aria-label="Verwijderen">${ICON.x}</button></div>`;
  const inleg = { bnd_maand: 0, goud_maand: 0, aandelen_week: 0, vanguard_week: 0, bitcoin_week: 0, ...(p.inleg || {}) };

  const m = modal({
    title: "Portfolio bijwerken", width: 720, onClose: () => reload(),
    body: `
      <div class="sec"><div class="sec-h"><h4>Waardes</h4><span>laatst: ${esc(p.last_updated || "—")}</span></div>
        ${money("p-bnd", h.bnd?.waarde, "Brand New Day — totaal")}
        <div class="f2">${money("p-goud", h.goud?.waarde, "Goud — huidige waarde")}${money("p-goud-a", h.goud?.aankoopwaarde, "Goud — aankoopwaarde")}</div>
        <div class="f2">${money("p-btc", h.bitcoin?.waarde, "Bitcoin — huidige waarde")}${money("p-btc-a", h.bitcoin?.aankoopwaarde, "Bitcoin — aankoopwaarde")}</div>
      </div>
      <div class="sec"><div class="sec-h"><h4>Losse aandelen</h4><span id="p-st-tot"></span></div>
        <div class="stock-head"><span>Ticker</span><span>Naam</span><span>Aantal</span><span>Waarde</span><span>Rendement</span><span></span></div>
        <div id="p-stocks">${(h.aandelen?.posities || []).map(stockRow).join("")}</div>
        <button class="btn sm" type="button" id="p-add-stock" style="margin-top:6px">${ICON.plus} Aandeel toevoegen</button>
      </div>
      <div class="sec"><div class="sec-h"><h4>Vanguard ETF</h4><span>${esc(vg.ticker || "")}</span></div>
        <div class="f2"><label class="f"><span>Ticker (Yahoo Finance)</span><input id="p-vg-ticker" value="${esc(vg.ticker || "")}" placeholder="VWCE.DE"></label>
          <label class="f"><span>Aantal</span><input id="p-vg-aantal" inputmode="decimal" value="${fmtAantal(vg.aantal)}"></label></div>
        <div class="f2">${money("p-vg", vg.waarde, "Huidige waarde")}${money("p-vg-a", vg.aankoopwaarde, "Aankoopwaarde")}</div>
      </div>
      <div class="sec"><div class="sec-h"><h4>Inleg</h4><span id="p-maand"></span></div>
        <div class="f2">${Object.keys(inleg).map((k) => money("p-in-" + k, inleg[k], INLEG_LABEL[k] || k)).join("")}</div>
      </div>
      <div class="sec"><div class="sec-h"><h4>Doel</h4></div>
        <div class="f2">${money("p-doel", p.doel?.bedrag ?? 25000, "Doelbedrag")}
          <label class="f"><span>Deadline</span><input type="date" id="p-deadline" value="${esc(p.doel?.deadline || "2029-12-31")}"></label></div>
      </div>`,
    foot: `<button class="btn sm" type="button" id="p-ververs">Koersen verversen</button>
      <span class="total-preview">Nieuw totaal<b id="p-total"></b></span><span class="spacer"></span>
      <button class="btn primary" id="p-save" type="button">Opslaan</button>`,
  });

  const stocks = () => m.$$("#p-stocks .stock").map((r) => {
    const o = {}; r.querySelectorAll("[data-k]").forEach((i) => (o[i.dataset.k] = i.value)); return o;
  }).filter((s) => s.ticker.trim() || s.naam.trim());
  const update = () => {
    const st = stocks().reduce((a, s) => a + num(s.waarde), 0);
    const tot = num(m.$("#p-bnd").value) + num(m.$("#p-goud").value) + num(m.$("#p-btc").value) + num(m.$("#p-vg").value) + st;
    m.$("#p-total").textContent = eur(tot);
    m.$("#p-st-tot").textContent = eur(st);
    const maand = Object.keys(inleg).reduce((a, k) => a + num(m.$("#p-in-" + k).value) * (k.endsWith("_week") ? 52 / 12 : 1), 0);
    m.$("#p-maand").textContent = `≈ ${eur(maand)}/maand`;
  };
  const bindRow = (r) => r.querySelector(".x").addEventListener("click", () => { r.remove(); update(); });
  m.$$("#p-stocks .stock").forEach(bindRow);
  m.$("#p-add-stock").addEventListener("click", () => {
    m.$("#p-stocks").insertAdjacentHTML("beforeend", stockRow());
    const r = m.$("#p-stocks").lastElementChild; bindRow(r); r.querySelector("input").focus();
  });
  m.el.addEventListener("input", update);
  update();

  m.$("#p-ververs").addEventListener("click", async () => {
    const b = m.$("#p-ververs"); b.disabled = true; b.textContent = "Koersen ophalen…";
    try {
      await api("/api/portfolio/ververs-koersen", { method: "POST" });
      toast("Koersen ververst 📈"); m.close(); openPortfolio();
    } catch (e) { toast("Verversen mislukt: " + e.message, true); b.disabled = false; b.textContent = "Koersen verversen"; }
  });

  m.$("#p-save").addEventListener("click", async () => {
    const b = m.$("#p-save"); b.disabled = true;
    try {
      state.portfolio = await api("/api/portfolio", { method: "PUT", body: {
        bnd: num(m.$("#p-bnd").value),
        goud: num(m.$("#p-goud").value), goud_aankoop: num(m.$("#p-goud-a").value),
        bitcoin: num(m.$("#p-btc").value), bitcoin_aankoop: num(m.$("#p-btc-a").value),
        vanguard: num(m.$("#p-vg").value), vanguard_aankoop: num(m.$("#p-vg-a").value),
        vanguard_ticker: m.$("#p-vg-ticker").value, vanguard_aantal: num(m.$("#p-vg-aantal").value),
        aandelen: stocks().map((s) => ({ ticker: s.ticker, naam: s.naam, aantal: num(s.aantal), waarde: num(s.waarde), rendement_pct: num(s.rendement_pct) })),
        inleg: Object.fromEntries(Object.keys(inleg).map((k) => [k, num(m.$("#p-in-" + k).value)])),
        doel: { bedrag: num(m.$("#p-doel").value), deadline: m.$("#p-deadline").value },
      } });
      toast("Portfolio bijgewerkt 📈"); m.close();
    } catch (e) { toast("Opslaan mislukt: " + e.message, true); b.disabled = false; }
  });
}

/* ── Todo, caloriedoel, commitment ──────────────────────────────────── */
function openTodo(t) {
  if (!t) return;
  let prio = t.priority || "medium";
  const chips = () => ["high", "medium", "low"].map((p) =>
    `<button type="button" class="chip ${p === prio ? "on" : ""}" data-p="${p}"><i class="prio ${p}" style="margin:0"></i>${{ high: "Hoog", medium: "Middel", low: "Laag" }[p]}</button>`).join("");
  const m = modal({
    title: "Todo bewerken", width: 520, onClose: () => reload(),
    body: `<input class="title-input" id="t-title" value="${esc(t.title)}" maxlength="200">
      <label class="f"><span>Prioriteit</span><div class="prio-choice" id="t-prio">${chips()}</div></label>
      <label class="f"><span>Notitie</span><textarea id="t-desc" rows="4" maxlength="2000">${esc(t.description || "")}</textarea></label>
      <div class="hint">Aangemaakt op ${esc(t.created_at || "?")}</div>`,
    foot: `<button class="btn danger" id="t-del" type="button">Verwijderen</button><span class="spacer"></span>
      <button class="btn primary" id="t-save" type="button">Opslaan</button>`,
  });
  const bindChips = () => m.$$("#t-prio .chip").forEach((c) => c.addEventListener("click", () => {
    prio = c.dataset.p; m.$("#t-prio").innerHTML = chips(); bindChips();
  }));
  bindChips();
  const id = encodeURIComponent(t.id);
  m.$("#t-save").addEventListener("click", async () => {
    await api(`/api/todos/${id}`, { method: "PATCH", body: { title: m.$("#t-title").value, priority: prio, description: m.$("#t-desc").value } });
    toast("Todo opgeslagen"); m.close();
  });
  confirmClick(m.$("#t-del"), "Echt verwijderen?", async () => {
    await api(`/api/todos/${id}`, { method: "DELETE" }); toast("Todo verwijderd"); m.close();
  });
}

function openCalGoal() {
  const m = modal({
    title: "Caloriedoel", width: 380,
    body: `<label class="f"><span>Doel voor vandaag (kcal)</span><input id="c-goal" type="number" min="600" max="8000" step="50" value="${state.calories.goal}" autofocus></label>
      <div class="hint">Geldt vanaf vandaag en blijft staan voor de volgende dagen.</div>`,
    foot: `<span class="spacer"></span><button class="btn primary" id="c-save" type="button">Opslaan</button>`,
  });
  const save = async () => {
    const goal = parseInt(m.$("#c-goal").value, 10);
    if (!(goal > 500 && goal <= 8000)) return toast("Kies een doel tussen 500 en 8000", true);
    state.calories = await api("/api/calories/goal", { method: "PUT", body: { goal } });
    renderFood(); m.close();
  };
  m.$("#c-save").addEventListener("click", save);
  m.$("#c-goal").addEventListener("keydown", (e) => { if (e.key === "Enter") save(); });
}

function openCommitEdit(text) {
  const m = modal({
    title: "Commitment wijzigen", width: 520, onClose: () => reload(),
    body: `<label class="f"><span>Vandaag ga ik…</span><textarea id="cm-text" rows="3" maxlength="500" autofocus>${esc(text)}</textarea></label>
      <div class="hint">Wijzigen zet de status terug op "open".</div>`,
    foot: `<span class="spacer"></span><button class="btn primary" id="cm-save" type="button">Opslaan</button>`,
  });
  m.$("#cm-save").addEventListener("click", async () => {
    const t = m.$("#cm-text").value.trim(); if (!t) return;
    await api("/api/commitment", { method: "POST", body: { text: t } }); toast("Commitment bijgewerkt"); m.close();
  });
}

$("#goal-new").addEventListener("click", openNewGoal);
$("#pf-edit").addEventListener("click", openPortfolio);
$("#food-goal").addEventListener("click", openCalGoal);
$("#food-details").addEventListener("click", openVoedingDetail);

/* ═══ Data laden ═════════════════════════════════════════════════════ */
async function reload(force = false) {
  const btn = $("#refresh");
  btn.classList.add("spin");
  try {
    state = await api(force ? "/api/refresh" : "/api/overview", { method: force ? "POST" : "GET" });
    render();
  } catch (e) {
    toast("Kon data niet laden: " + e.message, true);
  } finally { btn.classList.remove("spin"); }
}
$("#refresh").addEventListener("click", () => reload(true));
$("#logout").addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  location.href = "/login";
});

function skeletons() {
  ["#recovery", "#agenda", "#commitment", "#goals", "#todos", "#portfolio", "#food", "#journal-mini", "#books"].forEach((s) => {
    $(s).innerHTML = '<div class="skeleton" style="width:70%"></div><div class="skeleton"></div><div class="skeleton" style="width:50%"></div>';
  });
}

/* ═══ Board ══════════════════════════════════════════════════════════ */
let boardPick = null;   // null = heel board
let boardBusy = false;

function renderSeats(states = {}) {
  $("#seats").innerHTML = boardAgents.map((a) => {
    const s = states[a.name] || { st: "idle" };
    const label = { idle: "wacht", thinking: "denkt na…", done: "klaar", skipped: "—" }[s.st];
    return `<article class="card seat ${s.st}" data-name="${esc(a.name)}">
      <div class="seat-head"><div class="avatar">${a.emoji}</div>
        <div><div class="seat-name">${esc(a.name)}</div><div class="seat-role">${ROLLEN[a.name] || ""}</div></div>
        <span class="seat-state">${label}</span></div>
      <div class="md">${s.st === "thinking" ? '<span class="typing"><i></i><i></i><i></i></span>' : s.text ? md(s.text) : ""}</div>
    </article>`;
  }).join("");
}

function renderBoardChips() {
  const all = [{ name: null, emoji: "👥", label: "Heel board" }, ...boardAgents.map((a) => ({ ...a, label: a.name }))];
  $("#board-agent-chips").innerHTML = all.map((a) =>
    `<button type="button" class="chip ${a.name === boardPick ? "on" : ""}" data-n="${a.name ?? ""}">${a.emoji} ${esc(a.label)}</button>`).join("");
  $$("#board-agent-chips .chip").forEach((c) => c.addEventListener("click", () => {
    boardPick = c.dataset.n || null; renderBoardChips();
  }));
  $("#seats-mini").innerHTML = boardAgents.map((a) => `<span title="${esc(a.name)}">${a.emoji}</span>`).join("");
}

function renderBoardHistory() {
  const h = loadLS("lifeos.board", []);
  $("#board-history").innerHTML = h.length ? `<h3>Eerdere meetings</h3>` + h.map((m, i) =>
    `<button class="hist-item" data-i="${i}"><span>${esc(m.question)}</span><time>${esc(m.when)}</time></button>`).join("") : "";
  $$(".hist-item").forEach((b) => b.addEventListener("click", () => {
    const m = h[+b.dataset.i];
    $("#board-question").value = m.question;
    const st = {};
    boardAgents.forEach((a) => (st[a.name] = m.answers[a.name] ? { st: "done", text: m.answers[a.name] } : { st: "skipped" }));
    renderSeats(st);
    $("#consensus").hidden = !m.consensus;
    $("#consensus-text").innerHTML = m.consensus ? md(m.consensus) : "";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }));
}

async function runBoard(question) {
  if (boardBusy || question.length < 3) return;
  boardBusy = true;
  const btn = $("#board-submit");
  btn.disabled = true; btn.querySelector("span").textContent = "Meeting loopt…";
  const st = {};
  boardAgents.forEach((a) => (st[a.name] = { st: boardPick && boardPick !== a.name ? "skipped" : "idle" }));
  renderSeats(st);
  $("#consensus").hidden = true;
  const answers = {}; let consensus = "";
  try {
    const res = await fetch("/api/board", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, agent: boardPick }),
    });
    checkAuth(res);
    if (!res.ok) throw new Error(await res.text());
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl); buf = buf.slice(nl + 1);
        if (!line.trim()) continue;
        const ev = JSON.parse(line);
        if (ev.type === "thinking" && st[ev.name]) {
          st[ev.name] = { st: "thinking" }; renderSeats(st);
          $(`.seat[data-name="${CSS.escape(ev.name)}"]`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } else if (ev.type === "thinking" && ev.name === "Voorzitter") {
          $("#consensus").hidden = false;
          $("#consensus-text").innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
          $("#consensus").scrollIntoView({ behavior: "smooth", block: "nearest" });
        } else if (ev.type === "agent") {
          st[ev.name] = { st: "done", text: ev.text }; answers[ev.name] = ev.text; renderSeats(st);
        } else if (ev.type === "consensus") {
          consensus = ev.text; $("#consensus-text").innerHTML = md(ev.text);
        } else if (ev.type === "error") toast(ev.text, true);
      }
    }
    const h = loadLS("lifeos.board", []);
    h.unshift({ question, answers, consensus, when: new Date().toLocaleString("nl-NL", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) });
    saveLS("lifeos.board", h.slice(0, 8));
    renderBoardHistory();
  } catch (e) {
    toast("Board meeting mislukt: " + e.message, true);
  } finally {
    boardBusy = false; btn.disabled = false; btn.querySelector("span").textContent = "Start meeting";
  }
}

$("#board-form").addEventListener("submit", (e) => { e.preventDefault(); runBoard($("#board-question").value.trim()); });
$("#board-question").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); runBoard($("#board-question").value.trim()); }
});
$("#board-mini-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $("#board-mini-input").value.trim();
  if (q.length < 3) return;
  $("#board-question").value = q; $("#board-mini-input").value = "";
  boardPick = null; renderBoardChips();
  setView("board"); runBoard(q);
});

/* ═══ Journal ════════════════════════════════════════════════════════ */
const jt = $("#journal-text");
jt.value = loadLS("lifeos.journalDraft", "");
const countWords = () => {
  const n = jt.value.trim() ? jt.value.trim().split(/\s+/).length : 0;
  $("#journal-count").textContent = `${n} ${n === 1 ? "woord" : "woorden"}`;
};
jt.addEventListener("input", () => { countWords(); saveLS("lifeos.journalDraft", jt.value); });
countWords();

async function loadJournal() {
  let entries = [];
  try { entries = await api("/api/journal"); } catch (e) { return toast("Journal laden mislukt", true); }
  const cells = moodStrip(entries.map((e) => ({ date: e.date, mood: e.mood })), 30);
  $("#mood-grid").innerHTML = cells.map((d) => `<i class="m-${d.mood || "none"} ${d.today ? "today" : ""}" title="${d.date}${d.mood ? " · " + d.mood : ""}"></i>`).join("");
  $("#mood-count").textContent = `${entries.filter((e) => e.date >= cells[0].date).length} entries`;
  const kleur = { goed: "var(--good)", matig: "var(--warn)", slecht: "var(--bad)" };
  $("#journal-list").innerHTML = entries.length ? entries.slice(0, 12).map((e) => `
    <div class="entry"><div class="entry-top"><i style="background:${kleur[e.mood] || "var(--faint)"}"></i>${esc(e.date)} · energie ${esc(e.energie)}</div>
      <p>${esc(e.kern || "")}</p><div class="raw">${esc(e.raw || "")}</div></div>`).join("")
    : `<div class="empty">Nog geen entries.</div>`;
  $$(".entry").forEach((x) => x.addEventListener("click", () => x.classList.toggle("open")));
  const today = entries.find((e) => e.date === new Date().toLocaleDateString("sv-SE"));
  if (today) showAnalysis(today);
}

function showAnalysis(e) {
  $("#journal-analysis").hidden = false;
  $("#ja-tag").textContent = e.date;
  const list = (xs) => (xs && xs.length ? xs.map((x) => `<li>${esc(x)}</li>`).join("") : '<li class="muted">—</li>');
  $("#journal-analysis-body").innerHTML = `
    <p class="quote" style="margin-bottom:12px">“${esc(e.kern || "")}”</p>
    <div class="pills"><span class="pill ${esc(e.mood)}">mood: ${esc(e.mood)}</span><span class="pill">energie: ${esc(e.energie)}</span>
      ${(e.tags || []).map((t) => `<span class="pill">#${esc(t)}</span>`).join("")}</div>
    <div class="an-grid"><div class="an-col wins"><h4>Wins</h4><ul>${list(e.wins)}</ul></div>
      <div class="an-col blockers"><h4>Blockers</h4><ul>${list(e.blockers)}</ul></div></div>`;
}

$("#journal-save").addEventListener("click", async () => {
  const text = jt.value.trim();
  if (text.length < 10) return toast("Schrijf eerst wat meer", true);
  const b = $("#journal-save"); b.disabled = true; b.textContent = "Analyseren…";
  try {
    const entry = await api("/api/journal", { method: "POST", body: { text } });
    jt.value = ""; saveLS("lifeos.journalDraft", ""); countWords();
    $("#followup").hidden = true;
    showAnalysis(entry); toast("Journal opgeslagen"); loadJournal(); reload();
  } catch (e) { toast("Opslaan mislukt: " + e.message, true); }
  finally { b.disabled = false; b.textContent = "Opslaan & analyseren"; }
});

$("#journal-ask").addEventListener("click", async () => {
  const text = jt.value.trim();
  if (text.length < 10) return toast("Schrijf eerst een paar zinnen", true);
  const b = $("#journal-ask"); b.disabled = true;
  try {
    const { question } = await api("/api/journal/question", { method: "POST", body: { text } });
    $("#followup").hidden = false; $("#followup").textContent = question;
    jt.value += "\n\n"; jt.focus(); jt.setSelectionRange(jt.value.length, jt.value.length);
  } catch (e) { toast("Kon geen vraag ophalen", true); }
  finally { b.disabled = false; }
});

$("#patterns-btn").addEventListener("click", async () => {
  const b = $("#patterns-btn"); b.disabled = true; b.textContent = "Analyseren…";
  $("#patterns").innerHTML = '<div class="skeleton"></div><div class="skeleton" style="width:80%"></div><div class="skeleton" style="width:60%"></div>';
  try {
    const r = await api("/api/journal/patterns", { method: "POST" });
    $("#patterns").innerHTML = md(r.text);
  } catch (e) { $("#patterns").innerHTML = `<p class="muted small">Analyse mislukt.</p>`; }
  finally { b.disabled = false; b.textContent = "Analyseer 14 dagen"; }
});

/* ═══ Chat ═══════════════════════════════════════════════════════════ */
const SUGGESTIES = [
  ["🌅 Briefing", () => `Geef me mijn ${new Date().getHours() < 17 ? "ochtend" : "avond"}briefing: herstel en wat dat betekent, agenda, de 3 belangrijkste focuspunten en aankomende deadlines.`],
  ["🎯 Focus", () => "Wat zijn de 3 belangrijkste dingen die ik vandaag moet doen, op basis van mijn doelen, todo's en agenda? Geef een concrete volgorde."],
  ["💪 Training", () => "Geef een concreet trainingsadvies voor vandaag op basis van mijn Whoop-herstel en mijn agenda."],
  ["📈 Doelen", () => "Welke doelen lopen achter en wat moet ik de komende week prioriteren?"],
];
let chatBusy = false;

function openChat() {
  $("#drawer").classList.add("open"); $("#drawer").setAttribute("aria-hidden", "false");
  $("#scrim").hidden = false; renderChat();
  setTimeout(() => $("#chat-input").focus(), 250);
}
function closeChat() {
  $("#drawer").classList.remove("open"); $("#drawer").setAttribute("aria-hidden", "true");
  $("#scrim").hidden = true;
}
$("#open-chat").addEventListener("click", openChat);
$("#close-chat").addEventListener("click", closeChat);
$("#scrim").addEventListener("click", closeChat);
$("#chat-clear").addEventListener("click", () => { if (chatBusy) return; chat = []; saveLS("lifeos.chat", chat); renderChat(); });

function renderChat() {
  const box = $("#messages");
  box.innerHTML = chat.length ? chat.map((m) => m.role === "user"
    ? `<div class="msg user">${esc(m.label || m.content)}</div>`
    : `<div class="msg assistant"><div class="msg-who"><i></i>LIFE OS</div><div class="md">${md(m.content)}</div></div>`).join("")
    : `<div class="chat-empty"><div class="orb"></div><b>Waar kan ik mee helpen?</b>Ik zie je herstel, agenda, doelen, todo's, portfolio en journal.</div>`;
  $("#suggestions").innerHTML = SUGGESTIES.map(([l], i) => `<button class="chip" data-i="${i}">${l}</button>`).join("");
  $$("#suggestions .chip").forEach((c) => c.addEventListener("click", () => {
    const [label, prompt] = SUGGESTIES[+c.dataset.i]; sendChat(prompt(), label);
  }));
  box.scrollTop = box.scrollHeight;
}

async function sendChat(content, label) {
  if (chatBusy || !content.trim()) return;
  chatBusy = true; $(".send").disabled = true;
  chat.push({ role: "user", content, ...(label ? { label } : {}) });
  renderChat();
  const box = $("#messages");
  const wrap = document.createElement("div");
  wrap.className = "msg assistant";
  wrap.innerHTML = `<div class="msg-who"><i></i>LIFE OS</div><div class="md caret"></div>`;
  box.append(wrap); box.scrollTop = box.scrollHeight;
  const out = $(".md", wrap);
  let text = "";
  try {
    const res = await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: chat.map(({ role, content }) => ({ role, content })) }),
    });
    checkAuth(res);
    if (!res.ok) throw new Error(await res.text());
    const reader = res.body.getReader(), dec = new TextDecoder();
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      text += dec.decode(value, { stream: true });
      out.innerHTML = md(text);
      const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 120;
      if (nearBottom) box.scrollTop = box.scrollHeight;
    }
  } catch (e) {
    text = text || `⚠️ ${e.message}`;
  }
  out.classList.remove("caret"); out.innerHTML = md(text);
  chat.push({ role: "assistant", content: text || "…" });
  saveLS("lifeos.chat", chat.slice(-40));
  chatBusy = false; $(".send").disabled = false;
}

const ci = $("#chat-input");
ci.addEventListener("input", () => { ci.style.height = "auto"; ci.style.height = Math.min(160, ci.scrollHeight) + "px"; });
ci.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#composer").requestSubmit(); }
});
$("#composer").addEventListener("submit", (e) => {
  e.preventDefault();
  const v = ci.value.trim(); if (!v) return;
  ci.value = ""; ci.style.height = "auto"; sendChat(v);
});

/* ── sneltoetsen ───────────────────────────────────────────────────── */
document.addEventListener("keydown", (e) => {
  if (openModals.length) {   // eerst het bovenste venster afhandelen
    if (e.key === "Escape") { e.preventDefault(); openModals[openModals.length - 1].close(); }
    return;
  }
  const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName);
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); $("#drawer").classList.contains("open") ? closeChat() : openChat(); }
  else if (e.key === "Escape" && $("#drawer").classList.contains("open")) closeChat();
  else if (!typing && !e.metaKey && !e.ctrlKey) {
    if (e.key === "1") setView("vandaag");
    else if (e.key === "2") setView("board");
    else if (e.key === "3") setView("journal");
    else if (e.key.toLowerCase() === "r") reload(true);
  }
});

/* ── start ─────────────────────────────────────────────────────────── */
(async function init() {
  skeletons();
  const start = (location.hash || "#vandaag").slice(1);
  if (["vandaag", "board", "journal"].includes(start)) setView(start);
  requestAnimationFrame(moveGlider);
  document.fonts?.ready.then(moveGlider);
  try { boardAgents = await api("/api/board/agents"); } catch { boardAgents = []; }
  renderBoardChips(); renderSeats(); renderBoardHistory();
  await reload();
  setInterval(() => { if (!document.hidden && !openModals.length) reload(); }, 5 * 60_000);

  // Snelkoppelingen: /?open=portfolio | nieuw-doel | doel:<id> | chat
  const open = new URLSearchParams(location.search).get("open");
  if (open) {
    history.replaceState(null, "", location.pathname + location.hash);
    if (open === "portfolio") openPortfolio();
    else if (open === "nieuw-doel") openNewGoal();
    else if (open === "chat") openChat();
    else if (open.startsWith("doel:")) openGoal(open.slice(5));
    else if (open === "eerste-doel" && state?.goals[0]) openGoal(state.goals[0].id);
  }
})();
