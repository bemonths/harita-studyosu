// Seçili sahnenin ayar formu: sahne şemasından otomatik kurulur.
import { h } from "./dom.js";
import { priceTable } from "./pricetable.js";
import { currentScene, currentSchema, geoFor, sceneErrors, setParam, store } from "./state.js";

const GROUP_ORDER = ["Genel", "Veri", "Renkler", "County boyama", "Vurgu", "Kamera", "Zaman"];
const CLOSED = new Set(["Kamera"]);
let token = 0;

export function assignText(value) {
  return `${Object.keys(value || {}).length} county boyandı. Düzenlemek için sağdaki "County boyama" panelini kullanın.`;
}

export async function renderForm(root) {
  const my = ++token;
  const scene = currentScene(), schema = currentSchema();
  document.getElementById("form-title").textContent = schema ? `Ayarlar · ${schema.title}` : "Ayarlar";
  if (!scene) { root.innerHTML = ""; return; }
  const groups = new Map();
  for (const p of schema.params) {
    if (!groups.has(p.group)) groups.set(p.group, []);
    groups.get(p.group).push(p);
  }
  const rank = g => (GROUP_ORDER.indexOf(g) + 1) || 99;
  const frag = document.createDocumentFragment();
  for (const g of [...groups.keys()].sort((a, b) => rank(a) - rank(b))) {
    const det = h("details", { class: "group", open: !CLOSED.has(g) }, h("summary", {}, g));
    for (const p of groups.get(g)) det.append(await field(p, scene));
    frag.append(det);
  }
  if (my !== token) return; // bu arada yeni bir çizim başladı
  root.innerHTML = "";
  root.append(frag);
  showErrors();
}

export function showErrors() {
  const errs = sceneErrors(store.selected);
  for (const el of document.querySelectorAll("#form .field")) {
    const e = errs.find(x => x.param === el.dataset.param);
    el.querySelector(".err").textContent = e ? e.message : "";
  }
}

async function field(p, scene) {
  const id = `f-${p.name}`;
  return h("div", { class: "field", dataset: { param: p.name } },
    h("label", { htmlFor: id }, p.label),
    await control(p, scene.params[p.name], scene, id),
    p.help ? h("div", { class: "help" }, p.help) : null,
    h("div", { class: "err" }));
}

async function control(p, value, scene, id) {
  const set = v => setParam(p.name, v);
  switch (p.kind) {
    case "text":
      return p.multiline
        ? h("textarea", { id, rows: 2, value: value ?? "", placeholder: p.auto ? "otomatik" : "", oninput: e => set(e.target.value) })
        : h("input", { type: "text", id, value: value ?? "", maxLength: p.max_len, placeholder: p.auto ? "otomatik" : "",
            oninput: e => set(e.target.value) });
    case "color":
      return h("input", { type: "color", id, value, oninput: e => set(e.target.value) });
    case "number": {
      const el = h("input", { type: "number", id, step: p.step ?? "any", value: value ?? "",
        oninput: e => set(e.target.value === "" ? (p.optional ? null : "") : Number(e.target.value)) });
      if (p.min != null) el.min = p.min;
      if (p.max != null) el.max = p.max;
      return el;
    }
    case "date":
      return h("input", { type: "date", id, value, onchange: e => set(e.target.value) });
    case "state":
      return stateSelect(p, value, id);
    case "county":
      return countySelect(p, value, scene, id);
    case "categories":
      return categoriesEditor(p, value);
    case "county_assign":
      return h("div", { class: "help", id, dataset: { assignSummary: p.name } }, assignText(value));
    case "price_table":
      return priceTable(value, rows => set(rows));
    default:
      return h("div", { class: "err" }, `Desteklenmeyen ayar tipi: ${p.kind}`);
  }
}

function stateSelect(p, value, id) {
  const sel = h("select", { id });
  for (const o of p.options) sel.add(new Option(o.label, o.value, false, o.value === value));
  sel.addEventListener("change", () => {
    const s = currentScene(), sch = currentSchema();
    const deps = sch.params.filter(q => (q.kind === "county" || q.kind === "county_assign") && q.state_param === p.name);
    const hasData = deps.some(q => q.kind === "county" ? s.params[q.name] : Object.keys(s.params[q.name] || {}).length);
    if (hasData && !confirm("Eyalet değişince county boyamaları ve vurgu temizlenecek. Devam edilsin mi?")) {
      sel.value = s.params[p.name];
      return;
    }
    const oldName = (p.options.find(o => o.value === s.params[p.name]) || {}).label?.toUpperCase();
    for (const q of sch.params) if (q.kind === "text" && q.auto && s.params[q.name] === oldName) s.params[q.name] = "";
    for (const q of deps) s.params[q.name] = q.kind === "county" ? null : {};
    for (const q of sch.params) if (q.kind === "text" && q.auto && deps.some(d => d.kind === "county" && d.group === q.group)) s.params[q.name] = "";
    setParam(p.name, sel.value, "structure");
  });
  return sel;
}

async function countySelect(p, value, scene, id) {
  const sel = h("select", { id });
  if (p.allow_none) sel.add(new Option("— yok —", ""));
  const geo = await geoFor(scene.params[p.state_param]);
  for (const c of [...geo.counties].sort((a, b) => a.name.localeCompare(b.name, "en"))) sel.add(new Option(c.name, c.fips));
  sel.value = value || "";
  sel.addEventListener("change", () => {
    const s = currentScene();
    // Vurgu değişince aynı gruptaki otomatik yazılar (ör. vurgu adı) otomatiğe döner.
    for (const q of currentSchema().params) if (q.kind === "text" && q.auto && q.group === p.group) s.params[q.name] = "";
    setParam(p.name, sel.value || null, "structure");
  });
  return sel;
}

function categoriesEditor(p, value) {
  const box = h("div");
  const cats = structuredClone(value);
  const commit = () => setParam(p.name, structuredClone(cats), "categories");
  const draw = () => {
    box.innerHTML = "";
    cats.forEach((c, i) => {
      const row = h("div", { class: "cat-row" },
        h("input", { type: "color", value: c.color, title: "Renk", oninput: e => { c.color = e.target.value; commit(); } }),
        h("input", { type: "text", value: c.label, maxLength: 40, oninput: e => { c.label = e.target.value; commit(); } }));
      if (c.key !== "none") {
        row.append(h("button", { class: "icon-btn", title: "Kategoriyi sil", onclick: () => {
          if (cats.length <= p.min_count) { alert(`En az ${p.min_count} kategori olmalı.`); return; }
          const s = currentScene();
          const ap = currentSchema().params.find(q => q.kind === "county_assign" && q.categories_param === p.name);
          if (ap) for (const [f, k] of Object.entries(s.params[ap.name])) if (k === c.key) delete s.params[ap.name][f];
          cats.splice(i, 1);
          draw();
          commit();
        } }, "✕"));
      }
      box.append(row);
    });
    box.append(h("button", { onclick: () => {
      if (cats.length >= p.max_count) { alert(`En fazla ${p.max_count} kategori olabilir.`); return; }
      let n = 1;
      while (cats.some(c => c.key === `k${n}`)) n++;
      cats.splice(cats.length - 1, 0, { key: `k${n}`, label: "NEW CATEGORY", color: "#8fb0d8" });
      draw();
      commit();
    } }, "Kategori ekle"));
  };
  draw();
  return box;
}
