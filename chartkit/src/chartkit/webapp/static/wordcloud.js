const $ = (id) => document.getElementById(id);

let meta = { palettes: [], shapes: [], layouts: [], sample_rows: [], sample_text: "" };
let mode = "words";
let shape = "ring";
let palette = "colorful";
let layout = "0.65";
let seed = 7;
let rows = [];
let lastUrl = "";
let lastBlob = null;
let generating = false;

function setActive(container, id, key = "id") {
  container.querySelectorAll(".chip").forEach((el) => {
    el.classList.toggle("active", el.dataset[key] === id);
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

function syncMode() {
  $("article-block").classList.toggle("hidden", mode !== "article");
  document.querySelectorAll("#mode-chips .chip").forEach((el) => {
    el.classList.toggle("active", el.dataset.mode === mode);
  });
}

function renderTable() {
  const body = $("word-table").querySelector("tbody");
  body.innerHTML = "";
  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="3" class="empty">还没有词。自己加一个，或粘贴文章后点「拆成词表」</td>';
    body.appendChild(tr);
    return;
  }
  rows.forEach((row, index) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input class="word" value="${escapeAttr(row.word)}" /></td>
      <td><input class="count" type="number" min="1" step="1" value="${row.count}" /></td>
      <td><button type="button" class="del">删除</button></td>
    `;
    tr.querySelector(".word").addEventListener("input", (e) => {
      rows[index].word = e.target.value;
    });
    tr.querySelector(".count").addEventListener("input", (e) => {
      rows[index].count = Number(e.target.value) || 1;
    });
    tr.querySelector(".del").addEventListener("click", () => {
      rows.splice(index, 1);
      renderTable();
    });
    body.appendChild(tr);
  });
}

function escapeAttr(value) {
  return String(value ?? "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function exportChoices() {
  const bg = $("export-bg").value || "white";
  let fmt = $("export-fmt").value || "png";
  if (bg === "transparent") fmt = "png";
  const name = ($("filename").value || "我的词云").replace(/[\\/:*?"<>|]/g, "");
  const bgName = bg === "transparent" ? "透明底" : "白底";
  return { bg, fmt, filename: `${name}_${bgName}.${fmt}` };
}

function payload(extra = {}) {
  const { bg, fmt } = exportChoices();
  return {
    mode,
    text: $("article").value,
    rows: rows.filter((row) => String(row.word || "").trim()),
    shape,
    palette,
    max_words: Number($("max-words").value) || 80,
    stopwords: $("stopwords").value,
    seed,
    scale: Number($("scale").value) || 1.4,
    prefer_horizontal: Number(layout) || 0.65,
    background_mode: bg,
    format: fmt,
    filename: $("filename").value || "我的词云",
    ...extra,
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
  const res = await fetch("/api/wordcloud/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, data, format: fmt, keep: true, ...payload(), ...extra }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || "导出失败，请再点一次");
  showSaveResult(status, body);
  await refreshGallery();
}

async function generate() {
  if (generating) return;
  if (!rows.filter((row) => String(row.word || "").trim()).length) {
    $("status").classList.add("error");
    $("status").textContent = "词表是空的。请先加词，或粘贴文章后点「拆成词表」";
    return;
  }
  generating = true;
  const status = $("status");
  $("btn-render").disabled = true;
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
      throw new Error(data.error || "词云做不出来，请检查词表");
    }
    const blob = await res.blob();
    lastBlob = blob;
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = URL.createObjectURL(blob);
    $("chart").src = lastUrl;
    $("chart").hidden = false;
    $("empty").hidden = true;
    $("btn-download").disabled = false;
    $("btn-keep").disabled = false;
    status.textContent = "做好了。可以换排布、导出这张图，或放入图库";
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  } finally {
    generating = false;
    $("btn-render").disabled = false;
  }
}

async function exportCurrent() {
  const status = $("status");
  $("btn-download").disabled = true;
  status.classList.remove("error");
  status.textContent = "请选择要保存的位置…";
  const { filename } = exportChoices();
  try {
    if (!lastBlob) throw new Error("还没有图，请先点「看效果」");
    const api = window.pywebview?.api;
    try {
      await saveWithDialog(filename, lastBlob);
      if (api?.save_file) await keepCurrent(false);
    } catch (_) {
      downloadBlob(lastBlob, filename);
      status.textContent = `已开始下载：${filename}`;
      await keepCurrent(false);
    }
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  } finally {
    $("btn-download").disabled = false;
  }
}

async function keepCurrent(showMsg = true) {
  if (!lastBlob) throw new Error("还没有图，请先点「看效果」");
  const { fmt, bg } = exportChoices();
  const data = await blobToBase64(lastBlob);
  const res = await fetch("/api/wordcloud/keep", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ data, format: fmt, background_mode: bg, shape }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || "放入图库失败");
  await refreshGallery();
  if (showMsg) {
    $("status").classList.remove("error");
    $("status").textContent = `已放入图库：${body.name}`;
  }
}

async function cutArticle() {
  const status = $("status");
  status.classList.remove("error");
  status.textContent = "正在拆词…";
  try {
    const res = await fetch("/api/wordcloud/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: "article",
        text: $("article").value,
        stopwords: $("stopwords").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "拆词失败");
    rows = data.rows || [];
    renderTable();
    status.textContent = `拆出 ${rows.length} 个词，可在表格里改，再点「看效果」`;
    if (rows.length) generate();
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  }
}

async function importFile(file) {
  const text = await file.text();
  const name = (file.name || "").toLowerCase();
  const asWords = name.endsWith(".csv") || name.endsWith(".tsv") || /[,，\t]\s*\d+\s*$/m.test(text);
  if (asWords) {
    const res = await fetch("/api/wordcloud/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "words", text, stopwords: $("stopwords").value }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "文件读不出来");
    rows = data.rows || [];
    mode = "words";
    syncMode();
    renderTable();
    generate();
    return;
  }
  $("article").value = text;
  mode = "article";
  syncMode();
  await cutArticle();
}

async function refreshGallery() {
  const box = $("gallery");
  const data = await fetch("/api/wordcloud/gallery").then((r) => r.json());
  const items = data.items || [];
  if (!items.length) {
    box.innerHTML = '<p class="empty">图库还是空的。做出图后点「导出这张图」或「放入图库」。</p>';
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
      <div class="gallery-btns">
        <button type="button" class="mini js-down">下载</button>
        <button type="button" class="del js-del">删除</button>
      </div>
    `;
    card.querySelector(".js-down").addEventListener("click", () => downloadGalleryItem(item));
    card.querySelector(".js-del").addEventListener("click", () => deleteGalleryItem(item));
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
      await saveWithDialog(item.name, blob, { keep: false });
    } catch (_) {
      downloadBlob(blob, item.name);
      status.textContent = `已开始下载：${item.name}`;
    }
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  }
}

async function deleteGalleryItem(item) {
  await fetch(`/api/wordcloud/gallery/${encodeURIComponent(item.id)}`, { method: "DELETE" });
  await refreshGallery();
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
      await saveWithDialog("词云图库.zip", blob, { keep: false });
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
  rows = (meta.sample_rows || []).map((row) => ({ ...row }));
  $("article").value = meta.sample_text || "";
  renderTable();
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
    renderChips("layouts", meta.layouts || [], layout, (id) => {
      layout = id;
      generate();
    });
    document.querySelectorAll("#mode-chips .chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        mode = btn.dataset.mode;
        syncMode();
      });
    });
    $("btn-sample").addEventListener("click", loadSample);
    $("btn-cut").addEventListener("click", cutArticle);
    $("add-word").addEventListener("click", () => {
      rows.push({ word: `词${rows.length + 1}`, count: 8 });
      renderTable();
    });
    $("file").addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      e.target.value = "";
      if (!file) return;
      try {
        await importFile(file);
      } catch (err) {
        $("status").classList.add("error");
        $("status").textContent = err.message;
      }
    });
    $("btn-render").addEventListener("click", generate);
    $("btn-download").addEventListener("click", exportCurrent);
    $("btn-keep").addEventListener("click", () => keepCurrent(true).catch((err) => {
      $("status").classList.add("error");
      $("status").textContent = err.message;
    }));
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
    $("scale").addEventListener("change", generate);
    syncMode();
    syncExport();
    rows = (meta.sample_rows || []).map((row) => ({ ...row }));
    $("article").value = meta.sample_text || "";
    renderTable();
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
