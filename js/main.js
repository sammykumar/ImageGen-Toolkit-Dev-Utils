import { app as c } from "../../../scripts/app.js";
var P = { commitHash: "dc2103ebde03", packageVersion: "0.0.5" };
const I = "load-video-url", _ = "video_url_preview", w = 320, m = 16 / 9, A = 120, k = 120, E = "imagegen-toolkit-dev-utils.load-video-url-preview", x = "/api/image-gen-toolkit/workflows/published-api", v = "imagegen-toolkit.publish-api-export";
console.info(`[${E}] build`, P);
function M(e) {
  return e instanceof Error && e.message.trim() ? e.message.trim() : typeof e == "string" && e.trim() ? e.trim() : "Unknown error";
}
async function S(e) {
  const r = await e.text().catch(() => "");
  if (!r.trim())
    return e.statusText || `HTTP ${e.status}`;
  try {
    const t = JSON.parse(r);
    if (typeof t.error == "string" && t.error.trim())
      return t.error.trim();
    if (t.error && typeof t.error == "object" && !Array.isArray(t.error) && typeof t.error.message == "string")
      return (t.error.message || "").trim() || r;
    if (typeof t.message == "string" && t.message.trim())
      return t.message.trim();
  } catch {
    return r.trim();
  }
  return r.trim();
}
function N() {
  var i;
  const e = c.workflowManager, r = (i = e == null ? void 0 : e.activeWorkflow) == null ? void 0 : i.path;
  if (typeof r != "string" || !r.trim())
    return null;
  const t = r.replace(/^\/+/, "").trim();
  return t ? { sourceKind: "userdata_file", sourceId: t.startsWith("workflows/") ? t : `workflows/${t}` } : null;
}
async function W() {
  const e = N();
  if (!e) {
    c.extensionManager.toast.add({
      severity: "warn",
      summary: "Cannot Publish Export(API)",
      detail: "Open a saved workflow file first (Workflow > Open), then publish.",
      life: 8e3
    });
    return;
  }
  const r = await c.graphToPrompt(), t = await c.api.fetchApi(x, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      sourceKind: e.sourceKind,
      sourceId: e.sourceId,
      workflow: r.workflow,
      apiPrompt: r.output
    })
  });
  if (!t.ok)
    throw new Error(await S(t));
  const o = await t.json();
  c.extensionManager.toast.add({
    severity: "success",
    summary: "Published Export(API)",
    detail: typeof o.workflowHash == "string" && o.workflowHash.length > 0 ? `Saved exact API snapshot ${o.workflowHash.slice(0, 12)} for bridge imports.` : "Saved exact API snapshot for bridge imports.",
    life: 5e3
  });
}
function g(e) {
  var r;
  return (r = e.widgets) == null ? void 0 : r.find((t) => t.name === "video_url");
}
function H(e) {
  if (typeof e != "string")
    return !1;
  const r = e.trim();
  if (!r)
    return !1;
  try {
    const t = new URL(r);
    return (t.protocol === "http:" || t.protocol === "https:") && t.pathname.toLowerCase().endsWith(".mp4");
  } catch {
    return !1;
  }
}
function O(e) {
  return e.videoWidth <= 0 || e.videoHeight <= 0 ? null : e.videoWidth / e.videoHeight;
}
function h(e, r = m) {
  var d, l, u, p;
  const t = (d = e.computeSize) == null ? void 0 : d.call(e);
  if (!t)
    return;
  const o = Math.max(((l = e.size) == null ? void 0 : l[0]) ?? t[0], w), i = Math.max(o - 16, w - 16), n = Math.max(Math.round(i / r), A), a = [
    o,
    Math.max(t[1], n + k)
  ];
  if (!(((u = e.size) == null ? void 0 : u[0]) === a[0] && ((p = e.size) == null ? void 0 : p[1]) === a[1])) {
    if (typeof e.setSize == "function") {
      e.setSize(a);
      return;
    }
    e.size = a;
  }
}
function b(e) {
  if (e.__loadVideoUrlPreviewState || typeof e.addDOMWidget != "function")
    return;
  const r = document.createElement("div");
  r.style.display = "none", r.style.width = "100%", r.style.padding = "8px 0 0", r.style.aspectRatio = `${m}`;
  const t = document.createElement("video");
  t.controls = !0, t.autoplay = !0, t.loop = !0, t.muted = !0, t.playsInline = !0, t.preload = "metadata", t.style.width = "100%", t.style.height = "100%", t.style.display = "block", t.style.objectFit = "contain", t.style.background = "#111", t.style.borderRadius = "8px", r.append(t);
  let o = m;
  const i = (s) => {
    o = s && Number.isFinite(s) && s > 0 ? s : m, r.style.aspectRatio = `${o}`, h(e, o);
  };
  e.addDOMWidget(_, "preview", r, {
    serialize: !1,
    hideOnZoom: !1,
    getValue() {
      return null;
    },
    setValue() {
    }
  });
  const n = new ResizeObserver(() => {
    r.style.display !== "none" && h(e, o);
  });
  n.observe(r), t.addEventListener("loadedmetadata", () => {
    i(O(t));
  }), t.addEventListener("emptied", () => {
    i(null);
  });
  const a = () => {
    const s = g(e), f = (typeof (s == null ? void 0 : s.value) == "string" ? s.value : "").trim();
    if (!H(f)) {
      r.style.display = "none", i(null), t.pause(), delete t.dataset.previewUrl, t.removeAttribute("src"), t.load();
      return;
    }
    r.style.display = "block", t.dataset.previewUrl !== f && (i(null), t.dataset.previewUrl = f, t.src = f, t.load()), t.play().catch(() => {
    }), h(e, o);
  }, d = () => {
    n.disconnect(), t.pause(), delete t.dataset.previewUrl, t.removeAttribute("src"), t.load();
  }, l = g(e), u = l == null ? void 0 : l.callback;
  l && (l.callback = function(...s) {
    const y = u == null ? void 0 : u.apply(this, s);
    return a(), y;
  });
  const p = e.onRemoved;
  e.onRemoved = function(...s) {
    return d(), p == null ? void 0 : p.apply(this, s);
  }, e.__loadVideoUrlPreviewState = {
    sync: a,
    cleanup: d
  }, a();
}
c.registerExtension({
  name: E,
  commands: [
    {
      id: v,
      label: "Publish Export(API) Snapshot",
      menubarLabel: "Publish Export(API) Snapshot",
      tooltip: "Publish the current graphToPrompt() API export for bridge-backed imports.",
      async function() {
        try {
          await W();
        } catch (e) {
          c.extensionManager.toast.add({
            severity: "error",
            summary: "Publish Export(API) failed",
            detail: M(e),
            life: 7e3
          });
        }
      }
    }
  ],
  menuCommands: [
    {
      path: ["Workflow"],
      commands: [v]
    }
  ],
  beforeRegisterNodeDef(e, r) {
    if (r.name !== I)
      return;
    const t = e.prototype.onNodeCreated;
    e.prototype.onNodeCreated = function(...i) {
      const n = t == null ? void 0 : t.apply(this, i);
      return b(this), n;
    };
    const o = e.prototype.onConfigure;
    e.prototype.onConfigure = function(...i) {
      var a;
      const n = o == null ? void 0 : o.apply(this, i);
      return b(this), (a = this.__loadVideoUrlPreviewState) == null || a.sync(), n;
    };
  }
});
