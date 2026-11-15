"""flac-hunter Web GUI 前端页面（单文件内嵌，纯 HTML/CSS/JS，无外部资源）。

后端见仓库根 gui.py；API：/api/state /api/prepare /api/download /api/upgrade
/api/audit /api/job/<id> /api/tracks。本文件只是一个大字符串常量。
"""

PAGE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>flac-hunter</title>
<style>
:root {
  --bg: #0d1117; --panel: #161b22; --border: #30363d; --text: #e6edf3;
  --dim: #8b949e; --accent: #d29922; --green: #3fb950; --red: #f85149;
  --blue: #58a6ff; --chip: #21262d;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
       font: 14px/1.5 "Segoe UI", "Microsoft YaHei", sans-serif; }
header { display: flex; align-items: center; gap: 16px; padding: 12px 20px;
         border-bottom: 1px solid var(--border); position: sticky; top: 0;
         background: var(--bg); z-index: 5; }
header h1 { font-size: 18px; margin: 0; color: var(--accent); }
header .stat { color: var(--dim); font-size: 12px; }
header .stat b { color: var(--text); }
nav { display: flex; gap: 4px; padding: 8px 20px 0; }
nav button { background: none; border: 1px solid transparent; border-bottom: none;
             color: var(--dim); padding: 8px 16px; cursor: pointer;
             border-radius: 6px 6px 0 0; font-size: 14px; }
nav button.on { color: var(--text); border-color: var(--border);
                background: var(--panel); }
main { padding: 16px 20px 60px; max-width: 1100px; margin: 0 auto; }
.card { background: var(--panel); border: 1px solid var(--border);
        border-radius: 8px; padding: 16px; margin-bottom: 14px; }
.card h2 { font-size: 15px; margin: 0 0 12px; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
input[type=text], textarea, select {
  background: var(--bg); color: var(--text); border: 1px solid var(--border);
  border-radius: 6px; padding: 8px 10px; font: inherit; }
input[type=text] { flex: 1; min-width: 260px; }
textarea { width: 100%; min-height: 90px; resize: vertical; }
button.act { background: #238636; color: #fff; border: none; border-radius: 6px;
             padding: 8px 16px; cursor: pointer; font-weight: 600; }
button.act:disabled { opacity: .45; cursor: default; }
button.ghost { background: var(--chip); color: var(--text); border: 1px solid var(--border);
               border-radius: 6px; padding: 6px 12px; cursor: pointer; }
.hint { color: var(--dim); font-size: 12px; margin-top: 6px; }
.badge { display: inline-block; border-radius: 10px; padding: 1px 9px;
         font-size: 12px; border: 1px solid var(--border); }
.badge.existing { color: var(--green); border-color: var(--green); }
.badge.new { color: var(--blue); border-color: var(--blue); }
.badge.run { color: var(--accent); border-color: var(--accent); }
.badge.done { color: var(--green); border-color: var(--green); }
.badge.err { color: var(--red); border-color: var(--red); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--border); }
th { color: var(--dim); font-weight: 500; }
td.num { color: var(--dim); }
.log { background: #010409; border: 1px solid var(--border); border-radius: 6px;
       padding: 10px; font: 12px/1.5 Consolas, monospace; color: #c9d1d9;
       max-height: 260px; overflow: auto; white-space: pre-wrap; word-break: break-all; }
.bar { height: 8px; background: var(--chip); border-radius: 4px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--green); width: 0; transition: width .4s; }
.jobline { display: flex; gap: 10px; align-items: center; padding: 8px 0;
           border-bottom: 1px dashed var(--border); cursor: pointer; }
.jobline .t { color: var(--dim); font-size: 12px; width: 130px; }
.hidden { display: none; }
label.chk { display: flex; gap: 6px; align-items: center; color: var(--dim); font-size: 13px; }
.pct { color: var(--dim); font-size: 12px; width: 70px; text-align: right; }
</style>
</head>
<body>
<header>
  <h1>flac-hunter</h1>
  <span class="stat" id="libstat">曲库读取中…</span>
  <span class="stat" style="margin-left:auto" id="jobstat"></span>
</header>
<nav>
  <button data-tab="import" class="on">歌单导入</button>
  <button data-tab="jobs">任务</button>
  <button data-tab="upgrade">无损升级</button>
  <button data-tab="audit">质量审计</button>
</nav>
<main>

<section id="tab-import">
  <div class="card">
    <h2>① 导入歌单（prepare）</h2>
    <div class="row">
      <input type="text" id="uri" placeholder="spotify:playlist:… | qq:歌单id | netease:歌单id | bili:fav:收藏夹id | 平台歌单URL">
      <button class="act" id="btn-uri">拉取并查重</button>
    </div>
    <div class="hint">支持的平台 URL 会自动路由；匿名只能读公开歌单。或改用文本清单：</div>
    <textarea id="listtext" placeholder="每行一条：歌名 - 歌手[ | 时长秒]&#10;例：快晴 - Orangestar | 263.5"></textarea>
    <div class="row" style="margin-top:8px">
      <button class="ghost" id="btn-list">按文本清单查重</button>
      <span class="hint">文本清单不会访问网络，直接对本地曲库查重。</span>
    </div>
  </div>
  <div class="card hidden" id="tracks-card">
    <h2>② 勾选要下载的曲目</h2>
    <div class="row" style="margin-bottom:8px">
      <span id="track-summary"></span>
      <button class="ghost" id="btn-selnew">只选新曲</button>
      <button class="ghost" id="btn-selall">全选</button>
      <button class="ghost" id="btn-selnone">全不选</button>
      <span style="flex:1"></span>
      <select id="source">
        <option value="auto">auto（无损优先）</option>
        <option value="gdstudio">gdstudio</option>
        <option value="netease">netease</option>
        <option value="musicdl">musicdl</option>
        <option value="bili">bili</option>
        <option value="youtube">youtube</option>
      </select>
      <label class="chk"><input type="checkbox" id="inc-ex"> 含已存在曲目重下</label>
      <button class="act" id="btn-dl">③ 开始下载</button>
    </div>
    <div style="max-height:340px;overflow:auto">
    <table id="tracks"><thead><tr>
      <th>#</th><th>歌名</th><th>歌手</th><th>时长</th><th>状态</th>
    </tr></thead><tbody></tbody></table>
    </div>
  </div>
</section>

<section id="tab-jobs" class="hidden">
  <div class="card">
    <h2>任务列表</h2>
    <div id="joblist"></div>
    <div class="hint">同一时间只跑一个作业（下载/升级共用限速与曲库锁），其余排队。</div>
  </div>
  <div class="card hidden" id="joblog-card">
    <h2 id="joblog-title">日志</h2>
    <div class="bar" id="dlbar-wrap" style="margin-bottom:10px"><i id="dlbar"></i></div>
    <div class="pct" id="dlpct" style="text-align:left;margin-bottom:6px"></div>
    <div class="log" id="joblog"></div>
  </div>
</section>

<section id="tab-upgrade" class="hidden">
  <div class="card">
    <h2>MP3 / OGG → FLAC 无损升级</h2>
    <div class="row">
      <select id="up-ext">
        <option value="mp3">mp3</option>
        <option value="ogg">ogg</option>
        <option value="all">all</option>
      </select>
      <label class="chk"><input type="checkbox" id="up-retry"> 清空跳名单全量重试</label>
      <button class="act" id="btn-up">开始升级</button>
    </div>
    <div class="hint">只升级「源确实是 FLAC」的文件（实测 codec），MP3 源不会被硬转。</div>
  </div>
</section>

<section id="tab-audit" class="hidden">
  <div class="card">
    <h2>四项质量门（时长 / 标签 / 封面 / 真 FLAC）</h2>
    <button class="act" id="btn-audit">全库审计</button>
    <div class="hint">扫描曲库全部 .flac，报告时长偏差、缺标签、缺封面、伪 FLAC。</div>
  </div>
</section>

</main>
<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s ?? "").toString().replace(/[&<>"']/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let tracksPath = null;
let activeJobId = null;
let logOffset = 0;
const onDoneMap = {};   // jobId -> 作业完成后的回调（prepare 完成后加载曲目表等）

document.querySelectorAll("nav button").forEach(b => b.onclick = () => {
  document.querySelectorAll("nav button").forEach(x => x.classList.remove("on"));
  b.classList.add("on");
  document.querySelectorAll("main section").forEach(s => s.classList.add("hidden"));
  document.querySelector("#tab-" + b.dataset.tab).classList.remove("hidden");
});

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function fmtDur(ms) {
  if (!ms) return "—";
  const s = Math.round(ms / 1000);
  return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
}

// ---------- 歌单导入 ----------
$("#btn-uri").onclick = async () => {
  const uri = $("#uri").value.trim();
  if (!uri) return alert("填入歌单 URI 或 URL");
  const j = await api("/api/prepare", {method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({uri: uri})});
  watchJob(j.id, () => loadTracks(j.tracks_path));
};

$("#btn-list").onclick = async () => {
  const text = $("#listtext").value.trim();
  if (!text) return alert("文本清单为空");
  const j = await api("/api/prepare", {method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({list_text: text})});
  watchJob(j.id, () => loadTracks(j.tracks_path));
};

async function loadTracks(path) {
  tracksPath = path;
  const d = await api("/api/tracks?path=" + encodeURIComponent(path));
  const tb = document.querySelector("#tracks tbody");
  tb.innerHTML = "";
  let exists = 0;
  d.records.forEach(r => {
    if (r.existing) exists += 1;
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td class="num"><input type="checkbox" class="sel" data-uri="${esc(r.uri || "")}" ${r.existing ? "" : "checked"}></td>` +
      `<td class="num">${r.position}</td><td>${esc(r.name)}</td>` +
      `<td>${esc((r.artists || []).join(" / "))}</td>` +
      `<td class="num">${fmtDur(r.duration_ms)}</td>` +
      `<td><span class="badge ${r.existing ? "existing" : "new"}">${r.existing ? "已有" : "新曲"}</span></td>`;
    tb.appendChild(tr);
  });
  $("#track-summary").textContent = `共 ${d.records.length} 首：新曲 ${d.records.length - exists}，已有 ${exists}`;
  $("#tracks-card").classList.remove("hidden");
}

$("#btn-selnew").onclick = () => setSel(false);
$("#btn-selall").onclick = () => setSel(true);
$("#btn-selnone").onclick = () => setSel("none");
function setSel(mode) {
  document.querySelectorAll("#tracks .sel").forEach(cb => {
    cb.checked = mode === "none" ? false : (mode === true ? true : !cb.checked);
  });
}

$("#btn-dl").onclick = async () => {
  if (!tracksPath) return;
  const only = [...document.querySelectorAll("#tracks .sel")].filter(c => c.checked)
    .map(c => c.dataset.uri).filter(Boolean);
  const body = {tracks: tracksPath, source: $("#source").value,
                include_existing: $("#inc-ex").checked};
  if (only.length > 0) body.only = only;
  const j = await api("/api/download", {method: "POST",
    headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  watchJob(j.id);
  showTab("jobs");
};

// ---------- 任务 ----------
let jobsCache = [];
function showTab(name) {
  document.querySelector(`nav button[data-tab="${name}"]`).click();
}

$("#joblist").onclick = (e) => {
  const line = e.target.closest(".jobline");
  if (line) openJobLog(line.dataset.id);
};

async function refreshState() {
  try {
    const d = await api("/api/state");
    const L = d.library;
    $("#libstat").innerHTML =
      `曲库：<b>${L.total}</b> 首（flac <b>${L.flac}</b> · mp3 <b>${L.mp3}</b> · ogg <b>${L.ogg}</b> · 其他 <b>${L.other}</b>）`;
    const running = d.jobs.filter(j => j.status === "running" || j.status === "queued");
    $("#jobstat").textContent = running.length > 0 ?
      `进行中 ${running.length}：${running[0].type}` : "空闲";
    renderJobs(d.jobs);
    if (activeJobId) pollJob();
  } catch (e) { /* 服务未就绪时静默 */ }
}

function renderJobs(jobs) {
  const box = $("#joblist");
  box.innerHTML = "";
  jobs.slice().reverse().forEach(j => {
    const div = document.createElement("div");
    div.className = "jobline";
    div.dataset.id = j.id;
    const badge = j.status === "running" ? "run" : j.status === "done" ? "done" :
                  j.status === "error" ? "err" : "";
    div.innerHTML = `<span class="badge ${badge}">${j.status}</span>` +
      `<span class="t">${esc(j.type)} · ${esc(j.started_h)}</span>` +
      `<span>${esc(j.summary || "")}</span>`;
    box.appendChild(div);
  });
}

function openJobLog(id) {
  activeJobId = id;
  logOffset = 0;
  $("#joblog").textContent = "";
  showTab("jobs");
  $("#joblog-card").classList.remove("hidden");
  pollJob();
}

async function pollJob() {
  if (!activeJobId) return;
  try {
    const j = await api("/api/job/" + activeJobId);
    $("#joblog-title").textContent = `日志 · ${j.type}`;
    if (j.progress && j.progress.total > 0) {
      const pct = Math.min(100, Math.round(j.progress.done * 100 / j.progress.total));
      $("#dlbar").style.width = pct + "%";
      $("#dlpct").textContent = `${j.progress.done} / ${j.progress.total}（${pct}%）`;
    } else {
      $("#dlbar").style.width = "0";
      $("#dlpct").textContent = "";
    }
    const tail = j.log_tail;
    if (tail.length > logOffset) {
      $("#joblog").textContent += tail.slice(logOffset).join("\\n") + "\\n";
      logOffset = tail.length;
      $("#joblog").scrollTop = $("#joblog").scrollHeight;
    }
    if (j.status !== "running" && j.status !== "queued") {
      const cb = onDoneMap[id];
      if (cb) { delete onDoneMap[id]; cb(); }
    } else {
      setTimeout(pollJob, 1500);
    }
  } catch (e) { setTimeout(pollJob, 2500); }
}

function watchJob(id, onDone) {
  if (onDone) onDoneMap[id] = onDone;
  openJobLog(id);
}

// ---------- 升级 / 审计 ----------
$("#btn-up").onclick = async () => {
  const j = await api("/api/upgrade", {method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ext: $("#up-ext").value, full_retry: $("#up-retry").checked})});
  watchJob(j.id);
  showTab("jobs");
};

$("#btn-audit").onclick = async () => {
  const j = await api("/api/audit", {method: "POST",
    headers: {"Content-Type": "application/json"}, body: "{}"});
  watchJob(j.id);
  showTab("jobs");
};

refreshState();
setInterval(refreshState, 2500);
</script>
</body>
</html>
"""
