// Uygulamanın girişi: veriyi yükler, parçaları bağlar, olayları dağıtır.
import { api } from "./api.js";
import { h } from "./dom.js";
import { assignText, renderForm, showErrors } from "./form.js";
import { renderCountyPanel } from "./countymap.js";
import { initPreview, schedulePreview, syncSlider } from "./preview.js";
import { renderRenderPanel } from "./render.js";
import { currentScene, defaultsFor, emit, on, sceneErrors, selectScene, setProject, store, touch } from "./state.js";

const $ = id => document.getElementById(id);
let validateTimer = null;
window.studio = { store };

function fmtDur(v) { return `${Number(v).toFixed(1).replace(".", ",")} sn`; }

function renderSceneList() {
  const ul = $("scene-list");
  ul.innerHTML = "";
  store.project.scenes.forEach((s, i) => {
    const sch = store.schemas[s.type];
    const li = h("li", { class: "scene-item" + (i === store.selected ? " selected" : ""), onclick: () => selectScene(i) },
      h("input", { type: "checkbox", checked: s.enabled, title: "Render'a dahil et",
        onclick: e => e.stopPropagation(), onchange: e => { s.enabled = e.target.checked; touch("scenes"); } }),
      h("span", { class: "title" }, `${i + 1}. ${sch.title}`),
      sceneErrors(i).length ? h("span", { class: "err-dot", title: "Bu sahnede hatalı ayar var" }) : null,
      h("span", { class: "dur" }, fmtDur(s.params.duration)));
    for (const [label, tip, fn] of [["↑", "Yukarı taşı", () => move(i, -1)], ["↓", "Aşağı taşı", () => move(i, 1)],
      ["✕", "Sahneyi sil", () => remove(i)]]) {
      li.append(h("button", { class: "icon-btn", title: tip, onclick: e => { e.stopPropagation(); fn(); } }, label));
    }
    ul.append(li);
  });
}

function move(i, d) {
  const sc = store.project.scenes, j = i + d;
  if (j < 0 || j >= sc.length) return;
  [sc[i], sc[j]] = [sc[j], sc[i]];
  if (store.selected === i) store.selected = j;
  else if (store.selected === j) store.selected = i;
  touch("scenes");
}

function remove(i) {
  const sc = store.project.scenes;
  if (sc.length === 1) { alert("Projede en az bir sahne kalmalı."); return; }
  if (!confirm(`${i + 1}. sahne silinsin mi?`)) return;
  sc.splice(i, 1);
  store.selected = Math.min(store.selected, sc.length - 1);
  touch("select");
}

function updateHeader() {
  $("project-name").textContent = `· ${store.project.name}`;
  $("dirty").hidden = !store.dirty;
}

function updateAssignSummary() {
  const el = document.querySelector("[data-assign-summary]");
  if (el) el.textContent = assignText(currentScene().params[el.dataset.assignSummary]);
}

function validateSoon() {
  clearTimeout(validateTimer);
  validateTimer = setTimeout(async () => {
    try {
      store.errors = (await api.validate(store.project)).errors;
      emit("errors");
    } catch (e) {
      console.warn("Doğrulama yapılamadı:", e);
    }
  }, 600);
}

async function refreshProjectList() {
  const sel = $("open-select");
  const { projects } = await api.projects();
  sel.innerHTML = "";
  sel.add(new Option("Proje aç…", ""));
  for (const n of projects) sel.add(new Option(n, n));
  sel.value = "";
  return projects;
}

function confirmDiscard() {
  return !store.dirty || confirm("Kaydedilmemiş değişiklikler kaybolacak. Devam edilsin mi?");
}

async function openProject(name) {
  const { project, errors } = await api.loadProject(name);
  setProject(project);
  if (errors.length) {
    alert("Projedeki bazı ayarlar geçersizdi ve varsayılanlarla değiştirildi:\n" +
      errors.map(e => `• ${e.param}: ${e.message}`).join("\n"));
  }
}

async function redrawScene() {
  renderSceneList();
  syncSlider();
  await renderForm($("form"));
  await renderCountyPanel($("county-panel"), $("county-map"));
  schedulePreview(0);
  validateSoon();
}

on(async reason => {
  updateHeader();
  switch (reason) {
    case "project":
      $("t-slider").value = Math.min(8.6, Number(store.project.scenes[0]?.params.duration) || 0);
      renderRenderPanel($("render"));
      await redrawScene();
      break;
    case "select":
    case "structure":
      await redrawScene();
      break;
    case "param":
      renderSceneList();
      syncSlider();
      schedulePreview();
      validateSoon();
      break;
    case "categories":
      await renderCountyPanel($("county-panel"), $("county-map"));
      schedulePreview();
      validateSoon();
      break;
    case "assign":
      updateAssignSummary();
      schedulePreview();
      validateSoon();
      break;
    case "scenes":
      renderSceneList();
      validateSoon();
      break;
    case "output":
      validateSoon();
      break;
    case "errors":
      renderSceneList();
      showErrors();
      break;
  }
});

$("btn-new").addEventListener("click", async () => {
  if (!confirmDiscard()) return;
  try { setProject(await api.newProject()); } catch (e) { alert(e.message); }
});

$("open-select").addEventListener("change", async e => {
  const name = e.target.value;
  e.target.value = "";
  if (!name || !confirmDiscard()) return;
  try { await openProject(name); } catch (err) { alert(err.message); }
});

$("btn-save").addEventListener("click", async () => {
  const answer = prompt("Proje adı (harf, rakam, _ ve -):", store.project.name);
  if (answer === null) return;
  const name = answer.trim();
  if (!/^[A-Za-z0-9_-]{1,60}$/.test(name)) { alert("Ad yalnızca harf, rakam, _ ve - içerebilir."); return; }
  try {
    const exists = (await api.projects()).projects.includes(name);
    if (exists && name !== store.project.name && !confirm(`"${name}" adında bir proje var. Üzerine yazılsın mı?`)) return;
    store.project.name = name;
    const res = await api.saveProject(name, store.project);
    store.dirty = false;
    updateHeader();
    await refreshProjectList();
    if (res.errors.length) {
      store.errors = res.errors;
      emit("errors");
      alert("Proje kaydedildi, ancak bazı ayarlar hatalı. Render almadan önce düzeltin.");
    }
  } catch (e) {
    alert(e.message);
  }
});

$("btn-add-scene").addEventListener("click", () => {
  const type = $("add-scene-type").value;
  store.project.scenes.push({ type, enabled: true, params: defaultsFor(type) });
  store.selected = store.project.scenes.length - 1;
  touch("select");
});

window.addEventListener("beforeunload", e => {
  if (store.dirty) { e.preventDefault(); e.returnValue = ""; }
});

async function init() {
  try {
    const [schemas, states] = await Promise.all([api.scenes(), api.states()]);
    store.schemas = Object.fromEntries(schemas.map(s => [s.id, s]));
    store.states = states;
    for (const s of schemas) $("add-scene-type").add(new Option(s.title, s.id));
    initPreview();
    const projects = await refreshProjectList();
    if (projects.includes("ornek_florida")) await openProject("ornek_florida");
    else setProject(await api.newProject());
  } catch (e) {
    document.body.prepend(h("div", { class: "errors-box", style: "padding:12px" }, `Arayüz başlatılamadı: ${e.message}`));
  }
}

init();
