// Uygulama durumu: açık proje, seçili sahne, hatalar ve değişiklik bildirimi.
import { api } from "./api.js";

export const store = { project: null, schemas: {}, states: [], selected: 0, dirty: false, errors: [], geo: {} };
const listeners = new Set();

export function on(fn) { listeners.add(fn); }
export function emit(reason) { for (const fn of listeners) fn(reason); }

export function setProject(p) {
  store.project = p;
  store.selected = 0;
  store.dirty = false;
  store.errors = [];
  emit("project");
}
export function currentScene() { return store.project ? store.project.scenes[store.selected] ?? null : null; }
export function currentSchema() { const s = currentScene(); return s ? store.schemas[s.type] : null; }
export function setParam(name, value, reason = "param") {
  currentScene().params[name] = value;
  store.dirty = true;
  emit(reason);
}
export function touch(reason) { store.dirty = true; emit(reason); }
export function selectScene(i) { store.selected = i; emit("select"); }
export function sceneErrors(i) { return store.errors.filter(e => e.scene === i); }
// Doğrulama hatasını okunur bir satıra çevirir: "• 2. sahne · Vurgulanan county: ..."
export function describeError(e, project = store.project) {
  const where = e.scene == null ? "Proje" : `${e.scene + 1}. sahne`;
  const sc = e.scene == null ? null : project?.scenes?.[e.scene];
  const sch = sc && store.schemas[sc.type];
  const label = sch ? (sch.params.find(p => p.name === e.param) || {}).label || e.param : e.param;
  return `• ${where}${label ? " · " + label : ""}: ${e.message}`;
}
export async function geoFor(abbr) {
  if (!store.geo[abbr]) store.geo[abbr] = await api.geo(abbr);
  return store.geo[abbr];
}
export function defaultsFor(type) {
  return Object.fromEntries(store.schemas[type].params.map(p => [p.name, structuredClone(p.default)]));
}
