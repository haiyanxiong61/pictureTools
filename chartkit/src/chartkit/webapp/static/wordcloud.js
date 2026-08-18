const $ = (id) => document.getElementById(id);

let meta = { palettes: [], shapes: [], sample_words: "", sample_text: "" };
let shape = "ring";
let palette = "colorful";
let seed = 7;
let rows = [];
let lastUrl = "";
let lastBlob = null;
let generating = false;
let textDirty = true;

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
      box.querySelectorAll(".chip").forEach((el) => {
        el.classList.toggle("active", el.dataset.id === item.id);
      });
    });
    box.appendChild(btn);
  });
}

function renderWordChips() {
  const box = $("word-chips");
  const count = $("word-count");
  if (!rows.length) {
    box.textContent = "点「拆词」后，词会出现在这里。点一下就能去掉。";
    count.textContent = "";
    return;
  }
  count.textContent = `共 ${rows.length} 个`;
  box.innerHTML = "";
  rows.forEach((row, index) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "word-chip";
    btn.textContent = `${row.word} ${row.count}`;
    btn.title = "点一下去掉这个词";
    btn.addEventListener("click", () => {
      rows.splice(index, 1);
      renderWordChips();
    });
    box.appendChild(btn);
  });
}

function payload(extra = {}) {
  const bg = $("export-bg").value || "white";
  const body = {
    mode: "auto",
    text: $("text").value,
    keep_words: $("keep-words").value,
    shape,
    palette,
    seed,
    background_mode: bg,
    format: "png",
    filename: "我的词云",
    ...extra,
  };
  if (rows.length && !textDirty) body.rows = rows;
  return body;
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

async function cutWords() {
  const status = $("status");
  status.classList.remove("error");
  status.textContent = "正在拆词…";
  try {
    const body = payload();
    delete body.rows;
    const res = await fetch("/api/wordcloud/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "拆词失败");
    rows = data.rows || [];
    textDirty = false;
    renderWordChips();
    status.textContent = `拆出 ${rows.length} 个词。不要的词点一下去掉，再点「看效果」`;
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  }
}

async function generate() {
  if (generating) return;
  generating = true;
  const status = $("status");
  $("btn-render").disabled = true;
  status.classList.remove("error");
  status.textContent = "正在做词云，请稍等…";
  try {
    if (!rows.length || textDirty) {
        const fresh = payload();
        delete fresh.rows;
        const analyzed = await fetch("/api/wordcloud/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(fresh),
        }).then((r) => r.json());
      if (analyzed.error) throw new Error(analyzed.error);
      rows = analyzed.rows || [];
      textDirty = false;
      renderWordChips();
    }
    const res = await fetch("/api/wordcloud/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(data.error || "词云做不出来，请检查左边有没有贴文字");
    }
    const blob = await res.blob();
    lastBlob = blob;
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = URL.createObjectURL(blob);
    $("chart").src = lastUrl;
    $("chart").hidden = false;
    $("empty").hidden = true;
    $("btn-download").disabled = false;
    status.textContent = "做好了。不要的词点一下去掉后再看效果，满意就保存";
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  } finally {
    generating = false;
    $("btn-render").disabled = false;
  }
}

async function save() {
  const status = $("status");
  $("btn-download").disabled = true;
  status.classList.remove("error");
  status.textContent = "请选择要保存的位置…";
  const bg = $("export-bg").value === "transparent" ? "透明底" : "白底";
  const filename = `我的词云_${bg}.png`;
  try {
    if (!lastBlob) throw new Error("请先点「看效果」");
    const data = await blobToBase64(lastBlob);
    const api = window.pywebview?.api;
    if (api?.save_file) {
      const result = await api.save_file(filename, data, "png");
      status.textContent = result?.cancelled ? "已取消保存" : `已保存：${result.name}`;
      if (!result?.cancelled) await keepInGallery(data);
      return;
    }
    const res = await fetch("/api/wordcloud/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename,
        data,
        format: "png",
        keep: true,
        shape,
        background_mode: $("export-bg").value,
      }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || "保存失败，请再点一次");
    status.textContent = body.cancelled ? "已取消保存" : `已保存：${body.name}`;
    await refreshGallery();
  } catch (err) {
    try {
      downloadBlob(lastBlob, filename);
      status.textContent = `已开始下载：${filename}`;
    } catch (_) {
      status.classList.add("error");
      status.textContent = err.message;
    }
  } finally {
    $("btn-download").disabled = false;
  }
}

async function keepInGallery(data) {
  await fetch("/api/wordcloud/keep", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      data,
      format: "png",
      shape,
      background_mode: $("export-bg").value,
    }),
  });
  await refreshGallery();
}

async function refreshGallery() {
  const box = $("gallery");
  const data = await fetch("/api/wordcloud/gallery").then((r) => r.json());
  const items = data.items || [];
  if (!items.length) {
    box.innerHTML = '<p class="empty">还没有保存过的图。保存图片后会出现在这里。</p>';
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
    card.querySelector(".js-del").addEventListener("click", async () => {
      await fetch(`/api/wordcloud/gallery/${encodeURIComponent(item.id)}`, { method: "DELETE" });
      refreshGallery();
    });
    box.appendChild(card);
  });
}

async function downloadGalleryItem(item) {
  const status = $("status");
  try {
    const res = await fetch(`/api/wordcloud/gallery/${encodeURIComponent(item.id)}`);
    if (!res.ok) throw new Error("这张图找不到了");
    const blob = await res.blob();
    const data = await blobToBase64(blob);
    const api = window.pywebview?.api;
    if (api?.save_file) {
      const result = await api.save_file(item.name, data, "png");
      status.textContent = result?.cancelled ? "已取消保存" : `已保存：${result.name}`;
      return;
    }
    const saveRes = await fetch("/api/wordcloud/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: item.name, data, format: "png", keep: false }),
    });
    const body = await saveRes.json().catch(() => ({}));
    if (!saveRes.ok) throw new Error(body.error || "下载失败");
    status.textContent = body.cancelled ? "已取消保存" : `已保存：${body.name}`;
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
    const res = await fetch("/api/wordcloud/gallery/zip");
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "打包失败" }));
      throw new Error(err.error || "打包失败");
    }
    const blob = await res.blob();
    const data = await blobToBase64(blob);
    const api = window.pywebview?.api;
    if (api?.save_file) {
      const result = await api.save_file("词云图库.zip", data, "zip");
      status.textContent = result?.cancelled ? "已取消保存" : `已保存：${result.name}`;
      return;
    }
    const saveRes = await fetch("/api/wordcloud/gallery/zip-save", { method: "POST" });
    const body = await saveRes.json().catch(() => ({}));
    if (saveRes.ok && !body.error) {
      status.textContent = body.cancelled ? "已取消保存" : `已保存：${body.name}`;
      return;
    }
    downloadBlob(blob, "词云图库.zip");
    status.textContent = "已开始下载：词云图库.zip";
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  }
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
    $("text").addEventListener("input", () => {
      textDirty = true;
    });
    $("keep-words").addEventListener("change", () => {
      textDirty = true;
    });
    $("btn-sample").addEventListener("click", () => {
      $("text").value = meta.sample_words;
      textDirty = true;
      rows = [];
      renderWordChips();
      generate();
    });
    $("btn-sample-text").addEventListener("click", () => {
      $("text").value = meta.sample_text;
      textDirty = true;
      rows = [];
      renderWordChips();
      cutWords();
    });
    $("btn-cut").addEventListener("click", cutWords);
    $("btn-render").addEventListener("click", generate);
    $("btn-download").addEventListener("click", save);
    $("btn-shuffle").addEventListener("click", () => {
      seed = Math.floor(Math.random() * 10000);
      generate();
    });
    $("btn-zip").addEventListener("click", downloadZip);
    $("btn-open-gallery").addEventListener("click", async () => {
      const data = await fetch("/api/wordcloud/gallery/open", { method: "POST" }).then((r) => r.json());
      $("status").textContent = `图库文件夹：${data.folder}`;
    });
    $("export-bg").addEventListener("change", generate);
    $("text").value = meta.sample_words;
    await refreshGallery();
    generate();
  } catch (err) {
    $("status").classList.add("error");
    $("status").textContent = "页面出了点问题，请刷新后再试";
    console.error(err);
  }
}

boot();
