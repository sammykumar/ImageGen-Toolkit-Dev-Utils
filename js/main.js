import { api as S } from "../../../scripts/api.js";
import { app as E } from "../../../scripts/app.js";
var x = { commitHash: "90af542006af", packageVersion: "0.0.5" };
const A = "load-video-url", P = "video_url_preview", y = "JobEventEmitter", U = "events_url", z = "event_token", h = ["ImageGen Toolkit", "Job Event Emitter"], L = "ImageGenToolkit.JobEventEmitter.eventsUrl", M = "ImageGenToolkit.JobEventEmitter.eventToken", I = 320, f = 16 / 9, G = 120, J = 120, O = "imagegen-toolkit-dev-utils.load-video-url-preview", W = "imagegen-toolkit.live-export.request", C = "/image-gen-toolkit/live-export/result", D = "imagegen-toolkit-dev-utils.live-export-bridge";
let N = !1;
console.info(`[${O}] build`, x);
function H() {
  var e, o, n, i;
  const t = E, r = B(document.title);
  return {
    clientId: (e = t.api) == null ? void 0 : e.clientId,
    graphId: (o = globalThis.graph) == null ? void 0 : o.id,
    frontendVersion: (i = (n = globalThis.graph) == null ? void 0 : n.extra) == null ? void 0 : i.frontendVersion,
    workflowTitle: X(r),
    pageTitle: r
  };
}
function B(t) {
  if (typeof t != "string")
    return;
  const r = t.replace(/\s+/g, " ").trim();
  return r || void 0;
}
function F(t) {
  const r = t.replace(/^[*\u2022]\s*/, "").replace(/\s+/g, " ").trim();
  if (!(!r || r.toLowerCase() === "comfyui"))
    return r;
}
function X(t) {
  if (!t)
    return;
  const r = [
    t.replace(/\s*[-|]\s*ComfyUI$/i, ""),
    t.replace(/^ComfyUI\s*[-|]\s*/i, ""),
    t
  ];
  for (const e of r) {
    const o = F(e);
    if (o)
      return o;
  }
}
function q(t) {
  return t instanceof Error && t.message.trim() ? t.message : typeof t == "string" && t.trim() ? t : "Live export failed in the ComfyUI frontend runtime";
}
async function m(t) {
  await S.fetchApi(C, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(t)
  });
}
async function K(t) {
  var i, s;
  const r = (s = (i = t.detail) == null ? void 0 : i.requestId) == null ? void 0 : s.trim();
  if (!r)
    return;
  const e = H(), o = (/* @__PURE__ */ new Date()).toISOString(), n = E;
  try {
    const c = n.graphToPrompt;
    if (typeof c != "function")
      throw new Error("app.graphToPrompt is unavailable");
    const { output: a } = await c.call(n);
    if (!a || typeof a != "object" || Array.isArray(a)) {
      await m({
        requestId: r,
        ok: !1,
        error: {
          code: "invalid_export_shape",
          message: "app.graphToPrompt() returned an invalid apiPrompt payload"
        },
        ...e,
        exportedAt: o
      });
      return;
    }
    await m({
      requestId: r,
      ok: !0,
      apiPrompt: a,
      ...e,
      exportedAt: o
    });
  } catch (c) {
    await m({
      requestId: r,
      ok: !1,
      error: {
        code: "graph_to_prompt_failed",
        message: q(c)
      },
      ...e,
      exportedAt: o
    });
  }
}
function w(t) {
  var r;
  return (r = t.widgets) == null ? void 0 : r.find((e) => e.name === "video_url");
}
function $(t, r) {
  var e;
  return (e = t.widgets) == null ? void 0 : e.find((o) => o.name === r);
}
function k(t) {
  return typeof t != "string" ? "" : t.trim();
}
function b(t) {
  var e, o;
  const r = (e = E.ui) == null ? void 0 : e.settings;
  return k((o = r == null ? void 0 : r.getSettingValue) == null ? void 0 : o.call(r, t, ""));
}
function V(t, r, e) {
  const o = $(t, r);
  return !o || k(o.value) === e ? !1 : (o.value = e, !0);
}
function T(t) {
  var n;
  const r = b(L), e = b(M);
  [
    V(t, U, r),
    V(t, z, e)
  ].some(Boolean) && ((n = t.setDirtyCanvas) == null || n.call(t, !0, !0));
}
function j(t) {
  return t.type === y || t.comfyClass === y;
}
function v() {
  var r;
  const t = (r = globalThis.graph) == null ? void 0 : r._nodes;
  if (Array.isArray(t))
    for (const e of t)
      j(e) && T(e);
}
function Y(t) {
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
function Z(t) {
  return t.videoWidth <= 0 || t.videoHeight <= 0 ? null : t.videoWidth / t.videoHeight;
}
function _(t, r = f) {
  var c, a, u, p;
  const e = (c = t.computeSize) == null ? void 0 : c.call(t);
  if (!e)
    return;
  const o = Math.max(((a = t.size) == null ? void 0 : a[0]) ?? e[0], I), n = Math.max(o - 16, I - 16), i = Math.max(Math.round(n / r), G), s = [
    o,
    Math.max(e[1], i + J)
  ];
  if (!(((u = t.size) == null ? void 0 : u[0]) === s[0] && ((p = t.size) == null ? void 0 : p[1]) === s[1])) {
    if (typeof t.setSize == "function") {
      t.setSize(s);
      return;
    }
    t.size = s;
  }
}
function R(t) {
  if (t.__loadVideoUrlPreviewState || typeof t.addDOMWidget != "function")
    return;
  const r = document.createElement("div");
  r.style.display = "none", r.style.width = "100%", r.style.padding = "8px 0 0", r.style.aspectRatio = `${f}`;
  const e = document.createElement("video");
  e.controls = !0, e.autoplay = !0, e.loop = !0, e.muted = !0, e.playsInline = !0, e.preload = "metadata", e.style.width = "100%", e.style.height = "100%", e.style.display = "block", e.style.objectFit = "contain", e.style.background = "#111", e.style.borderRadius = "8px", r.append(e);
  let o = f;
  const n = (l) => {
    o = l && Number.isFinite(l) && l > 0 ? l : f, r.style.aspectRatio = `${o}`, _(t, o);
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
  const i = new ResizeObserver(() => {
    r.style.display !== "none" && _(t, o);
  });
  i.observe(r), e.addEventListener("loadedmetadata", () => {
    n(Z(e));
  }), e.addEventListener("emptied", () => {
    n(null);
  });
  const s = () => {
    const l = w(t), d = (typeof (l == null ? void 0 : l.value) == "string" ? l.value : "").trim();
    if (!Y(d)) {
      r.style.display = "none", n(null), e.pause(), delete e.dataset.previewUrl, e.removeAttribute("src"), e.load();
      return;
    }
    r.style.display = "block", e.dataset.previewUrl !== d && (n(null), e.dataset.previewUrl = d, e.src = d, e.load()), e.play().catch(() => {
    }), _(t, o);
  }, c = () => {
    i.disconnect(), e.pause(), delete e.dataset.previewUrl, e.removeAttribute("src"), e.load();
  }, a = w(t), u = a == null ? void 0 : a.callback;
  a && (a.callback = function(...l) {
    const g = u == null ? void 0 : u.apply(this, l);
    return s(), g;
  });
  const p = t.onRemoved;
  t.onRemoved = function(...l) {
    return c(), p == null ? void 0 : p.apply(this, l);
  }, t.__loadVideoUrlPreviewState = {
    sync: s,
    cleanup: c
  }, s();
}
E.registerExtension({
  name: O,
  settings: [
    {
      id: L,
      name: "Job Event Emitter Events URL",
      type: "text",
      defaultValue: "",
      category: h,
      tooltip: "Syncs into Job Event Emitter nodes. Leave blank to use IMAGEGEN_EVENTS_URL.",
      onChange() {
        v();
      }
    },
    {
      id: M,
      name: "Job Event Emitter Event Token",
      type: "text",
      defaultValue: "",
      category: h,
      tooltip: "Syncs into Job Event Emitter nodes. Leave blank to use IMAGEGEN_EVENT_TOKEN.",
      onChange() {
        v();
      }
    }
  ],
  async setup() {
    v();
  },
  beforeRegisterNodeDef(t, r) {
    if (r.name === A) {
      const e = t.prototype.onNodeCreated;
      t.prototype.onNodeCreated = function(...n) {
        const i = e == null ? void 0 : e.apply(this, n);
        return R(this), i;
      };
      const o = t.prototype.onConfigure;
      t.prototype.onConfigure = function(...n) {
        var s;
        const i = o == null ? void 0 : o.apply(this, n);
        return R(this), (s = this.__loadVideoUrlPreviewState) == null || s.sync(), i;
      };
    }
    if (r.name === y) {
      const e = t.prototype.onNodeCreated;
      t.prototype.onNodeCreated = function(...n) {
        const i = e == null ? void 0 : e.apply(this, n);
        return T(this), i;
      };
      const o = t.prototype.onConfigure;
      t.prototype.onConfigure = function(...n) {
        const i = o == null ? void 0 : o.apply(this, n);
        return T(this), i;
      };
    }
  }
});
E.registerExtension({
  name: D,
  async setup() {
    N || (S.addEventListener(W, K), N = !0);
  }
});
