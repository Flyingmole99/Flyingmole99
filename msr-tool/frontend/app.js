"use strict";

const state = { projektId: null, anlageId: null };
const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------- helpers
async function api(method, path, body) {
  const opt = { method, headers: {} };
  if (body !== undefined) {
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  const res = await fetch(path, opt);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.status === 204 ? null : res.json();
}

let statusTimer;
function toast(msg, isErr = false) {
  const el = $("status");
  el.textContent = msg;
  el.className = "status show" + (isErr ? " err" : "");
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => (el.className = "status"), 3200);
}

// ---------------------------------------------------------------- Projekte
async function loadProjekte(selectId) {
  const list = await api("GET", "/projekte");
  const sel = $("projektSelect");
  sel.innerHTML = "";
  if (!list.length) {
    sel.innerHTML = '<option value="">– kein Projekt –</option>';
    state.projektId = null;
    await onProjektChange();
    return;
  }
  for (const p of list) {
    const o = document.createElement("option");
    o.value = p.id;
    o.textContent = `${p.name}${p.kunde ? " · " + p.kunde : ""}`;
    sel.appendChild(o);
  }
  sel.value = selectId || list[0].id;
  await onProjektChange();
}

async function createProjekt() {
  const name = "Projekt " + new Date().toLocaleTimeString("de-DE");
  const p = await api("POST", "/projekte", { name });
  toast(`Projekt „${name}“ angelegt`);
  await loadProjekte(p.id);
}

async function onProjektChange() {
  state.projektId = $("projektSelect").value ? Number($("projektSelect").value) : null;
  await loadAnlagen();
}

// ---------------------------------------------------------------- Anlagen
async function loadAnlagen(selectId) {
  const sel = $("anlageSelect");
  sel.innerHTML = "";
  if (!state.projektId) { sel.innerHTML = '<option value="">–</option>'; return onAnlageChange(); }
  const proj = await api("GET", `/projekte/${state.projektId}`);
  if (!proj.anlagen.length) {
    sel.innerHTML = '<option value="">– keine Anlage –</option>';
    return onAnlageChange();
  }
  for (const a of proj.anlagen) {
    const o = document.createElement("option");
    o.value = a.id; o.textContent = a.bas;
    sel.appendChild(o);
  }
  sel.value = selectId || proj.anlagen[0].id;
  await onAnlageChange();
}

async function createAnlage(ev) {
  ev.preventDefault();
  if (!state.projektId) { toast("Erst ein Projekt anlegen", true); return; }
  const body = {
    gewerk_kg: $("aGewerk").value.trim(),
    anlage_kuerzel: $("aKuerzel").value.trim(),
    nummer: Number($("aNummer").value) || 1,
  };
  try {
    const a = await api("POST", `/projekte/${state.projektId}/anlagen`, body);
    toast(`Anlage ${a.bas} angelegt`);
    await loadAnlagen(a.id);
  } catch (e) { toast(e.message, true); }
}

async function onAnlageChange() {
  const v = $("anlageSelect").value;
  state.anlageId = v ? Number(v) : null;
  await refreshAnlage();
}

// ---------------------------------------------------------------- Palette
async function loadPalette() {
  const q = $("paletteSuche").value.trim();
  const path = "/catalog/aggregate-templates?typ=Baugruppe&limit=150"
    + (q ? "&q=" + encodeURIComponent(q) : "");
  const items = await api("GET", path);
  const ul = $("paletteListe");
  ul.innerHTML = "";
  for (const t of items) {
    const li = document.createElement("li");
    li.draggable = true;
    li.dataset.uuid = t.uuid;
    li.innerHTML = `
      <span class="pl-main">
        <span class="pl-kennung">${t.kennung}</span>
        <span class="pl-bez" title="${t.bezeichnung || ""}">${t.bezeichnung || ""}</span>
      </span>
      <span class="gewerk">${t.gewerk_kg || ""}</span>
      <button class="add-btn" title="hinzufügen">+</button>`;
    li.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/template-uuid", t.uuid);
      e.dataTransfer.effectAllowed = "copy";
      li.classList.add("dragging");
    });
    li.addEventListener("dragend", () => li.classList.remove("dragging"));
    li.querySelector(".add-btn").addEventListener("click", () => addBaugruppe(t.uuid));
    ul.appendChild(li);
  }
}

// ---------------------------------------------------------------- Baugruppen (Drag & Drop)
async function addBaugruppe(uuid) {
  if (!state.anlageId) { toast("Erst eine Anlage wählen/anlegen", true); return; }
  try {
    const r = await api("POST", `/anlagen/${state.anlageId}/baugruppen`,
      { aggregat_template_uuid: uuid });
    const s = r.instanziierung;
    toast(`${r.bas}: ${s.datenpunkte} Datenpunkte (${s.hardware} Hardware) instanziiert`);
    await refreshAnlage();
  } catch (e) { toast(e.message, true); }
}

async function removeBaugruppe(id) {
  await api("DELETE", `/baugruppen/${id}`);
  toast("Baugruppe entfernt");
  await refreshAnlage();
}

// ---------------------------------------------------------------- Rendering
async function refreshAnlage() {
  const dzTitel = $("dzTitel"), dzHint = $("dzHint");
  const bgListe = $("baugruppenListe");
  const tbody = $("dpTabelle").querySelector("tbody");
  bgListe.innerHTML = ""; tbody.innerHTML = "";
  $("dpCount").textContent = "0"; $("dpStats").innerHTML = "";

  if (!state.anlageId) {
    dzTitel.textContent = "Keine Anlage gewählt";
    dzHint.textContent = "Lege oben eine Anlage an, dann ziehe eine Baugruppe hierher.";
    $("dlDatenpunkte").removeAttribute("href");
    $("dlKabel").removeAttribute("href");
    return;
  }
  const anlage = await api("GET", `/anlagen/${state.anlageId}`);
  dzTitel.textContent = "Anlage " + anlage.bas;
  dzHint.textContent = anlage.baugruppen.length
    ? "Ziehe weitere Baugruppen hierher."
    : "Ziehe eine Baugruppe aus der Palette hierher (oder klicke „+“).";

  for (const b of anlage.baugruppen) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="bg-bas">${b.bas}</span>
      <span class="bg-dp">${b.template} · ${b.datenpunkte} DP</span>
      <button class="rm" title="entfernen">×</button>`;
    li.querySelector(".rm").addEventListener("click", () => removeBaugruppe(b.id));
    bgListe.appendChild(li);
  }

  const dps = await api("GET", `/anlagen/${state.anlageId}/datenpunkte`);
  $("dpCount").textContent = dps.length;
  const hw = dps.filter((d) => d.hardware).length;
  const tr = dps.filter((d) => d.trend).length;
  const al = dps.filter((d) => d.alarm).length;
  $("dpStats").innerHTML =
    `<span><b>${hw}</b> Hardware-I/O</span><span><b>${dps.length - hw}</b> Software</span>` +
    `<span><b>${tr}</b> Trend</span><span><b>${al}</b> Alarm</span>`;

  for (const d of dps) {
    const trEl = document.createElement("tr");
    trEl.innerHTML = `
      <td class="mono">${d.bas}</td>
      <td>${d.object_type}</td>
      <td>${d.bezeichnung || ""}</td>
      <td>${d.units || ""}</td>
      <td class="${d.hardware ? "tag-hw" : "tag-sw"}">${d.hardware ? "HW" : "sw"}</td>
      <td>${d.trend ? "•" : ""}</td>
      <td>${d.alarm ? "•" : ""}</td>`;
    tbody.appendChild(trEl);
  }

  $("dlDatenpunkte").href = `/anlagen/${state.anlageId}/dokumente/datenpunktliste`;
  $("dlKabel").href = `/anlagen/${state.anlageId}/dokumente/kabelzugliste`;
}

// ---------------------------------------------------------------- DnD dropzone
function wireDropzone() {
  const dz = $("dropzone");
  dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("over"); });
  dz.addEventListener("dragleave", () => dz.classList.remove("over"));
  dz.addEventListener("drop", (e) => {
    e.preventDefault(); dz.classList.remove("over");
    const uuid = e.dataTransfer.getData("text/template-uuid");
    if (uuid) addBaugruppe(uuid);
  });
}

// ---------------------------------------------------------------- init
function init() {
  $("neuesProjekt").addEventListener("click", () => createProjekt().catch((e) => toast(e.message, true)));
  $("projektSelect").addEventListener("change", () => onProjektChange().catch((e) => toast(e.message, true)));
  $("anlageSelect").addEventListener("change", () => onAnlageChange().catch((e) => toast(e.message, true)));
  $("anlageForm").addEventListener("submit", createAnlage);
  let deb;
  $("paletteSuche").addEventListener("input", () => { clearTimeout(deb); deb = setTimeout(() => loadPalette().catch(() => {}), 200); });
  wireDropzone();
  Promise.all([loadPalette(), loadProjekte()]).catch((e) => toast(e.message, true));
}
document.addEventListener("DOMContentLoaded", init);
