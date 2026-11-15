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
  --bg: #0d1117; --panel: #161b22; --panel2: #1c2129; --border: #30363d;
  --text: #e6edf3; --dim: #8b949e; --accent: #d29922; --green: #3fb950;
  --red: #f85149; --blue: #58a6ff; --chip: #21262d; --purple: #bc8cff;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
       font: 14px/1.55 "Segoe UI", "Microsoft YaHei", sans-serif; }
header { display: flex; align-items: center; gap: 14px; padding: 14px 22px;
         border-bottom: 1px solid var(--border); position: sticky; top: 0;
         background: rgba(13,17,23,.92); backdrop-filter: blur(6px); z-index: 5; }
header h1 { font-size: 19px; margin: 0; color: var(--accent); letter-spacing: .5px; }
.libchips { display: flex; gap: 8px; }
.lchip { background: var(--chip); border: 1px solid var(--border); border-radius: 20px;
         padding: 3px 12px; font-size: 12.5px; color: var(--dim); }
.lchip b { color: var(--text); }
.lchip .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
              margin-right: 6px; vertical-align: 1px; }
.dot.flac { background: var(--purple); } .dot.mp3 { background: var(--blue); }
.dot.ogg { background: var(--green); }
#jobstat { margin-left: auto; font-size: 13px; color: var(--dim); }
#jobstat .live { color: var(--accent); font-weight: 600; }
nav { display: flex; gap: 6px; padding: 10px 22px 0; }
nav button { background: none; border: 1px solid transparent; border-bottom: none;
             color: var(--dim); padding: 9px 18px; cursor: pointer;
             border-radius: 8px 8px 0 0; font-size: 14px; transition: color .15s; }
nav button:hover { color: var(--text); }
nav button.on { color: var(--text); border-color: var(--border);
                background: var(--panel); }
main { padding: 18px 22px 70px; max-width: 1080px; margin: 0 auto; }
.card { background: var(--panel); border: 1px solid var(--border);
        border-radius: 12px; padding: 18px; margin-bottom: 16px; }
.card h2 { font-size: 15px; margin: 0 0 14px; display: flex; align-items: center; gap: 8px; }
.card h2 .sub { color: var(--dim); font-weight: 400; font-size: 12.5px; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
input[type=text], textarea, select {
  background: var(--bg); color: var(--text); border: 1px solid var(--border);
  border-radius: 8px; padding: 9px 12px; font: inherit; outline: none; }
input[type=text]:focus, textarea:focus, select:focus { border-color: var(--accent); }
input[type=text] { flex: 1; min-width: 260px; }
textarea { width: 100%; min-height: 84px; resize: vertical; }
button.act { background: #238636; color: #fff; border: none; border-radius: 8px;
             padding: 9px 18px; cursor: pointer; font-weight: 600; font-size: 14px;
             transition: filter .15s; }
button.act:hover { filter: brightness(1.15); }
button.act:disabled { opacity: .45; cursor: default; }
button.ghost { background: var(--chip); color: var(--text); border: 1px solid var(--border);
               border-radius: 8px; padding: 7px 14px; cursor: pointer; font-size: 13px; }
button.ghost:hover { border-color: var(--dim); }
button.ghost.on { border-color: var(--accent); color: var(--accent); }
.hint { color: var(--dim); font-size: 12.5px; margin-top: 8px; }
.badge { display: inline-block; border-radius: 10px; padding: 1px 10px;
         font-size: 12px; border: 1px solid var(--border); color: var(--dim); }
.badge.existing { color: var(--green); border-color: var(--green); background: rgba(63,185,80,.08); }
.badge.new { color: var(--blue); border-color: var(--blue); background: rgba(88,166,255,.08); }
.badge.run { color: var(--accent); border-color: var(--accent); background: rgba(210,153,34,.08); }
.badge.done { color: var(--green); border-color: var(--green); background: rgba(63,185,80,.08); }
.badge.err { color: var(--red); border-color: var(--red); background: rgba(248,81,73,.08); }
.badge.q { color: var(--dim); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--border); }
th { color: var(--dim); font-weight: 500; position: sticky; top: 0; background: var(--panel); }
td.num { color: var(--dim); }
.log { background: #010409; border: 1px solid var(--border); border-radius: 8px;
       padding: 12px; font: 12px/1.6 Consolas, "Cascadia Mono", monospace; color: #c9d1d9;
       max-height: 300px; overflow: auto; white-space: pre-wrap; word-break: break-all; }
.bar { height: 9px; background: var(--chip); border-radius: 5px; overflow: hidden; }
.bar i { display: block; height: 100%; background: linear-gradient(90deg, var(--green), var(--blue));
         width: 0; transition: width .4s; }
.jobcard { background: var(--panel2); border: 1px solid var(--border); border-radius: 10px;
           padding: 12px 16px; margin-bottom: 10px; cursor: pointer; transition: border-color .15s; }
.jobcard:hover { border-color: var(--dim); }
.jobcard .top { display: flex; gap: 10px; align-items: center; }
.jobcard .ico { font-size: 18px; }
.jobcard .name { font-weight: 600; }
.jobcard .t { color: var(--dim); font-size: 12px; }
.jobcard .sum { color: var(--dim); font-size: 12.5px; margin-top: 4px; }
.jobcard .bar { margin-top: 8px; }
.empty { color: var(--dim); text-align: center; padding: 26px 0; font-size: 13px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
         gap: 10px; margin-bottom: 14px; }
.tile { background: var(--panel2); border: 1px solid var(--border); border-radius: 10px;
        padding: 14px 16px; }
.tile .v { font-size: 26px; font-weight: 700; }
.tile .k { color: var(--dim); font-size: 12.5px; margin-top: 2px; }
.tile.ok .v { color: var(--green); } .tile.bad .v { color: var(--red); }
.tile.rate .v { color: var(--accent); }
.ichips { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.ichip { background: var(--chip); border: 1px solid var(--border); border-radius: 16px;
         padding: 4px 14px; cursor: pointer; font-size: 13px; color: var(--dim);
         transition: all .15s; }
.ichip:hover { color: var(--text); }
.ichip.on { border-color: var(--accent); color: var(--accent); }
.ichip b { color: var(--text); }
.ichip.on b { color: var(--accent); }
.hidden { display: none; }
label.chk { display: flex; gap: 6px; align-items: center; color: var(--dim); font-size: 13px; }
.step { display: inline-flex; width: 22px; height: 22px; border-radius: 50%;
        background: var(--chip); border: 1px solid var(--border); color: var(--accent);
        align-items: center; justify-content: center; font-size: 12px; margin-right: 8px; }
details.rawlog summary { cursor: pointer; color: var(--dim); font-size: 12.5px; }
</style>
</head>
<body>
<header>
  <h1>🎵 flac-hunter</h1>
  <div class="libchips" id="libchips"></div>
  <span id="jobstat"></span>
</header>
<nav>
  <button data-tab="import" class="on">🎶 歌单导入</button>
  <button data-tab="jobs">📡 任务</button>
  <button data-tab="upgrade">💎 无损升级</button>
  <button data-tab="audit">🩺 质量审计</button>
</nav>
<main>

<section id="tab-import">
  <div class="card">
    <h2><span class="step">1</span>导入歌单 <span class="sub">拉元数据 → 对本地曲库查重 → 告诉你哪些已有、哪些要下</span></h2>
    <div class="row">
      <input type="text" id="uri" placeholder="粘贴歌单链接或 URI：B站收藏夹 / QQ / 网易云 / Spotify / 平台 URL">
      <button class="act" id="btn-uri">拉取并查重</button>
    </div>
    <div class="hint">支持：bilibili.com 收藏夹、y.qq.com 歌单、网易云 playlist、spotify: URI；
      匿名只能读<b>公开</b>歌单。没有链接？用下面的文本清单：</div>
    <textarea id="listtext" placeholder="每行一条：歌名 - 歌手[ | 时长秒]&#10;例：快晴 - Orangestar | 263.5"></textarea>
    <div class="row" style="margin-top:10px">
      <button class="ghost" id="btn-list">按文本清单查重</button>
      <span class="hint">文本清单不访问网络，直接对本地曲库查重。</span>
    </div>
  </div>
  <div class="card hidden" id="tracks-card">
    <h2><span class="step">2</span>勾选要下载的曲目 <span class="sub" id="track-summary"></span></h2>
    <div class="row" style="margin-bottom:10px">
      <button class="ghost" id="btn-selnew">只选新曲</button>
      <button class="ghost" id="btn-selall">全选</button>
      <button class="ghost" id="btn-selnone">全不选</button>
      <span style="flex:1"></span>
      <label class="chk">下载源
        <select id="source">
          <option value="auto">auto（无损优先）</option>
          <option value="gdstudio">gdstudio</option>
          <option value="netease">netease</option>
          <option value="musicdl">musicdl</option>
          <option value="bili">bili</option>
          <option value="youtube">youtube</option>
        </select>
      </label>
      <label class="chk"><input type="checkbox" id="inc-ex"> 含已有曲目重下</label>
      <button class="act" id="btn-dl"><span class="step" style="background:rgba(255,255,255,.15);border:none;color:#fff">3</span>开始下载</button>
    </div>
    <div style="max-height:360px;overflow:auto;border:1px solid var(--border);border-radius:8px">
    <table id="tracks"><thead><tr>
      <th style="width:34px"></th><th style="width:44px">#</th><th>歌名</th><th>歌手</th><th style="width:70px">时长</th><th style="width:80px">状态</th>
    </tr></thead><tbody></tbody></table>
    </div>
  </div>
</section>

<section id="tab-jobs" class="hidden">
  <div class="card">
    <h2>任务列表 <span class="sub">同一时间只跑一个作业（共享限速与曲库锁），其余排队</span></h2>
    <div id="joblist"><div class="empty">还没有任务 —— 去「🎶 歌单导入」开始吧</div></div>
  </div>
  <div class="card hidden" id="joblog-card">
    <h2 id="joblog-title">日志</h2>
    <div class="bar" id="dlbar-wrap" style="margin-bottom:8px"><i id="dlbar"></i></div>
    <div class="row hidden" id="jobctl-wrap" style="margin-bottom:10px">
      <div class="hint" id="dlpct" style="margin:0"></div>
      <span style="flex:1"></span>
      <span class="hint" id="cur-track" style="margin:0"></span>
      <button class="ghost hidden" id="btn-pause">⏸ 暂停</button>
      <button class="ghost hidden" id="btn-skip">⏭ 跳过这首</button>
    </div>
    <div class="log" id="joblog"></div>
  </div>
</section>

<section id="tab-upgrade" class="hidden">
  <div class="card">
    <h2>💎 MP3 / OGG → FLAC 无损升级 <span class="sub">只升「源确实是 FLAC」的文件（实测 codec），绝不硬转</span></h2>
    <div class="row">
      <label class="chk">目标格式
        <select id="up-ext">
          <option value="mp3">mp3</option>
          <option value="ogg">ogg</option>
          <option value="all">all</option>
        </select>
      </label>
      <label class="chk"><input type="checkbox" id="up-retry"> 清空跳名单全量重试</label>
      <button class="act" id="btn-up">开始升级</button>
    </div>
    <div class="hint">找不到无损源的文件会记进跳名单，失败 ≥2 次自动跳过；全量重试会清空名单再跑一轮。</div>
  </div>
</section>

<section id="tab-audit" class="hidden">
  <div class="card hidden" id="audit-result">
    <h2>🩺 上次审计结果 <span class="sub" id="audit-when"></span></h2>
    <div class="tiles" id="audit-tiles"></div>
    <div class="ichips" id="audit-chips"></div>
    <div class="row" style="margin-bottom:8px">
      <input type="text" id="audit-search" placeholder="按文件名搜索…" style="max-width:300px">
      <span class="hint" style="margin:0" id="audit-count"></span>
    </div>
    <div style="max-height:340px;overflow:auto;border:1px solid var(--border);border-radius:8px">
      <table id="audit-files"><thead><tr><th>文件</th><th style="width:200px">问题</th></tr></thead><tbody></tbody></table>
    </div>
    <div class="hint">点击上方分类 chip 可筛选问题类型；合格文件不在列表中。</div>
  </div>
  <div class="card">
    <h2>发起审计 <span class="sub">四项质量门：时长偏差 / 缺标签 / 缺封面 / 伪 FLAC</span></h2>
    <button class="act" id="btn-audit">扫描全库 .flac</button>
    <div class="hint">逐文件实测（ffprobe），结果以统计卡片呈现，不再只给前 50 条。</div>
  </div>
</section>

</main>
<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s ?? "").toString().replace(/[&<>"']/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const TYPE_NAME = {prepare: "歌单查重", download: "下载", upgrade: "无损升级",
                   audit: "质量审计", custom: "自定义"};
let tracksPath = null;
let activeJobId = null;
let logOffset = 0;
const onDoneMap = {};
let auditData = null;      // {total, pass, fail, by_issue, files, when}
let auditFilter = "全部";

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

function showTab(name) {
  document.querySelector(`nav button[data-tab="${name}"]`).click();
}

// ---------- 审计结果渲染 ----------
function renderAudit() {
  if (!auditData) return;
  const A = auditData;
  const rate = A.total > 0 ? Math.round(A.pass * 100 / A.total) : 0;
  $("#audit-tiles").innerHTML =
    `<div class="tile"><div class="v">${A.total}</div><div class="k">扫描 FLAC</div></div>` +
    `<div class="tile ok"><div class="v">${A.pass}</div><div class="k">通过</div></div>` +
    `<div class="tile bad"><div class="v">${A.fail}</div><div class="k">不合格</div></div>` +
    `<div class="tile rate"><div class="v">${rate}%</div><div class="k">合格率</div></div>`;
  const chips = ["全部", ...Object.entries(A.by_issue).sort((a, b) => b[1] - a[1])
                  .map(([k, v]) => k)];
  $("#audit-chips").innerHTML = chips.map(k => {
    const n = k === "全部" ? A.fail : (A.by_issue[k] || 0);
    return `<span class="ichip ${k === auditFilter ? "on" : ""}" data-k="${esc(k)}">${esc(k)} <b>${n}</b></span>`;
  }).join("");
  document.querySelectorAll("#audit-chips .ichip").forEach(c => c.onclick = () => {
    auditFilter = c.dataset.k;
    renderAudit();
  });
  const kw = ($("#audit-search").value || "").toLowerCase();
  const rows = A.files.filter(f =>
    (auditFilter === "全部" || f.issues.includes(auditFilter)) &&
    (!kw || f.name.toLowerCase().includes(kw)));
  $("#audit-count").textContent = `显示 ${rows.length} / ${A.fail} 个不合格文件`;
  $("#audit-files tbody").innerHTML = rows.slice(0, 500).map(f =>
    `<tr><td>${esc(f.name)}</td><td>${f.issues.map(i =>
      `<span class="badge q">${esc(i)}</span>`).join(" ")}</td></tr>`).join("") ||
    `<tr><td colspan="2" class="empty">（无匹配项）</td></tr>`;
}
$("#audit-search").oninput = renderAudit;

function showAudit(A) {
  auditData = A;
  auditFilter = "全部";
  $("#audit-when").textContent = A.when || "";
  renderAudit();
  $("#audit-result").classList.remove("hidden");
}

// ---------- 歌单导入 ----------
$("#btn-uri").onclick = async () => {
  const uri = $("#uri").value.trim();
  if (!uri) return alert("填入歌单链接或 URI");
  const j = await api("/api/prepare", {method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({uri: uri})});
  watchJob(j.id, () => loadTracks(j.tracks_path));
  showTab("jobs");
};

$("#btn-list").onclick = async () => {
  const text = $("#listtext").value.trim();
  if (!text) return alert("文本清单为空");
  const j = await api("/api/prepare", {method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({list_text: text})});
  watchJob(j.id, () => loadTracks(j.tracks_path));
  showTab("jobs");
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
      `<td><input type="checkbox" class="sel" data-uri="${esc(r.uri || "")}" ${r.existing ? "" : "checked"}></td>` +
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
  if (only.length > 0 && only.length < document.querySelectorAll("#tracks .sel").length)
    body.only = only;
  const j = await api("/api/download", {method: "POST",
    headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  watchJob(j.id);
  showTab("jobs");
};

// ---------- 任务 ----------
let jobsCache = [];
$("#joblist").onclick = (e) => {
  const card = e.target.closest(".jobcard");
  if (card) openJobLog(card.dataset.id);
};

async function refreshState() {
  try {
    const d = await api("/api/state");
    const L = d.library;
    $("#libchips").innerHTML =
      `<span class="lchip"><span class="dot flac"></span>FLAC <b>${L.flac}</b></span>` +
      `<span class="lchip"><span class="dot mp3"></span>MP3 <b>${L.mp3}</b></span>` +
      `<span class="lchip"><span class="dot ogg"></span>OGG <b>${L.ogg}</b></span>` +
      `<span class="lchip">共 <b>${L.total}</b> 首</span>`;
    const running = d.jobs.filter(j => j.status === "running" || j.status === "queued");
    $("#jobstat").innerHTML = running.length > 0 ?
      `进行中 <span class="live">${running.length}</span>：${TYPE_NAME[running[0].type] || running[0].type}` : "空闲";
    renderJobs(d.jobs);
    if (activeJobId) pollJob();
    // 自动发现最近一次完成的审计 → 填充审计页（内存作业或持久化的 last_audit.json）
    if (!auditData) {
      const last = d.jobs.find(j => j.type === "audit" && j.status === "done");
      if (last) {
        const j = await api("/api/job/" + last.id);
        if (j.audit) showAudit({...j.audit, when: j.started_h});
      } else {
        try {
          const lastSaved = await api("/api/audit/last");
          showAudit({...lastSaved.audit, when: lastSaved.when});
        } catch (e) { /* 从未审计过 */ }
      }
    }
  } catch (e) { /* 服务未就绪时静默 */ }
}

function renderJobs(jobs) {
  const box = $("#joblist");
  if (jobs.length === 0) {
    box.innerHTML = `<div class="empty">还没有任务 —— 去「🎶 歌单导入」开始吧</div>`;
    return;
  }
  box.innerHTML = "";
  jobs.forEach(j => {
    const icon = {prepare: "🔎", download: "⬇️", upgrade: "💎", audit: "🩺"}[j.type] || "⚙️";
    const badge = j.status === "running" ? "run" : j.status === "done" ? "done" :
                  j.status === "error" ? "err" : "q";
    const st = j.status === "running" ? "进行中" : j.status === "queued" ? "排队中" :
               j.status === "done" ? "已完成" : "失败";
    const pct = j.total > 0 ? Math.min(100, Math.round(j.progress.done * 100 / j.total)) : 0;
    const div = document.createElement("div");
    div.className = "jobcard";
    div.dataset.id = j.id;
    div.innerHTML =
      `<div class="top"><span class="ico">${icon}</span>` +
      `<span class="name">${TYPE_NAME[j.type] || j.type}</span>` +
      `<span class="badge ${badge}">${st}</span>` +
      `<span class="t">${esc(j.started_h)}</span>` +
      `<span class="sum">${esc(j.summary || "")}</span></div>` +
      (j.total > 0 ? `<div class="bar"><i style="width:${pct}%"></i></div>` : "");
    box.appendChild(div);
  });
}

function openJobLog(id) {
  activeJobId = id;
  logOffset = 0;
  $("#joblog").textContent = "";
  $("#joblog-card").classList.remove("hidden");
  pollJob();
}

async function pollJob() {
  if (!activeJobId) return;
  try {
    const j = await api("/api/job/" + activeJobId);
    $("#joblog-title").textContent = `日志 · ${TYPE_NAME[j.type] || j.type}`;
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
    // 下载作业的暂停/跳过控制
    const ctl = $("#jobctl-wrap");
    if (j.type === "download" && j.status === "running" && j.current !== undefined) {
      ctl.classList.remove("hidden");
      $("#btn-pause").textContent = j.paused ? "▶️ 继续" : "⏸ 暂停";
      $("#btn-pause").dataset.paused = j.paused ? "1" : "";
      $("#cur-track").textContent = j.current && j.current.name ?
        (j.paused ? "已暂停（当前曲目完成后停下）" : "正在处理：" + j.current.name) : "";
    } else {
      ctl.classList.add("hidden");
    }
    if (j.status !== "running" && j.status !== "queued") {
      const cb = onDoneMap[activeJobId];
      if (cb) { delete onDoneMap[activeJobId]; cb(); }
    } else {
      setTimeout(pollJob, 1500);
    }
  } catch (e) { setTimeout(pollJob, 2500); }
}

function watchJob(id, onDone) {
  if (onDone) onDoneMap[id] = onDone;
  openJobLog(id);
}

// ---------- 下载控制（暂停/跳过） ----------
$("#btn-pause").onclick = async () => {
  if (!activeJobId) return;
  const paused = $("#btn-pause").dataset.paused === "1";
  await api(`/api/job/${activeJobId}/pause`, {method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({paused: !paused})});
};
$("#btn-skip").onclick = async () => {
  if (!activeJobId) return;
  await api(`/api/job/${activeJobId}/skip`, {method: "POST",
    headers: {"Content-Type": "application/json"}, body: "{}"});
};

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
  watchJob(j.id, async () => {
    const full = await api("/api/job/" + j.id);
    if (full.audit) showAudit({...full.audit, when: full.started_h});
    showTab("audit");
  });
  showTab("jobs");
};

refreshState();
setInterval(refreshState, 2500);
</script>
</body>
</html>
"""
