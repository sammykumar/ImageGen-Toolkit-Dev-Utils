import { app as w } from "../../../scripts/app.js";
var I = { commitHash: "6f4c3fa3695c", packageVersion: "0.0.5" };
const b = "load-video-url", N = "video_url_preview", h = 320, f = 16 / 9, g = 120, M = 120, _ = "imagegen-toolkit-dev-utils.load-video-url-preview";
console.info(`[${_}] build`, I);
function m(t) {
  var r;
  return (r = t.widgets) == null ? void 0 : r.find((e) => e.name === "video_url");
}
function z(t) {
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
function R(t) {
  return t.videoWidth <= 0 || t.videoHeight <= 0 ? null : t.videoWidth / t.videoHeight;
}
function v(t, r = f) {
  var p, l, c, u;
  const e = (p = t.computeSize) == null ? void 0 : p.call(t);
  if (!e)
    return;
  const s = Math.max(((l = t.size) == null ? void 0 : l[0]) ?? e[0], h), a = Math.max(s - 16, h - 16), n = Math.max(Math.round(a / r), g), o = [
    s,
    Math.max(e[1], n + M)
  ];
  if (!(((c = t.size) == null ? void 0 : c[0]) === o[0] && ((u = t.size) == null ? void 0 : u[1]) === o[1])) {
    if (typeof t.setSize == "function") {
      t.setSize(o);
      return;
    }
    t.size = o;
  }
}
function E(t) {
  if (t.__loadVideoUrlPreviewState || typeof t.addDOMWidget != "function")
    return;
  const r = document.createElement("div");
  r.style.display = "none", r.style.width = "100%", r.style.padding = "8px 0 0", r.style.aspectRatio = `${f}`;
  const e = document.createElement("video");
  e.controls = !0, e.autoplay = !0, e.loop = !0, e.muted = !0, e.playsInline = !0, e.preload = "metadata", e.style.width = "100%", e.style.height = "100%", e.style.display = "block", e.style.objectFit = "contain", e.style.background = "#111", e.style.borderRadius = "8px", r.append(e);
  let s = f;
  const a = (i) => {
    s = i && Number.isFinite(i) && i > 0 ? i : f, r.style.aspectRatio = `${s}`, v(t, s);
  };
  t.addDOMWidget(N, "preview", r, {
    serialize: !1,
    hideOnZoom: !1,
    getValue() {
      return null;
    },
    setValue() {
    }
  });
  const n = new ResizeObserver(() => {
    r.style.display !== "none" && v(t, s);
  });
  n.observe(r), e.addEventListener("loadedmetadata", () => {
    a(R(e));
  }), e.addEventListener("emptied", () => {
    a(null);
  });
  const o = () => {
    const i = m(t), d = (typeof (i == null ? void 0 : i.value) == "string" ? i.value : "").trim();
    if (!z(d)) {
      r.style.display = "none", a(null), e.pause(), delete e.dataset.previewUrl, e.removeAttribute("src"), e.load();
      return;
    }
    r.style.display = "block", e.dataset.previewUrl !== d && (a(null), e.dataset.previewUrl = d, e.src = d, e.load()), e.play().catch(() => {
    }), v(t, s);
  }, p = () => {
    n.disconnect(), e.pause(), delete e.dataset.previewUrl, e.removeAttribute("src"), e.load();
  }, l = m(t), c = l == null ? void 0 : l.callback;
  l && (l.callback = function(...i) {
    const y = c == null ? void 0 : c.apply(this, i);
    return o(), y;
  });
  const u = t.onRemoved;
  t.onRemoved = function(...i) {
    return p(), u == null ? void 0 : u.apply(this, i);
  }, t.__loadVideoUrlPreviewState = {
    sync: o,
    cleanup: p
  }, o();
}
w.registerExtension({
  name: _,
  beforeRegisterNodeDef(t, r) {
    if (r.name !== b)
      return;
    const e = t.prototype.onNodeCreated;
    t.prototype.onNodeCreated = function(...a) {
      const n = e == null ? void 0 : e.apply(this, a);
      return E(this), n;
    };
    const s = t.prototype.onConfigure;
    t.prototype.onConfigure = function(...a) {
      var o;
      const n = s == null ? void 0 : s.apply(this, a);
      return E(this), (o = this.__loadVideoUrlPreviewState) == null || o.sync(), n;
    };
  }
});
