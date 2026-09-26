// Grafik verisi tablosu: etiket + değer + işaret satırları, ekle/sil (satır sayısı sınırları içinde).
import { h } from "./dom.js";

export function valueTable(p, rows, onChange) {
  const box = h("div");
  const data = structuredClone(rows || []);
  const commit = () => onChange(structuredClone(data));
  const draw = () => {
    box.innerHTML = "";
    const body = h("tbody");
    data.forEach((r, i) => {
      body.append(h("tr", {},
        h("td", {}, h("input", { type: "text", value: r.label ?? "", maxLength: 24, title: "Etiket (en fazla 24 karakter)",
          oninput: e => { r.label = e.target.value; commit(); } })),
        h("td", {}, h("input", { type: "number", step: p.integer ? 1 : "any", min: p.min ?? "", value: r.value ?? "",
          oninput: e => { r.value = e.target.value === "" ? null : Number(e.target.value); commit(); } })),
        h("td", {}, h("input", { type: "checkbox", checked: !!r.highlight, title: "Vurgula",
          onchange: e => { r.highlight = e.target.checked; commit(); } })),
        h("td", {}, h("button", { class: "icon-btn", title: "Satırı sil", onclick: () => {
          if (data.length <= p.min_rows) { alert(`En az ${p.min_rows} satır olmalı.`); return; }
          data.splice(i, 1);
          draw();
          commit();
        } }, "✕")),
      ));
    });
    box.append(h("table", { class: "prices values" },
      h("thead", {}, h("tr", {}, h("th", {}, "Etiket"), h("th", {}, "Değer"), h("th", { title: "Vurgula" }, "★"), h("th"))),
      body));
    box.append(h("button", { onclick: () => {
      if (data.length >= p.max_rows) { alert(`En fazla ${p.max_rows} satır olabilir.`); return; }
      const last = data[data.length - 1];
      data.push({ label: "", value: last ? last.value : 0, highlight: false });
      draw();
      commit();
    } }, "Satır ekle"));
  };
  draw();
  return box;
}
