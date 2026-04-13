import { api as I } from "../../../scripts/api.js";
import { app as m } from "../../../scripts/app.js";
var T = { commitHash: "7f92a2824bdc", packageVersion: "0.0.5" };
const x = "load-video-url", P = "video_url_preview", y = 320, f = 16 / 9, R = 120, N = 120, b = "imagegen-toolkit-dev-utils.load-video-url-preview", A = "imagegen-toolkit.live-export.request", V = "/image-gen-toolkit/live-export/result", M = "imagegen-toolkit-dev-utils.live-export-bridge";
let g = !1;
console.info(`[${b}] build`, T);
function O() {
  var r, e, i, o;
  return {
    clientId: (r = m.api) == null ? void 0 : r.clientId,
    graphId: (e = globalThis.graph) == null ? void 0 : e.id,
    frontendVersion: (o = (i = globalThis.graph) == null ? void 0 : i.extra) == null ? void 0 : o.frontendVersion
  };
}
function L(t) {
  return t instanceof Error && t.message.trim() ? t.message : typeof t == "string" && t.trim() ? t : "Live export failed in the ComfyUI frontend runtime";
}
async function v(t) {
  await I.fetchApi(V, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(t)
  });
}
async function S(t) {
  var l, a;
  const r = (a = (l = t.detail) == null ? void 0 : l.requestId) == null ? void 0 : a.trim();
  if (!r)
    return;
  const e = O(), i = (/* @__PURE__ */ new Date()).toISOString(), o = m;
  try {
    const p = o.graphToPrompt;
    if (typeof p != "function")
      throw new Error("app.graphToPrompt is unavailable");
    const { output: n } = await p.call(o);
    if (!n || typeof n != "object" || Array.isArray(n)) {
      await v({
        requestId: r,
        ok: !1,
        error: {
          code: "invalid_export_shape",
          message: "app.graphToPrompt() returned an invalid apiPrompt payload"
        },
        ...e,
        exportedAt: i
      });
      return;
    }
    await v({
      requestId: r,
      ok: !0,
      apiPrompt: n,
      ...e,
      exportedAt: i
    });
  } catch (p) {
    await v({
      requestId: r,
      ok: !1,
      error: {
        code: "graph_to_prompt_failed",
        message: L(p)
      },
      ...e,
      exportedAt: i
    });
  }
}
function _(t) {
  var r;
  return (r = t.widgets) == null ? void 0 : r.find((e) => e.name === "video_url");
}
function U(t) {
  if (typeof t != "string")
    return !1;
  const r = t.trim();
  if (!r)
    return !1;
  try {
    const e = new URL(r);
    return (e.protocol === "http:" || e.protocol === "https:") && e.pathname.toLowerCase().endsWith(".mp4");
  } catch {
    return !1;
  }
}
function z(t) {
  return t.videoWidth <= 0 || t.videoHeight <= 0 ? null : t.videoWidth / t.videoHeight;
}
function E(t, r = f) {
  var p, n, c, u;
  const e = (p = t.computeSize) == null ? void 0 : p.call(t);
  if (!e)
    return;
  const i = Math.max(((n = t.size) == null ? void 0 : n[0]) ?? e[0], y), o = Math.max(i - 16, y - 16), l = Math.max(Math.round(o / r), R), a = [
    i,
    Math.max(e[1], l + N)
  ];
  if (!(((c = t.size) == null ? void 0 : c[0]) === a[0] && ((u = t.size) == null ? void 0 : u[1]) === a[1])) {
    if (typeof t.setSize == "function") {
      t.setSize(a);
      return;
    }
    t.size = a;
  }
}
function w(t) {
  if (t.__loadVideoUrlPreviewState || typeof t.addDOMWidget != "function")
    return;
  const r = document.createElement("div");
  r.style.display = "none", r.style.width = "100%", r.style.padding = "8px 0 0", r.style.aspectRatio = `${f}`;
  const e = document.createElement("video");
  e.controls = !0, e.autoplay = !0, e.loop = !0, e.muted = !0, e.playsInline = !0, e.preload = "metadata", e.style.width = "100%", e.style.height = "100%", e.style.display = "block", e.style.objectFit = "contain", e.style.background = "#111", e.style.borderRadius = "8px", r.append(e);
  let i = f;
  const o = (s) => {
    i = s && Number.isFinite(s) && s > 0 ? s : f, r.style.aspectRatio = `${i}`, E(t, i);
  };
  t.addDOMWidget(P, "preview", r, {
    serialize: !1,
    hideOnZoom: !1,
    getValue() {
      return null;
    },
    setValue() {
    }
  });
  const l = new ResizeObserver(() => {
    r.style.display !== "none" && E(t, i);
  });
  l.observe(r), e.addEventListener("loadedmetadata", () => {
    o(z(e));
  }), e.addEventListener("emptied", () => {
    o(null);
  });
  const a = () => {
    const s = _(t), d = (typeof (s == null ? void 0 : s.value) == "string" ? s.value : "").trim();
    if (!U(d)) {
      r.style.display = "none", o(null), e.pause(), delete e.dataset.previewUrl, e.removeAttribute("src"), e.load();
      return;
    }
    r.style.display = "block", e.dataset.previewUrl !== d && (o(null), e.dataset.previewUrl = d, e.src = d, e.load()), e.play().catch(() => {
    }), E(t, i);
  }, p = () => {
    l.disconnect(), e.pause(), delete e.dataset.previewUrl, e.removeAttribute("src"), e.load();
  }, n = _(t), c = n == null ? void 0 : n.callback;
  n && (n.callback = function(...s) {
    const h = c == null ? void 0 : c.apply(this, s);
    return a(), h;
  });
  const u = t.onRemoved;
  t.onRemoved = function(...s) {
    return p(), u == null ? void 0 : u.apply(this, s);
  }, t.__loadVideoUrlPreviewState = {
    sync: a,
    cleanup: p
  }, a();
}
m.registerExtension({
  name: b,
  beforeRegisterNodeDef(t, r) {
    if (r.name !== x)
      return;
    const e = t.prototype.onNodeCreated;
    t.prototype.onNodeCreated = function(...o) {
      const l = e == null ? void 0 : e.apply(this, o);
      return w(this), l;
    };
    const i = t.prototype.onConfigure;
    t.prototype.onConfigure = function(...o) {
      var a;
      const l = i == null ? void 0 : i.apply(this, o);
      return w(this), (a = this.__loadVideoUrlPreviewState) == null || a.sync(), l;
    };
  }
});
m.registerExtension({
  name: M,
  async setup() {
    g || (I.addEventListener(A, S), g = !0);
  }
});
