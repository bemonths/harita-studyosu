// Sunucu API'si için fetch sarmalayıcıları. Hatalar Error(message) olarak fırlatılır.
export function apiError(status, data) {
  const d = data && data.detail;
  let msg = typeof d === "string" ? d : (d && d.message) || `İstek başarısız oldu (${status}).`;
  if (d && d.errors && !Array.isArray(d.errors)) {
    msg += " " + Object.entries(d.errors).map(([k, v]) => `${k}: ${v}`).join(", ");
  }
  const err = new Error(msg);
  err.status = status;
  err.data = data;
  return err;
}

async function request(method, url, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(url, opts);
  const isJson = (r.headers.get("content-type") || "").includes("json");
  const data = isJson ? await r.json() : await r.blob();
  if (!r.ok) throw apiError(r.status, data);
  return data;
}

const enc = encodeURIComponent;
export const api = {
  scenes: () => request("GET", "/api/scenes"),
  states: () => request("GET", "/api/states"),
  geo: abbr => request("GET", `/api/geo/${enc(abbr)}`),
  projects: () => request("GET", "/api/projects"),
  newProject: () => request("GET", "/api/projects/_new"),
  loadProject: name => request("GET", `/api/projects/${enc(name)}`),
  saveProject: (name, project) => request("PUT", `/api/projects/${enc(name)}`, project),
  validate: project => request("POST", "/api/validate", project),
  importAssignments: body => request("POST", "/api/import-assignments", body),
  render: project => request("POST", "/api/render", { project }),
  job: id => request("GET", `/api/jobs/${enc(id)}`),
  cancel: id => request("POST", `/api/jobs/${enc(id)}/cancel`),
  openFolder: path => request("POST", "/api/open-folder", { path }),
};

export async function previewBlob(body, signal) {
  const r = await fetch("/api/preview", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal,
  });
  if (!r.ok) {
    let data = null;
    try { data = await r.json(); } catch { data = null; }
    throw apiError(r.status, data);
  }
  return r.blob();
}
