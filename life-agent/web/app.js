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

  renderRecovery(); renderAgenda(); renderCommitment(); renderGoals();
  renderTodos(); renderPortfolio(); renderFood(); renderJournalMini();
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
    <p class="quote ${c.achieved ? "done" : ""}">“${esc(c.commitment)}”</p>
    <button class="commit-btn ${c.achieved ? "done" : ""}" id="commit-toggle">
      ${ICON.check}<span>${c.achieved ? "Nagekomen — goed bezig" : "Markeer als nagekomen"}</span></button>${streak}`;
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
    return `<div class="goal" style="--c:${c}">
      <div class="goal-top"><span class="goal-title" title="${esc(x.title)}">${esc(x.title)}</span>
        ${dl ? `<span class="days">${dl}</span>` : ""}<span class="goal-pct">${x.progress}%</span></div>
      <div class="bar"><i style="width:0" data-w="${Math.max(2, Math.min(100, x.progress))}%"></i></div>
      ${x.next_milestone ? `<div class="goal-next"><b>Volgende:</b> ${esc(x.next_milestone)} · ${x.milestones_done}/${x.milestones_total}</div>` : ""}
    </div>`;
  }).join("") + (g.length > 5 ? `<button class="more" id="goals-more">${goalsAll ? "Minder tonen" : `Alle ${g.length} doelen tonen →`}</button>` : "");
  requestAnimationFrame(() => $$(".bar > i", el).forEach((b) => (b.style.width = b.dataset.w)));
  $("#goals-more")?.addEventListener("click", () => { goalsAll = !goalsAll; renderGoals(); });
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

function renderPortfolio() {
  const p = state.portfolio, el = $("#portfolio");
  $("#pf-updated").textContent = p.updated;
  const pct = Math.min(100, (p.total / p.goal) * 100);
  const kleuren = { BND: "#a78bfa", Aandelen: "#22d3ee", Goud: "#fbbf24", Bitcoin: "#fb923c" };
  const parts = Object.entries(p.parts).filter(([, v]) => v > 0);
  const tot = parts.reduce((a, [, v]) => a + v, 0) || 1;
  const onSchema = p.projection >= p.goal;
  el.innerHTML = `
    <div class="big-num">${eur(p.total)}</div>
    <div class="goal-line"><span>${pct.toFixed(1)}% van doel</span><b>${eur(p.goal)}</b></div>
    <div class="bar" style="--c:#a78bfa;height:6px"><i style="width:0" data-w="${pct}%"></i></div>
    <div class="alloc">${parts.map(([k, v]) => `<i style="width:${(v / tot) * 100}%;background:${kleuren[k]}" title="${k}"></i>`).join("")}</div>
    <div class="alloc-legend">${parts.map(([k, v]) => `<span><i style="background:${kleuren[k]}"></i>${k}<em>${Math.round((v / tot) * 100)}%</em></span>`).join("")}</div>
    <div class="proj">Met <b>${eur(p.monthly)}/mnd</b> inleg: <b style="color:${onSchema ? "var(--good)" : "var(--warn)"}">${eur(p.projection)}</b> in ${esc(p.deadline.slice(0, 4))} ${onSchema ? "— op schema" : "zonder rendement"}</div>`;
  requestAnimationFrame(() => $$(".bar > i", el).forEach((b) => (b.style.width = b.dataset.w)));
}

function renderFood() {
  const c = state.calories, el = $("#food");
  $("#food-goal").textContent = `doel ${c.goal}`;
  const over = c.total > c.goal, pct = Math.min(100, (c.total / c.goal) * 100);
  const items = c.items.map((x, i) => ({ ...x, i })).reverse().slice(0, 5);
  el.innerHTML = `
    <div class="kcal-top"><div class="big-num" style="${over ? "color:var(--bad)" : ""}">${c.total.toLocaleString("nl-NL")}<small> kcal</small></div>
      <span class="muted small">${over ? `${c.total - c.goal} over` : `${c.goal - c.total} te gaan`}</span></div>
    <div class="kcal-bar ${over ? "over" : ""}"><i style="width:${pct}%"></i></div>
    <form class="food-form" id="food-form">
      <input id="food-item" placeholder="Wat at je?" autocomplete="off">
      <input id="food-kcal" type="number" min="1" max="5000" placeholder="kcal">
      <button class="btn" type="submit" aria-label="Toevoegen">${ICON.plus}</button></form>
    ${items.length ? items.map((x) => `<div class="food-item"><time>${esc(x.time)}</time><span>${esc(x.item)}</span><b>${x.kcal}</b>
      <button class="x" data-i="${x.i}" aria-label="Verwijderen">${ICON.x}</button></div>`).join("") : `<div class="empty">Nog niets gelogd vandaag.</div>`}`;
  $("#food-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const item = $("#food-item").value.trim(), kcal = parseInt($("#food-kcal").value, 10);
    if (!item || !(kcal > 0)) return toast("Vul een omschrijving en kcal in", true);
    state.calories = await api("/api/calories", { method: "POST", body: { item, kcal } });
    renderFood(); $("#food-item").focus();
  });
  $$(".x", el).forEach((b) => b.addEventListener("click", async () => {
    state.calories = await api(`/api/calories/${b.dataset.i}`, { method: "DELETE" });
    renderFood();
  }));
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
  ["#recovery", "#agenda", "#commitment", "#goals", "#todos", "#portfolio", "#food", "#journal-mini"].forEach((s) => {
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
  setInterval(() => { if (!document.hidden) reload(); }, 5 * 60_000);
})();
