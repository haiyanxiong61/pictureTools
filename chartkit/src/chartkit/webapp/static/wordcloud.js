const $ = (id) => document.getElementById(id);

let meta = { palettes: [], shapes: [], sample_words: "" };
let shape = "ring";
let palette = "colorful";
let seed = 7;
let lastUrl = "";
let lastBlob = null;
let generating = false;

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

function payload() {
  const bg = $("export-bg").value || "white";
  return {
    mode: "auto",
    text: $("text").value,
    shape,
    palette,
    seed,
    background_mode: bg,
    format: "png",
    filename: "我的词云",
  };
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

async function generate() {
  if (generating) return;
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
    status.textContent = "做好了。满意就保存图片，想换位置就点「换一换」";
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
      return;
    }
    const res = await fetch("/api/wordcloud/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, data, format: "png", keep: false }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || "保存失败，请再点一次");
    status.textContent = body.cancelled ? "已取消保存" : `已保存：${body.name}`;
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
    $("btn-sample").addEventListener("click", () => {
      $("text").value = meta.sample_words;
      generate();
    });
    $("btn-render").addEventListener("click", generate);
    $("btn-download").addEventListener("click", save);
    $("btn-shuffle").addEventListener("click", () => {
      seed = Math.floor(Math.random() * 10000);
      generate();
    });
    $("export-bg").addEventListener("change", generate);
    $("text").value = meta.sample_words;
    generate();
  } catch (err) {
    $("status").classList.add("error");
    $("status").textContent = "页面出了点问题，请刷新后再试";
    console.error(err);
  }
}

boot();
