const v = "load-video-url", m = "video_url_preview";
function p(e) {
  var r;
  return (r = e.widgets) == null ? void 0 : r.find((t) => t.name === "video_url");
}
function E(e) {
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
function d(e) {
  var o;
  const r = (o = e.computeSize) == null ? void 0 : o.call(e);
  if (!r)
    return;
  const t = [
    Math.max(r[0], 320),
    Math.max(r[1], 300)
  ];
  if (typeof e.setSize == "function") {
    e.setSize(t);
    return;
  }
  e.size = t;
}
function f(e) {
  if (e.__loadVideoUrlPreviewState || typeof e.addDOMWidget != "function")
    return;
  const r = document.createElement("div");
  r.style.display = "none", r.style.width = "100%", r.style.padding = "8px 0 0";
  const t = document.createElement("video");
  t.controls = !0, t.autoplay = !0, t.loop = !0, t.muted = !0, t.playsInline = !0, t.preload = "metadata", t.style.width = "100%", t.style.maxHeight = "180px", t.style.display = "block", t.style.objectFit = "contain", t.style.background = "#111", t.style.borderRadius = "8px", r.append(t), e.addDOMWidget(m, "preview", r, {
    serialize: !1,
    hideOnZoom: !1,
    getValue() {
      return null;
    },
    setValue() {
    }
  });
  const o = () => {
    const s = p(e), l = (typeof (s == null ? void 0 : s.value) == "string" ? s.value : "").trim();
    if (!E(l)) {
      r.style.display = "none", t.pause(), t.removeAttribute("src"), t.load(), d(e);
      return;
    }
    r.style.display = "block", t.dataset.previewUrl !== l && (t.dataset.previewUrl = l, t.src = l, t.load()), t.play().catch(() => {
    }), d(e);
  }, a = () => {
    t.pause(), t.removeAttribute("src"), t.load();
  }, i = p(e), n = i == null ? void 0 : i.callback;
  i && (i.callback = function(...s) {
    const u = n == null ? void 0 : n.apply(this, s);
    return o(), u;
  });
  const c = e.onRemoved;
  e.onRemoved = function(...s) {
    return a(), c == null ? void 0 : c.apply(this, s);
  }, e.__loadVideoUrlPreviewState = {
    sync: o,
    cleanup: a
  }, o();
}
const y = window.app;
y && y.registerExtension({
  name: "imagegen-toolkit-dev-utils.load-video-url-preview",
  beforeRegisterNodeDef(e, r) {
    if (r.name !== v)
      return;
    const t = e.prototype.onNodeCreated;
    e.prototype.onNodeCreated = function(...a) {
      const i = t == null ? void 0 : t.apply(this, a);
      return f(this), i;
    };
    const o = e.prototype.onConfigure;
    e.prototype.onConfigure = function(...a) {
      var n;
      const i = o == null ? void 0 : o.apply(this, a);
      return f(this), (n = this.__loadVideoUrlPreviewState) == null || n.sync(), i;
    };
  }
});
