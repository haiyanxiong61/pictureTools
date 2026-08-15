const STORE_KEY = "chartkit.spec.v3";
const LIST_KINDS = new Set(["histogram", "box"]);
const NO_CAT_KINDS = new Set(["histogram", "box", "gauge"]);

const state = {
  kind: "combo",
  theme: "academic",
  title: "",
  filename: "chart",
  xlabel: "",
  ylabel: "",
  y2label: "",
  bar_mode: "percent",
  figsize: [10.5, 6.4],
  dpi: 200,
  rotate_xticks: 0,
  y_lim: [null, null],
  y2_lim: [0, 1],
  bins: 8,
  background: "",
  show_bar_labels: true,
  show_line_labels: true,
  show_counts: true,
  legend: true,
  grid: true,
  categories: ["人物", "叙述角度", "情节"],
  series: [
    { name: "neg", values: [187, 3, 84] },
    { name: "neu", values: [12, 0, 9] },
    { name: "pos", values: [409, 184, 301] },
  ],
  lines: [
    { name: "pos_average", values: [0.63, 0.91, 0.79] },
    { name: "neg_average", values: [0.37, 0.09, 0.21] },
  ],
};

let lastBlobUrl = "";
let lastBlob = null;
let lastFmt = "png";
let meta = { types: [], themes: [], presets: [] };
let debounceTimer = 0;
let generating = false;

const $ = (id) => document.getElementById(id);

function hide(id, on) {
  const node = $(id);
  if (node) node.classList.toggle("hidden", on);
}

function toRows(obj) {
  return Object.entries(obj || {}).map(([name, values]) => ({
    name,
    values: (values || []).map(Number),
  }));
}

function fromRows(rows) {
  const out = {};
  for (const row of rows) {
    if (!row.name) continue;
    out[row.name] = (row.values || []).map((v) => (v === "" || v === null ? 0 : Number(v)));
  }
  return out;
}

function editorMode() {
  if (state.kind === "gauge") return "gauge";
  if (LIST_KINDS.has(state.kind)) return "lists";
  return "grid";
}

function applyMapping(data, generateNow = true) {
  state.kind = data.kind || state.kind;
  state.theme = data.theme || state.theme;
  state.title = data.title || "";
  state.filename = data.filename || state.filename || "chart";
  state.xlabel = data.xlabel || "";
  state.ylabel = data.ylabel || "";
  state.y2label = data.y2label || "";
  state.bar_mode = data.bar_mode || (state.kind === "combo" ? "percent" : "grouped");
  state.figsize = data.figsize || state.figsize;
  state.dpi = data.dpi || state.dpi;
  state.rotate_xticks = data.rotate_xticks || 0;
  state.y_lim = data.y_lim || [null, null];
  state.y2_lim = data.y2_lim || [0, 1];
  state.bins = data.bins || state.bins;
  state.background = data.background || "";
  state.show_bar_labels = data.show_bar_labels !== false;
  state.show_line_labels = data.show_line_labels !== false;
  state.show_counts = data.show_counts !== false;
  state.legend = data.legend !== false;
  state.grid = data.grid !== false;
  if (data.categories) state.categories = [...data.categories];
  if (data.series) state.series = toRows(data.series);
  if (data.lines) state.lines = toRows(data.lines);
  else if (data.kind && data.kind !== "combo") state.lines = state.lines;
  syncForm();
  renderAll();
  persist();
  if (generateNow) generate();
}

function applyPreset(preset) {
  const select = $("preset");
  if (select && preset.id) select.value = preset.id;
  applyMapping(preset, true);
}

function pickType(id) {
  state.kind = id;
  if (id === "combo" && !state.lines.length) {
    state.lines = [{ name: "均值", values: state.categories.map(() => 0.5) }];
  }
  if (id === "gauge" && !state.series.length) {
    state.series = [{ name: "值", values: [70] }];
  }
  persist();
  syncForm();
  generate();
}

function pickTheme(id) {
  state.theme = id;
  persist();
  syncForm();
  generate();
}

function readInputsToState() {
  state.title = $("title").value;
  state.filename = $("filename").value.trim() || "chart";
  state.xlabel = $("xlabel").value;
  state.ylabel = $("ylabel").value;
  state.y2label = $("y2label").value;
  state.bar_mode = $("bar-mode").value;
  state.figsize = [Number($("fig-w").value) || 10.5, Number($("fig-h").value) || 6.4];
  state.dpi = Number($("dpi").value) || 200;
  state.rotate_xticks = Number($("rotate").value) || 0;
  state.bins = Number($("bins").value) || 8;
  state.background = $("bg").value.trim();
  const ymin = $("ymin").value;
  const ymax = $("ymax").value;
  state.y_lim = [ymin === "" ? null : Number(ymin), ymax === "" ? null : Number(ymax)];
  const y2min = $("y2min").value;
  const y2max = $("y2max").value;
  state.y2_lim = [y2min === "" ? null : Number(y2min), y2max === "" ? null : Number(y2max)];
  state.show_bar_labels = $("show-bar-labels").checked;
  state.show_line_labels = $("show-line-labels").checked;
  state.show_counts = $("show-counts").checked;
  state.legend = $("show-legend").checked;
  state.grid = $("show-grid").checked;
  if (state.kind === "gauge") {
    state.series = [{ name: "值", values: [Number($("gauge-value").value) || 0] }];
    state.y_lim = [Number($("gauge-min").value) || 0, Number($("gauge-max").value) || 100];
  }
}

function syncForm() {
  $("title").value = state.title;
  $("filename").value = state.filename || "chart";
  $("xlabel").value = state.xlabel;
  $("ylabel").value = state.ylabel;
  $("y2label").value = state.y2label;
  $("bar-mode").value = state.bar_mode;
  $("fig-w").value = state.figsize[0];
  $("fig-h").value = state.figsize[1];
  $("dpi").value = state.dpi;
  $("rotate").value = state.rotate_xticks;
  $("bins").value = state.bins;
  $("bg").value = state.background;
  $("ymin").value = state.y_lim?.[0] ?? "";
  $("ymax").value = state.y_lim?.[1] ?? "";
  $("y2min").value = state.y2_lim?.[0] ?? "";
  $("y2max").value = state.y2_lim?.[1] ?? "";
  $("show-bar-labels").checked = state.show_bar_labels;
  $("show-line-labels").checked = state.show_line_labels;
  $("show-counts").checked = state.show_counts;
  $("show-legend").checked = state.legend;
  $("show-grid").checked = state.grid;
  const combo = state.kind === "combo";
  const mode = editorMode();
  hide("bar-mode-wrap", !["bar", "hbar", "combo", "area"].includes(state.kind));
  hide("y2-wrap", !combo);
  hide("y2min-wrap", !combo);
  hide("y2max-wrap", !combo);
  hide("bins-wrap", state.kind !== "histogram");
  hide("lines-block", !combo);
  hide("cat-block", NO_CAT_KINDS.has(state.kind));
  hide("gauge-block", mode !== "gauge");
  hide("series-block", mode === "gauge");
  hide("grid-wrap", mode !== "grid");
  hide("list-wrap", mode !== "lists");
  hide("add-series", mode === "gauge");
  $("series-title").textContent = mode === "lists" ? "一串数字，用逗号隔开" : "填数字";
  if (mode === "gauge") {
    $("gauge-value").value = state.series[0]?.values?.[0] ?? 70;
    $("gauge-min").value = state.y_lim?.[0] ?? 0;
    $("gauge-max").value = state.y_lim?.[1] ?? 100;
  }
  document.querySelectorAll("#types .chip").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === state.kind);
  });
  document.querySelectorAll("#themes .chip").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === state.theme);
  });
  renderCategories();
  renderTable("series-table", state.series, (rows) => { state.series = rows; });
  renderTable("lines-table", state.lines, (rows) => { state.lines = rows; });
  renderLists();
}

function renderCategories() {
  const box = $("categories");
  box.innerHTML = "";
  state.categories.forEach((cat, i) => {
    const wrap = document.createElement("div");
    wrap.className = "cat-item";
    const input = document.createElement("input");
    input.value = cat;
    input.dataset.catIndex = String(i);
    input.addEventListener("input", () => {
      renameCategory(i, input.value);
    });
    const del = document.createElement("button");
    del.className = "del";
    del.type = "button";
    del.textContent = "×";
    del.addEventListener("click", () => {
      if (state.categories.length <= 1) return;
      state.categories.splice(i, 1);
      state.series.forEach((row) => row.values.splice(i, 1));
      state.lines.forEach((row) => row.values.splice(i, 1));
      syncForm();
      scheduleGenerate();
    });
    wrap.append(input, del);
    box.appendChild(wrap);
  });
}

function renameCategory(index, value) {
  state.categories[index] = value;
  document.querySelectorAll(`[data-cat-index="${index}"]`).forEach((el) => {
    if (el !== document.activeElement) el.value = value;
  });
  scheduleGenerate();
}

function renderTable(tableId, rows, onChange) {
  const table = $(tableId);
  const cats = state.categories.length ? state.categories : ["值"];
  table.innerHTML = "";
  const head = document.createElement("tr");
  const nameTh = document.createElement("th");
  nameTh.textContent = "这一组叫什么";
  head.appendChild(nameTh);
  cats.forEach((cat, i) => {
    const th = document.createElement("th");
    const input = document.createElement("input");
    input.value = cat;
    input.dataset.catIndex = String(i);
    input.title = "修改分类名称";
    input.addEventListener("input", () => renameCategory(i, input.value));
    th.appendChild(input);
    head.appendChild(th);
  });
  head.appendChild(document.createElement("th"));
  table.appendChild(head);
  rows.forEach((row, r) => {
    while (row.values.length < cats.length) row.values.push(0);
    if (!LIST_KINDS.has(state.kind)) row.values = row.values.slice(0, cats.length);
    const tr = document.createElement("tr");
    const nameTd = document.createElement("td");
    nameTd.className = "row-name";
    const nameInput = document.createElement("input");
    nameInput.value = row.name;
    nameInput.addEventListener("input", () => {
      rows[r].name = nameInput.value;
      onChange(rows);
      scheduleGenerate();
    });
    nameTd.appendChild(nameInput);
    tr.appendChild(nameTd);
    cats.forEach((_, c) => {
      const td = document.createElement("td");
      const input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.value = row.values[c] ?? 0;
      input.addEventListener("input", () => {
        rows[r].values[c] = input.value === "" ? 0 : Number(input.value);
        onChange(rows);
        scheduleGenerate();
      });
      td.appendChild(input);
      tr.appendChild(td);
    });
    const delTd = document.createElement("td");
    const del = document.createElement("button");
    del.className = "del";
    del.type = "button";
    del.textContent = "去掉";
    del.addEventListener("click", () => {
      rows.splice(r, 1);
      onChange(rows);
      syncForm();
      scheduleGenerate();
    });
    delTd.appendChild(del);
    tr.appendChild(delTd);
    table.appendChild(tr);
  });
}

function renderLists() {
  const box = $("list-wrap");
  box.innerHTML = "";
  state.series.forEach((row, r) => {
    const wrap = document.createElement("div");
    wrap.className = "list-row";
    const name = document.createElement("input");
    name.value = row.name;
    name.addEventListener("input", () => {
      state.series[r].name = name.value;
      scheduleGenerate();
    });
    const values = document.createElement("input");
    values.value = row.values.join(", ");
    values.placeholder = "0.62, 0.71, 0.80";
    values.addEventListener("input", () => {
      state.series[r].values = values.value
        .split(/[,，\s]+/)
        .filter((part) => part !== "")
        .map(Number);
      scheduleGenerate();
    });
    const del = document.createElement("button");
    del.className = "del";
    del.type = "button";
    del.textContent = "去掉";
    del.addEventListener("click", () => {
      state.series.splice(r, 1);
      syncForm();
      scheduleGenerate();
    });
    wrap.append(name, values, del);
    box.appendChild(wrap);
  });
}

function renderChips(boxId, items, current, onPick) {
  const box = $(boxId);
  box.innerHTML = "";
  items.forEach((item) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip" + (item.id === current ? " active" : "");
    btn.dataset.id = item.id;
    btn.textContent = item.name;
    if (item.hint) btn.title = item.hint;
    btn.addEventListener("click", () => onPick(item.id));
    box.appendChild(btn);
  });
}

function collectSpec() {
  readInputsToState();
  const spec = {
    kind: state.kind,
    theme: state.theme,
    title: state.title,
    xlabel: state.xlabel,
    ylabel: state.ylabel,
    y2label: state.y2label,
    bar_mode: state.bar_mode,
    figsize: state.figsize,
    dpi: state.dpi,
    rotate_xticks: state.rotate_xticks,
    bins: state.bins,
    show_bar_labels: state.show_bar_labels,
    show_line_labels: state.show_line_labels,
    show_counts: state.show_counts,
    legend: state.legend,
    grid: state.grid,
    categories: [...state.categories],
    series: fromRows(state.series),
  };
  if (state.background) spec.background = state.background;
  if (state.y_lim && (state.y_lim[0] !== null || state.y_lim[1] !== null)) {
    if (state.y_lim[0] !== null && state.y_lim[1] !== null) spec.y_lim = state.y_lim;
  }
  if (state.kind === "combo") {
    spec.lines = fromRows(state.lines);
    if (state.y2_lim[0] !== null && state.y2_lim[1] !== null) spec.y2_lim = state.y2_lim;
  }
  if (state.kind === "gauge" && state.y_lim[0] !== null && state.y_lim[1] !== null) {
    spec.y_lim = state.y_lim;
  }
  return spec;
}

function persist() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(collectSpec()));
  } catch (_) {
    /* ignore quota */
  }
}

function scheduleGenerate() {
  persist();
  const auto = $("auto-render");
  if (auto && !auto.checked) return;
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(generate, 380);
}

async function generate() {
  if (generating) return;
  generating = true;
  const status = $("status");
  const btn = $("btn-render");
  btn.disabled = true;
  status.classList.remove("error");
  status.textContent = "正在画图，请稍等…";
  const fmt = $("fmt").value || "png";
  try {
    const res = await fetch(`/api/render?fmt=${encodeURIComponent(fmt)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectSpec()),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(data.error || "图画不出来，请检查数字有没有填错");
    }
    const blob = await res.blob();
    if (lastBlobUrl) URL.revokeObjectURL(lastBlobUrl);
    lastBlob = blob;
    lastFmt = fmt;
    lastBlobUrl = URL.createObjectURL(blob);
    const img = $("chart");
    if (fmt === "pdf") {
      img.hidden = true;
      $("empty").hidden = false;
      $("empty").textContent = "图已经准备好，请点下载";
    } else {
      img.src = lastBlobUrl;
      img.hidden = false;
      $("empty").hidden = true;
    }
    $("btn-download").disabled = false;
    status.textContent = "画好了。改数字后图会自己变，满意了就下载";
    persist();
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  } finally {
    generating = false;
    btn.disabled = false;
  }
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function exportChoices() {
  const bg = $("export-bg")?.value || "white";
  let fmt = $("export-fmt")?.value || "png";
  if (bg === "transparent") fmt = "png";
  return { bg, fmt };
}

function syncExportOptions() {
  const bg = $("export-bg");
  const fmt = $("export-fmt");
  if (!bg || !fmt) return;
  const transparent = bg.value === "transparent";
  fmt.disabled = transparent;
  if (transparent) fmt.value = "png";
}

async function fetchImage(bg, fmt) {
  const res = await fetch(`/api/render?fmt=${encodeURIComponent(fmt)}&bg=${encodeURIComponent(bg)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectSpec()),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(data.error || "下载失败，请再点一次");
  }
  const blob = await res.blob();
  const ext = (res.headers.get("content-type") || "").includes("svg")
    ? "svg"
    : (res.headers.get("content-type") || "").includes("pdf")
      ? "pdf"
      : (res.headers.get("content-type") || "").includes("jpeg")
        ? "jpg"
        : "png";
  return { blob, ext };
}

async function download() {
  const status = $("status");
  const btn = $("btn-download");
  btn.disabled = true;
  status.classList.remove("error");
  const { bg, fmt } = exportChoices();
  const bgName = bg === "transparent" ? "透明底" : "白底";
  status.textContent = `正在保存${bgName}的 ${fmt.toUpperCase()} 图片…`;
  try {
    const name = (state.title || state.filename || "我的图表").replace(/[\\/:*?"<>|]/g, "");
    const file = await fetchImage(bg, fmt);
    saveBlob(file.blob, `${name}_${bgName}.${file.ext}`);
    status.textContent = `已保存：${name}_${bgName}.${file.ext}。请到「下载」文件夹里找`;
  } catch (err) {
    status.classList.add("error");
    status.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

async function importText(text, filename = "") {
  const res = await fetch("/api/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, filename }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "导入失败");
  applyMapping({ ...collectSpec(), ...data }, true);
}

function renderAll() {
  renderChips("types", meta.types, state.kind, pickType);
  renderChips("themes", meta.themes, state.theme, pickTheme);
  syncForm();
}

async function boot() {
  try {
  meta = await fetch("/api/meta").then((r) => r.json());
  const select = $("preset");
  select.innerHTML = '<option value="">请先选一个例子</option>' +
    meta.presets.map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
  select.addEventListener("change", () => {
    const preset = meta.presets.find((p) => p.id === select.value);
    if (preset) applyPreset(preset);
  });

  [
    "title", "filename", "xlabel", "ylabel", "y2label", "fig-w", "fig-h", "dpi",
    "rotate", "ymin", "ymax", "y2min", "y2max", "bins", "bg", "gauge-value",
    "gauge-min", "gauge-max",
  ].forEach((id) => $(id).addEventListener("input", scheduleGenerate));
  ["bar-mode", "fmt"].forEach((id) => $(id).addEventListener("change", () => {
    if (id === "fmt") generate();
    else scheduleGenerate();
  }));
  ["show-bar-labels", "show-line-labels", "show-counts", "show-legend", "show-grid"].forEach((id) => {
    $(id).addEventListener("change", scheduleGenerate);
  });

  $("add-cat").addEventListener("click", () => {
    state.categories.push(`第${state.categories.length + 1}项`);
    state.series.forEach((row) => row.values.push(0));
    state.lines.forEach((row) => row.values.push(0));
    syncForm();
    scheduleGenerate();
  });
  $("add-series").addEventListener("click", () => {
    const values = editorMode() === "lists" ? [0.5, 0.6, 0.7] : state.categories.map(() => 0);
    state.series.push({ name: `第${state.series.length + 1}组`, values });
    syncForm();
    scheduleGenerate();
  });
  $("add-line").addEventListener("click", () => {
    state.lines.push({ name: `第${state.lines.length + 1}条线`, values: state.categories.map(() => 0) });
    syncForm();
    scheduleGenerate();
  });
  $("btn-render").addEventListener("click", generate);
  $("btn-download").addEventListener("click", download);
  $("export-bg")?.addEventListener("change", syncExportOptions);
  $("export-fmt")?.addEventListener("change", syncExportOptions);
  syncExportOptions();
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      generate();
    }
  });

  renderAll();
  let restored = null;
  try {
    restored = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
  } catch (_) {
    restored = null;
  }
  if (restored?.series) applyMapping(restored, true);
  else if (meta.presets[0]) applyPreset(meta.presets[0]);
  else generate();
  } catch (err) {
    const status = $("status");
    if (status) {
      status.classList.add("error");
      status.textContent = "页面出了点问题，请刷新后再试";
    }
    console.error(err);
  }
}

boot();
