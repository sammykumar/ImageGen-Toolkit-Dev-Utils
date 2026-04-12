import { app as d } from "../../../scripts/app.js";
var P = { commitHash: "25b8cc75c672", packageVersion: "0.0.5" };
const _ = "load-video-url", I = "video_url_preview", w = 320, m = 16 / 9, A = 120, x = 120, b = "imagegen-toolkit-dev-utils.load-video-url-preview", k = "/api/image-gen-toolkit/workflows/published-api", v = "imagegen-toolkit.publish-api-export";
console.info(`[${b}] build`, P);
function M(e) {
  return e instanceof Error && e.message.trim() ? e.message.trim() : typeof e == "string" && e.trim() ? e.trim() : "Unknown error";
}
async function N(e) {
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
async function S() {
  const e = await d.graphToPrompt(), r = await d.api.fetchApi(k, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      workflow: e.workflow,
      apiPrompt: e.output
    })
  });
  if (!r.ok)
    throw new Error(await N(r));
  const t = await r.json();
  d.extensionManager.toast.add({
    severity: "success",
    summary: "Published Export(API)",
    detail: typeof t.workflowHash == "string" && t.workflowHash.length > 0 ? `Saved exact API snapshot ${t.workflowHash.slice(0, 12)} for bridge imports.` : "Saved exact API snapshot for bridge imports.",
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
function T(e) {
  return e.videoWidth <= 0 || e.videoHeight <= 0 ? null : e.videoWidth / e.videoHeight;
}
function h(e, r = m) {
  var u, l, c, p;
  const t = (u = e.computeSize) == null ? void 0 : u.call(e);
  if (!t)
    return;
  const o = Math.max(((l = e.size) == null ? void 0 : l[0]) ?? t[0], w), a = Math.max(o - 16, w - 16), n = Math.max(Math.round(a / r), A), s = [
    o,
    Math.max(t[1], n + x)
  ];
  if (!(((c = e.size) == null ? void 0 : c[0]) === s[0] && ((p = e.size) == null ? void 0 : p[1]) === s[1])) {
    if (typeof e.setSize == "function") {
      e.setSize(s);
      return;
    }
    e.size = s;
  }
}
function E(e) {
  if (e.__loadVideoUrlPreviewState || typeof e.addDOMWidget != "function")
    return;
  const r = document.createElement("div");
  r.style.display = "none", r.style.width = "100%", r.style.padding = "8px 0 0", r.style.aspectRatio = `${m}`;
  const t = document.createElement("video");
  t.controls = !0, t.autoplay = !0, t.loop = !0, t.muted = !0, t.playsInline = !0, t.preload = "metadata", t.style.width = "100%", t.style.height = "100%", t.style.display = "block", t.style.objectFit = "contain", t.style.background = "#111", t.style.borderRadius = "8px", r.append(t);
  let o = m;
  const a = (i) => {
    o = i && Number.isFinite(i) && i > 0 ? i : m, r.style.aspectRatio = `${o}`, h(e, o);
  };
  e.addDOMWidget(I, "preview", r, {
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
    a(T(t));
  }), t.addEventListener("emptied", () => {
    a(null);
  });
  const s = () => {
    const i = g(e), f = (typeof (i == null ? void 0 : i.value) == "string" ? i.value : "").trim();
    if (!H(f)) {
      r.style.display = "none", a(null), t.pause(), delete t.dataset.previewUrl, t.removeAttribute("src"), t.load();
      return;
    }
    r.style.display = "block", t.dataset.previewUrl !== f && (a(null), t.dataset.previewUrl = f, t.src = f, t.load()), t.play().catch(() => {
    }), h(e, o);
  }, u = () => {
    n.disconnect(), t.pause(), delete t.dataset.previewUrl, t.removeAttribute("src"), t.load();
  }, l = g(e), c = l == null ? void 0 : l.callback;
  l && (l.callback = function(...i) {
    const y = c == null ? void 0 : c.apply(this, i);
    return s(), y;
  });
  const p = e.onRemoved;
  e.onRemoved = function(...i) {
    return u(), p == null ? void 0 : p.apply(this, i);
  }, e.__loadVideoUrlPreviewState = {
    sync: s,
    cleanup: u
  }, s();
}
d.registerExtension({
  name: b,
  commands: [
    {
      id: v,
      label: "Publish Export(API) Snapshot",
      menubarLabel: "Publish Export(API) Snapshot",
      tooltip: "Publish the current graphToPrompt() API export for bridge-backed imports.",
      async function() {
        try {
          await S();
        } catch (e) {
          d.extensionManager.toast.add({
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
    if (r.name !== _)
      return;
    const t = e.prototype.onNodeCreated;
    e.prototype.onNodeCreated = function(...a) {
      const n = t == null ? void 0 : t.apply(this, a);
      return E(this), n;
    };
    const o = e.prototype.onConfigure;
    e.prototype.onConfigure = function(...a) {
      var s;
      const n = o == null ? void 0 : o.apply(this, a);
      return E(this), (s = this.__loadVideoUrlPreviewState) == null || s.sync(), n;
    };
  }
});
