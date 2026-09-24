// Fiyat geçmişi tablosu: tarih + fiyat satırları, ekle/sil.
import { h } from "./dom.js";

export function priceTable(rows, onChange) {
  const box = h("div");
  const data = structuredClone(rows || []);
  const commit = () => onChange(structuredClone(data));
  const draw = () => {
    box.innerHTML = "";
    const body = h("tbody");
    data.forEach((r, i) => {
      body.append(h("tr", {},
        h("td", {}, h("input", { type: "date", value: r.date, onchange: e => { r.date = e.target.value; commit(); } })),
        h("td", {}, h("input", { type: "number", min: 1, step: 1, value: r.price ?? "",
          oninput: e => { r.price = e.target.value === "" ? null : Number(e.target.value); commit(); } })),
        h("td", {}, h("button", { class: "icon-btn", title: "Satırı sil", onclick: () => { data.splice(i, 1); draw(); commit(); } }, "✕")),
      ));
    });
    box.append(h("table", { class: "prices" },
      h("thead", {}, h("tr", {}, h("th", {}, "Tarih"), h("th", {}, "Fiyat ($)"), h("th"))), body));
    box.append(h("button", { onclick: () => {
      const last = data[data.length - 1];
      const next = last ? new Date(Date.parse(last.date) + 30 * 864e5) : new Date();
      data.push({ date: next.toISOString().slice(0, 10), price: last ? last.price : 100000 });
      draw();
      commit();
    } }, "Satır ekle"));
  };
  draw();
  return box;
}
