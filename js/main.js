import { api as I } from "../../../scripts/api.js";
import { app as m } from "../../../scripts/app.js";
var b = { commitHash: "b055ac9d411f", packageVersion: "0.0.5" };
const x = "load-video-url", P = "video_url_preview", h = 320, f = 16 / 9, R = 120, L = 120, T = "imagegen-toolkit-dev-utils.load-video-url-preview", N = "imagegen-toolkit.live-export.request", V = "/image-gen-toolkit/live-export/result", z = "imagegen-toolkit-dev-utils.live-export-bridge";
let g = !1;
console.info(`[${T}] build`, b);
function A() {
  var t, i, o, n;
  const e = m, r = M(document.title);
  return {
    clientId: (t = e.api) == null ? void 0 : t.clientId,
    graphId: (i = globalThis.graph) == null ? void 0 : i.id,
    frontendVersion: (n = (o = globalThis.graph) == null ? void 0 : o.extra) == null ? void 0 : n.frontendVersion,
    workflowTitle: k(r),
    pageTitle: r
  };
}
function M(e) {
  if (typeof e != "string")
    return;
  const r = e.replace(/\s+/g, " ").trim();
  return r || void 0;
}
function O(e) {
  const r = e.replace(/^[*\u2022]\s*/, "").replace(/\s+/g, " ").trim();
  if (!(!r || r.toLowerCase() === "comfyui"))
    return r;
}
function k(e) {
  if (!e)
    return;
  const r = [
    e.replace(/\s*[-|]\s*ComfyUI$/i, ""),
    e.replace(/^ComfyUI\s*[-|]\s*/i, ""),
    e
  ];
  for (const t of r) {
    const i = O(t);
    if (i)
      return i;
  }
}
function U(e) {
  return e instanceof Error && e.message.trim() ? e.message : typeof e == "string" && e.trim() ? e : "Live export failed in the ComfyUI frontend runtime";
}
async function v(e) {
  await I.fetchApi(V, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(e)
  });
}
async function S(e) {
  var n, a;
  const r = (a = (n = e.detail) == null ? void 0 : n.requestId) == null ? void 0 : a.trim();
  if (!r)
    return;
  const t = A(), i = (/* @__PURE__ */ new Date()).toISOString(), o = m;
  try {
    const c = o.graphToPrompt;
    if (typeof c != "function")
      throw new Error("app.graphToPrompt is unavailable");
    const { output: s } = await c.call(o);
    if (!s || typeof s != "object" || Array.isArray(s)) {
      await v({
        requestId: r,
        ok: !1,
        error: {
          code: "invalid_export_shape",
          message: "app.graphToPrompt() returned an invalid apiPrompt payload"
        },
        ...t,
        exportedAt: i
      });
      return;
    }
    await v({
      requestId: r,
      ok: !0,
      apiPrompt: s,
      ...t,
      exportedAt: i
    });
  } catch (c) {
    await v({
      requestId: r,
      ok: !1,
      error: {
        code: "graph_to_prompt_failed",
        message: U(c)
      },
      ...t,
      exportedAt: i
    });
  }
}
function _(e) {
  var r;
  return (r = e.widgets) == null ? void 0 : r.find((t) => t.name === "video_url");
}
function W(e) {
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
function D(e) {
  return e.videoWidth <= 0 || e.videoHeight <= 0 ? null : e.videoWidth / e.videoHeight;
}
function y(e, r = f) {
  var c, s, p, u;
  const t = (c = e.computeSize) == null ? void 0 : c.call(e);
  if (!t)
    return;
  const i = Math.max(((s = e.size) == null ? void 0 : s[0]) ?? t[0], h), o = Math.max(i - 16, h - 16), n = Math.max(Math.round(o / r), R), a = [
    i,
    Math.max(t[1], n + L)
  ];
  if (!(((p = e.size) == null ? void 0 : p[0]) === a[0] && ((u = e.size) == null ? void 0 : u[1]) === a[1])) {
    if (typeof e.setSize == "function") {
      e.setSize(a);
      return;
    }
    e.size = a;
  }
}
function w(e) {
  if (e.__loadVideoUrlPreviewState || typeof e.addDOMWidget != "function")
    return;
  const r = document.createElement("div");
  r.style.display = "none", r.style.width = "100%", r.style.padding = "8px 0 0", r.style.aspectRatio = `${f}`;
  const t = document.createElement("video");
  t.controls = !0, t.autoplay = !0, t.loop = !0, t.muted = !0, t.playsInline = !0, t.preload = "metadata", t.style.width = "100%", t.style.height = "100%", t.style.display = "block", t.style.objectFit = "contain", t.style.background = "#111", t.style.borderRadius = "8px", r.append(t);
  let i = f;
  const o = (l) => {
    i = l && Number.isFinite(l) && l > 0 ? l : f, r.style.aspectRatio = `${i}`, y(e, i);
  };
  e.addDOMWidget(P, "preview", r, {
    serialize: !1,
    hideOnZoom: !1,
    getValue() {
      return null;
    },
    setValue() {
    }
  });
  const n = new ResizeObserver(() => {
    r.style.display !== "none" && y(e, i);
  });
  n.observe(r), t.addEventListener("loadedmetadata", () => {
    o(D(t));
  }), t.addEventListener("emptied", () => {
    o(null);
  });
  const a = () => {
    const l = _(e), d = (typeof (l == null ? void 0 : l.value) == "string" ? l.value : "").trim();
    if (!W(d)) {
      r.style.display = "none", o(null), t.pause(), delete t.dataset.previewUrl, t.removeAttribute("src"), t.load();
      return;
    }
    r.style.display = "block", t.dataset.previewUrl !== d && (o(null), t.dataset.previewUrl = d, t.src = d, t.load()), t.play().catch(() => {
    }), y(e, i);
  }, c = () => {
    n.disconnect(), t.pause(), delete t.dataset.previewUrl, t.removeAttribute("src"), t.load();
  }, s = _(e), p = s == null ? void 0 : s.callback;
  s && (s.callback = function(...l) {
    const E = p == null ? void 0 : p.apply(this, l);
    return a(), E;
  });
  const u = e.onRemoved;
  e.onRemoved = function(...l) {
    return c(), u == null ? void 0 : u.apply(this, l);
  }, e.__loadVideoUrlPreviewState = {
    sync: a,
    cleanup: c
  }, a();
}
m.registerExtension({
  name: T,
  beforeRegisterNodeDef(e, r) {
    if (r.name === x) {
      const t = e.prototype.onNodeCreated;
      e.prototype.onNodeCreated = function(...o) {
        const n = t == null ? void 0 : t.apply(this, o);
        return w(this), n;
      };
      const i = e.prototype.onConfigure;
      e.prototype.onConfigure = function(...o) {
        var a;
        const n = i == null ? void 0 : i.apply(this, o);
        return w(this), (a = this.__loadVideoUrlPreviewState) == null || a.sync(), n;
      };
    }
  }
});
m.registerExtension({
  name: z,
  async setup() {
    g || (I.addEventListener(N, S), g = !0);
  }
});
