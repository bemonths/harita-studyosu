// Render paneli: çıktı seçenekleri, başlatma, ilerleme, iptal, biten dosyalar.
import { api } from "./api.js";
import { h } from "./dom.js";
import { schedulePreview, syncSlider } from "./preview.js";
import { describeError, emit, store, touch } from "./state.js";

let jobId = null, root = null;
const $ = id => root.querySelector("#" + id);

export function renderRenderPanel(el) {
  root = el;
  const o = store.project.output;
  root.innerHTML = `
    <div class="render-opts">
      <label><input type="checkbox" id="o-separate"> Her sahne ayrı dosya</label>
      <label><input type="checkbox" id="o-combined"> Birleşik video</label>
      <label><input type="radio" name="o-bg" id="o-opaque"> Koyu arka plan</label>
      <label><input type="radio" name="o-bg" id="o-transparent"> Şeffaf arka plan</label>
      <label>Geçiş <input type="number" id="o-transition" min="0" max="2" step="0.1" style="width:70px"> sn</label>
    </div>
    <div class="progress">
      <button class="primary" id="btn-render">Render al</button>
      <button id="btn-cancel" hidden>İptal</button>
      <div class="bar"><div id="bar-fill"></div></div>
      <span id="render-status" class="muted"></span>
    </div>
    <div id="render-errors" class="errors-box"></div>
    <ul id="outputs" class="outputs"></ul>`;
  $("o-separate").checked = o.separate;
  $("o-combined").checked = o.combined;
  $("o-opaque").checked = !o.transparent;
  $("o-transparent").checked = o.transparent;
  $("o-transition").value = store.project.transition;
  $("o-separate").addEventListener("change", e => { o.separate = e.target.checked; touch("output"); });
  $("o-combined").addEventListener("change", e => { o.combined = e.target.checked; touch("output"); });
  for (const id of ["o-opaque", "o-transparent"]) {
    $(id).addEventListener("change", () => {
      o.transparent = $("o-transparent").checked;
      touch("output");
      syncSlider();
      schedulePreview(0);
    });
  }
  $("o-transition").addEventListener("input", e => {
    store.project.transition = e.target.value === "" ? 0 : Number(e.target.value);
    touch("output");
  });
  $("btn-render").addEventListener("click", start);
  $("btn-cancel").addEventListener("click", () => { if (jobId) api.cancel(jobId).catch(e => alert(e.message)); });
  if (jobId) { $("btn-render").disabled = true; $("btn-cancel").hidden = false; }
}

async function start() {
  $("render-errors").textContent = "";
  try {
    const { errors } = await api.validate(store.project);
    store.errors = errors;
    emit("errors");
    if (errors.length) {
      $("render-errors").textContent = "Render başlamadı. Önce şu hataları düzeltin:\n" + errors.map(e => describeError(e)).join("\n");
      return;
    }
    jobId = (await api.render(store.project)).job_id;
  } catch (e) {
    $("render-errors").textContent = e.message;
    return;
  }
  $("btn-render").disabled = true;
  $("btn-cancel").hidden = false;
  $("outputs").innerHTML = "";
  poll();
}

async function poll() {
  let j;
  try {
    j = await api.job(jobId);
  } catch (e) {
    $("render-status").textContent = e.message;
    finish();
    return;
  }
  $("bar-fill").style.width = `${j.percent}%`;
  if (j.state === "running") {
    $("render-status").textContent = j.phase === "compose"
      ? "Sahneler birleştiriliyor…"
      : j.parallel ? `${j.finished_scenes}/${j.scenes} sahne bitti · %${j.percent}` : `Sahne ${j.scene + 1}/${j.scenes} · %${j.percent}`;
    setTimeout(poll, 700);
    return;
  }
  if (j.state === "done") {
    $("render-status").textContent = "Tamamlandı";
    showOutputs(j);
  } else if (j.state === "canceled") {
    $("render-status").textContent = "İptal edildi";
    $("bar-fill").style.width = "0";
  } else {
    $("render-status").textContent = "Başarısız";
    $("render-errors").textContent = [j.error, ...(j.log || [])].filter(Boolean).join("\n");
  }
  finish();
}

function finish() {
  jobId = null;
  $("btn-render").disabled = false;
  $("btn-cancel").hidden = true;
}

function showOutputs(j) {
  const ul = $("outputs");
  ul.innerHTML = "";
  for (const rel of j.outputs) {
    const li = h("li", {}, h("div", {}, rel.split("/").pop()));
    if (rel.endsWith(".mp4")) {
      li.append(h("video", { controls: true, preload: "metadata", src: "/api/outputs/" + rel.split("/").map(encodeURIComponent).join("/") }));
    } else {
      li.append(h("div", { class: "muted" }, "Şeffaf .mov dosyası tarayıcıda oynatılamaz; kurgu programında açın."));
    }
    ul.append(li);
  }
  ul.append(h("li", {}, h("button", { onclick: () => api.openFolder(j.dir).catch(e => alert(e.message)) }, "Klasörü aç")));
}
