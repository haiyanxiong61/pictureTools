const $ = (id) => document.getElementById(id);

let meta = { palettes: [], shapes: [], sample_words: "", sample_text: "" };
let shape = "ring";
let palette = "colorful";
let seed = 7;
let lastUrl = "";
let generating = false;

function setActive(container, id) {
  container.querySelectorAll(".chip").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === id);
  });
}

function renderChips(containerId, items, current, onPick) {
  const box = $(containerId);
  box.innerHTML = "";
  items.forEach((item) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip" + (item.id === current ? " active" : "");
    btn.dataset.id = item.id;
    btn.textContent = item.name;
    btn.addEventListener("click", () => {
      onPick(item.id);
      setActive(box, item.id);
    });
    box.appendChild(btn);
  });
}

function syncModeHint() {
  const article = $("mode").value === "article";
  $("text-title").textContent = article ? "粘贴文章" : "填词（越大的数字，字越大）";
  $("text").placeholder = article
    ? "把整段中文粘贴进来，软件会自动拆成词"
    : "小米 36\n汽车 32\n造车 28";
}

function payload() {
  const bg = $("export-bg").value || "white";
  let fmt = $("export-fmt").value || "png";
  if (bg === "transparent") fmt = "png";
  return {
    mode: $("mode").value,
    text: $("text").value,
    shape,
    palette,
    max_words: Number($("max-words").value) || 80,
    stopwords: $("stopwords").value,
    seed,
    background_mode: bg,
    format: fmt,
    filename: "我的词云",
  };
}

function syncExport() {
  const transparent = $("export-bg").value === "transparent";
  $("export-fmt").disabled = transparent;
  if (transparent) $("export-fmt").value = "png";
}

async function generate() {
  if (generating) return;
  generating = true;
  const status = $("status");
  const btn = $("btn-render");
  btn.disabled = true;
  status.classList.remove("error");
  status.textContent = "正在做词云，请稍等…";
  try {
    const res = await fetch("/api/wordcloud/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(data.error || "词云做不出来，请检查有没有填词");
    }
    const blob = await res.blob();
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = URL.createObjectURL(blob);
    $("chart").src = lastUrl;
    $("chart").hidden = false;
    $("empty").hidden = true;
    $("btn-download").disabled = false;
    status.textContent = "做好了。想换位置就点「换一换排布」，满意了再保存";
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  } finally {
    generating = false;
    btn.disabled = false;
  }
}

function showSaveResult(status, data) {
  if (data?.cancelled) {
    status.textContent = "已取消保存";
    return;
  }
  status.textContent = `已保存：${data.name}`;
}

async function save() {
  const status = $("status");
  const btn = $("btn-download");
  btn.disabled = true;
  status.classList.remove("error");
  status.textContent = "请选择要保存的位置…";
  const body = payload();
  try {
    const api = window.pywebview?.api;
    if (api?.save_wordcloud) {
      showSaveResult(status, await api.save_wordcloud(body));
      return;
    }
    const res = await fetch("/api/wordcloud/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "保存失败，请再点一次");
    showSaveResult(status, data);
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

function loadSample() {
  const article = $("mode").value === "article";
  $("text").value = article ? meta.sample_text : meta.sample_words;
  generate();
}

async function boot() {
  try {
    meta = await fetch("/api/wordcloud/meta").then((r) => r.json());
    renderChips("shapes", meta.shapes, shape, (id) => {
      shape = id;
      generate();
    });
    renderChips("palettes", meta.palettes, palette, (id) => {
      palette = id;
      generate();
    });
    $("mode").addEventListener("change", () => {
      syncModeHint();
      loadSample();
    });
    $("btn-sample").addEventListener("click", loadSample);
    $("btn-render").addEventListener("click", generate);
    $("btn-download").addEventListener("click", save);
    $("btn-shuffle").addEventListener("click", () => {
      seed = Math.floor(Math.random() * 10000);
      generate();
    });
    $("export-bg").addEventListener("change", () => {
      syncExport();
      generate();
    });
    $("export-fmt").addEventListener("change", generate);
    $("max-words").addEventListener("change", generate);
    syncModeHint();
    syncExport();
    $("text").value = meta.sample_words;
    generate();
  } catch (err) {
    $("status").classList.add("error");
    $("status").textContent = "页面出了点问题，请刷新后再试";
    console.error(err);
  }
}

window.addEventListener("pywebviewready", () => {
  window.pywebviewReady = true;
});

boot();
