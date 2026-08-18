const $ = (id) => document.getElementById(id);

let meta = { palettes: [], shapes: [], sample_words: "", sample_text: "" };
let shape = "ring";
let palette = "colorful";
let seed = 7;
let lastUrl = "";
let lastBlob = null;
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

function exportName() {
  const bg = $("export-bg").value === "transparent" ? "透明底" : "白底";
  const fmt = $("export-fmt").disabled ? "png" : ($("export-fmt").value || "png");
  return { filename: `我的词云_${bg}.${fmt}`, fmt, bg };
}

function payload() {
  const { fmt } = exportName();
  const bg = $("export-bg").value || "white";
  return {
    mode: $("mode").value,
    text: $("text").value,
    shape,
    palette,
    max_words: Number($("max-words").value) || 80,
    stopwords: $("stopwords").value,
    seed,
    background_mode: bg,
    format: bg === "transparent" ? "png" : fmt,
    filename: "我的词云",
  };
}

function syncExport() {
  const transparent = $("export-bg").value === "transparent";
  $("export-fmt").disabled = transparent;
  if (transparent) $("export-fmt").value = "png";
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function showSaveResult(status, data) {
  if (data?.cancelled) {
    status.textContent = "已取消保存";
    return;
  }
  status.textContent = `已导出：${data.name}`;
}

async function saveWithDialog(filename, blob, extra = {}) {
  const status = $("status");
  const fmt = filename.split(".").pop() || "png";
  const data = await blobToBase64(blob);
  const api = window.pywebview?.api;
  if (api?.save_file) {
    return showSaveResult(status, await api.save_file(filename, data, fmt));
  }
  if (api?.save_wordcloud) {
    return showSaveResult(status, await api.save_wordcloud({ filename, data, format: fmt, ...extra }));
  }
  const res = await fetch("/api/wordcloud/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, data, format: fmt, ...extra }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || "导出失败，请再点一次");
  showSaveResult(status, body);
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
    lastBlob = blob;
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = URL.createObjectURL(blob);
    $("chart").src = lastUrl;
    $("chart").hidden = false;
    $("empty").hidden = true;
    $("btn-download").disabled = false;
    status.textContent = "做好了，已放入图库。可以导出这张，或打包下载全部";
    await refreshGallery();
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  } finally {
    generating = false;
    btn.disabled = false;
  }
}

async function exportCurrent() {
  const status = $("status");
  const btn = $("btn-download");
  btn.disabled = true;
  status.classList.remove("error");
  status.textContent = "请选择要保存的位置…";
  const { filename } = exportName();
  try {
    if (!lastBlob) throw new Error("还没有图，请先点「看效果」");
    try {
      await saveWithDialog(filename, lastBlob);
    } catch (_) {
      downloadBlob(lastBlob, filename);
      status.textContent = `已开始下载：${filename}`;
    }
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

async function refreshGallery() {
  const box = $("gallery");
  const data = await fetch("/api/wordcloud/gallery").then((r) => r.json());
  const items = data.items || [];
  if (!items.length) {
    box.innerHTML = '<p class="empty">图库还是空的。做出词云后，会出现在这里。</p>';
    $("btn-zip").disabled = true;
    return;
  }
  $("btn-zip").disabled = false;
  box.innerHTML = "";
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "gallery-card";
    card.innerHTML = `
      <img src="${item.url}" alt="${item.name}" />
      <div class="gallery-name" title="${item.name}">${item.name}</div>
      <button type="button" class="mini">下载这张</button>
    `;
    card.querySelector("button").addEventListener("click", () => downloadGalleryItem(item));
    box.appendChild(card);
  });
}

async function downloadGalleryItem(item) {
  const status = $("status");
  status.classList.remove("error");
  status.textContent = "请选择要保存的位置…";
  try {
    const res = await fetch(`/api/wordcloud/gallery/${encodeURIComponent(item.id)}`);
    if (!res.ok) throw new Error("这张图找不到了");
    const blob = await res.blob();
    try {
      await saveWithDialog(item.name, blob);
    } catch (_) {
      downloadBlob(blob, item.name);
      status.textContent = `已开始下载：${item.name}`;
    }
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  }
}

async function downloadZip() {
  const status = $("status");
  status.classList.remove("error");
  status.textContent = "正在打包图库…";
  try {
    const api = window.pywebview?.api;
    const res = await fetch("/api/wordcloud/gallery/zip");
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "打包失败" }));
      throw new Error(err.error || "打包失败");
    }
    const blob = await res.blob();
    if (api?.save_file) {
      const encoded = await blobToBase64(blob);
      showSaveResult(status, await api.save_file("词云图库.zip", encoded, "zip"));
      return;
    }
    try {
      await saveWithDialog("词云图库.zip", blob);
    } catch (_) {
      downloadBlob(blob, "词云图库.zip");
      status.textContent = "已开始下载：词云图库.zip";
    }
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  }
}

async function openGallery() {
  const status = $("status");
  try {
    const data = await fetch("/api/wordcloud/gallery/open", { method: "POST" }).then((r) => r.json());
    status.classList.remove("error");
    status.textContent = `图库文件夹：${data.folder}`;
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
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
    $("btn-download").addEventListener("click", exportCurrent);
    $("btn-shuffle").addEventListener("click", () => {
      seed = Math.floor(Math.random() * 10000);
      generate();
    });
    $("btn-zip").addEventListener("click", downloadZip);
    $("btn-open-gallery").addEventListener("click", openGallery);
    $("export-bg").addEventListener("change", () => {
      syncExport();
      generate();
    });
    $("export-fmt").addEventListener("change", generate);
    $("max-words").addEventListener("change", generate);
    syncModeHint();
    syncExport();
    $("text").value = meta.sample_words;
    await refreshGallery();
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
