// Tek kare önizleme: ayar değişince gecikmeli, kaydırma çubuğunda hızlı istek; eski istek iptal edilir.
import { previewBlob } from "./api.js";
import { currentScene, store } from "./state.js";

const $ = id => document.getElementById(id);
let timer = null, ctrl = null, lastUrl = null;

export function fmtSec(v) { return `${Number(v).toFixed(1).replace(".", ",")} sn`; }

function setStatus(text, error = false) {
  $("preview-status").textContent = text;
  $("preview-status").classList.toggle("error", error);
}

export function syncSlider() {
  const s = currentScene();
  if (!s) return;
  const dur = Number(s.params.duration) || 1;
  const sl = $("t-slider");
  sl.max = dur;
  if (Number(sl.value) > dur) sl.value = dur;
  $("t-max").textContent = fmtSec(dur);
  $("t-label").textContent = fmtSec(sl.value);
  $("preview-wrap").classList.toggle("checker", !!store.project.output.transparent);
}

export function schedulePreview(delay = 500) {
  clearTimeout(timer);
  timer = setTimeout(run, delay);
}

async function run() {
  const s = currentScene();
  if (!s) return;
  if (ctrl) ctrl.abort();
  ctrl = new AbortController();
  setStatus("Önizleme hazırlanıyor…");
  try {
    const blob = await previewBlob({ type: s.type, params: s.params, t: Number($("t-slider").value),
      transparent: !!store.project.output.transparent }, ctrl.signal);
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = URL.createObjectURL(blob);
    $("preview-img").src = lastUrl;
    setStatus("");
  } catch (e) {
    if (e.name === "AbortError") return;
    setStatus(e.status === 422 ? "Ayarlarda hata var; kırmızı yazılı alanları düzeltin." : e.message, true);
  }
}

export function initPreview() {
  $("t-slider").addEventListener("input", () => {
    $("t-label").textContent = fmtSec($("t-slider").value);
    schedulePreview(120);
  });
}
