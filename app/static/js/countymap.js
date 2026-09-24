// County boyama paneli: kategori fırçası, tıkla/sürükle ile boyama, CSV/Excel içe aktarma.
import { api } from "./api.js";
import { h } from "./dom.js";
import { currentScene, currentSchema, geoFor, touch } from "./state.js";

const NS = "http://www.w3.org/2000/svg";
let brush = null, painting = false, token = 0;
window.addEventListener("pointerup", () => { painting = false; });

export async function renderCountyPanel(panel, body) {
  const my = ++token;
  const schema = currentSchema(), scene = currentScene();
  const ap = schema && schema.params.find(p => p.kind === "county_assign");
  panel.hidden = !ap;
  if (!ap) { body.innerHTML = ""; return; }
  const abbr = scene.params[ap.state_param];
  const cats = scene.params[ap.categories_param];
  const assign = scene.params[ap.name];
  if (!cats.some(c => c.key === brush)) brush = cats[0].key;
  const color = Object.fromEntries(cats.map(c => [c.key, c.color]));
  const geo = await geoFor(abbr);
  if (my !== token) return;

  const info = h("div", { class: "map-info" }, "Bir renk seçin, sonra county'lere tıklayın ya da basılı tutup sürükleyin.");
  const result = h("div", { class: "import-result" });
  const paths = {};
  const repaint = () => { for (const [f, el] of Object.entries(paths)) el.setAttribute("fill", color[assign[f] || "none"]); };
  const changed = () => touch("assign");
  const paint = fips => {
    if ((assign[fips] || "none") === brush) return;
    if (brush === "none") delete assign[fips]; else assign[fips] = brush;
    paths[fips].setAttribute("fill", color[brush]);
    changed();
  };

  const bar = h("div", { class: "map-toolbar" });
  for (const c of cats) {
    const b = h("span", { class: "brush" + (c.key === brush ? " active" : ""), title: "Fırça", onclick: () => {
      brush = c.key;
      bar.querySelectorAll(".brush").forEach(x => x.classList.remove("active"));
      b.classList.add("active");
    } });
    const sw = h("span", { class: "swatch" });
    sw.style.background = c.color;
    b.append(sw, c.label);
    bar.append(b);
  }
  const file = h("input", { type: "file", accept: ".csv,.xlsx,.xlsm", hidden: true, onchange: async () => {
    const f = file.files[0];
    file.value = "";
    if (f) await importFile(f);
  } });
  bar.append(h("span", { class: "spacer" }),
    h("button", { onclick: () => file.click() }, "CSV / Excel yükle"), file,
    h("button", { onclick: () => {
      if (!Object.keys(assign).length || !confirm("Tüm county boyamaları silinsin mi?")) return;
      for (const k of Object.keys(assign)) delete assign[k];
      repaint();
      changed();
    } }, "Temizle"));

  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${geo.width} ${geo.height}`);
  for (const c of geo.counties) {
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", c.d);
    const title = document.createElementNS(NS, "title");
    title.textContent = c.name;
    path.append(title);
    path.addEventListener("pointerdown", e => { e.preventDefault(); painting = true; paint(c.fips); });
    path.addEventListener("pointerenter", () => {
      const k = assign[c.fips] || "none";
      info.textContent = `${c.name} · ${(cats.find(x => x.key === k) || {}).label || ""}`;
      if (painting) paint(c.fips);
    });
    paths[c.fips] = path;
    svg.append(path);
  }

  async function importFile(f) {
    result.textContent = "Dosya okunuyor…";
    try {
      const buf = new Uint8Array(await f.arrayBuffer());
      let bin = "";
      for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode(...buf.subarray(i, i + 0x8000));
      const res = await api.importAssignments({ state: abbr, categories: cats, filename: f.name, content_b64: btoa(bin) });
      for (const [fips, key] of Object.entries(res.assign)) {
        if (key === "none") delete assign[fips]; else assign[fips] = key;
      }
      repaint();
      changed();
      result.innerHTML = "";
      result.append(h("div", {}, `${Object.keys(res.assign).length} county atandı.`));
      if (res.unmatched.length || res.ambiguous.length) {
        const ul = h("ul");
        for (const u of res.unmatched) ul.append(h("li", {}, `Satır ${u.row}: "${u.county}" (${u.category}): ${u.reason}`));
        for (const a of res.ambiguous) {
          ul.append(h("li", {}, `Satır ${a.row}: "${a.county}" birden fazla county'ye uyuyor (${a.candidates.join(", ")}). Tam adı yazın.`));
        }
        result.append(ul);
      }
    } catch (e) {
      result.textContent = e.message;
    }
  }

  body.innerHTML = "";
  body.append(bar, h("div", { class: "county-map" }, svg), info, result);
  repaint();
}
