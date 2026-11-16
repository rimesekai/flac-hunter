"""flac-hunter 本地 Web GUI（标准库 http.server，零 pip 依赖，仅绑 127.0.0.1 自用）。

用法：python gui.py [--port 8756]  → 自动开浏览器。
核心四件套：歌单导入（含查重预览）→ 勾选下载（实时进度）→ 无损升级 → 质量审计。
下载/升级以子进程跑仓库自带的 cli.py（零侵入核心）；审计在服务内直跑
audit_one（拿到全量结构化结果，不受 CLI 只打印前 50 条失败的限制）。
同一时间只跑一个作业；下载/升级进度来自 tasks/results.jsonl 增量行。
其余子命令在更新目标清单里（README §七）。
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flac_hunter.config import load_config  # noqa: E402
from flac_hunter.gui_page import PAGE_HTML  # noqa: E402

REPO = Path(__file__).resolve().parent
LOG_CAP = 1200           # 每作业日志行数上限（环形丢弃最旧的）
LOG_TAIL = 400           # /api/job 返回的日志尾行数
AUDIT_FILES_CAP = 2000   # 审计不合格文件明细上限
GATE_ZH = {"dur_ok": "时长偏差", "tags_ok": "缺标签", "jpg_ok": "缺封面", "flac_ok": "伪FLAC"}
PY = sys.executable or "python"


def _now_h() -> str:
    return time.strftime("%m-%d %H:%M:%S")


class Job:
    """一个作业：下载/升级是 cli.py 子进程，审计在服务内直跑。"""

    def __init__(self, jid: str, jtype: str, cmd: list | None, cwd: Path,
                 total: int = 0, tracks_path: str | None = None,
                 tracks_list: list | None = None, source: str = "auto",
                 include_existing: bool = False, music_dir: str = "",
                 audit_files: list[str] | None = None,
                 download_cover: bool = True, download_lyrics: bool = True,
                 list_text: str | None = None):
        self.id = jid
        self.type = jtype
        self.cmd = cmd
        self.cwd = cwd
        self.total = total
        self.tracks_path = tracks_path
        self.tracks_list = tracks_list          # 下载逐曲模式的目标曲目列表
        self.source = source
        self.include_existing = include_existing
        self.music_dir = music_dir              # 本次下载/审计自定义目录（空则沿用 config.toml）
        self.audit_files = audit_files          # 质量审计选定文件列表（None 表示全库）
        self.download_cover = download_cover
        self.download_lyrics = download_lyrics
        self.list_text = list_text              # 含无歌手歌名时的文本清单展开原文
        self.status = "queued"
        self.exit_code: int | None = None
        self.started = time.time()
        self.started_h = _now_h()
        self.ended: float | None = None
        self.summary = ""
        self.log: deque[str] = deque(maxlen=LOG_CAP)
        self.done = 0
        self.status_counts: dict = {}
        self.audit: dict | None = None          # 审计作业的全量结构化结果
        self.paused = False                     # 逐曲下载：干完当前首后停下
        self.skip_requested = False             # 逐曲下载：终止当前首、开下一首
        self.cancel_requested = False           # 取消请求：逐曲/子进程/审计三类作业协作检查（POST /api/job/<id>/cancel）
        self.cancelled = False                  # 已受理取消（snapshot 顶层 "cancelled"，字段名冻结）
        self.cancelled_remaining = 0            # 取消时剩余未处理曲目数（snapshot 顶层 "cancelled_remaining"）
        self.current = None                     # 正在处理的曲目
        self.current_proc = None                # 当前子进程引用：取消端点直接终止，避免 readline 阻塞期无法响应
        self._started_tracks = 0                # 已发出子进程的曲目数（计算取消剩余 cancelled_remaining）
        self._res_offset = 0
        res = cwd / "tasks" / "results.jsonl"
        if res.exists():
            self._res_offset = res.stat().st_size
        self._stop_tail = threading.Event()

    def snapshot(self, with_log: bool = False) -> dict:
        d = {
            "id": self.id, "type": self.type, "status": self.status,
            "exit_code": self.exit_code, "started_h": self.started_h,
            "summary": self.summary, "total": self.total,
            "progress": {"done": self.done, "total": self.total},
            "tracks_path": self.tracks_path,
            "music_dir": self.music_dir,
            "status_counts": dict(self.status_counts),
            "audit": self.audit,
            "paused": self.paused, "current": self.current,
            "cancelled": self.cancelled,
            "cancelled_remaining": self.cancelled_remaining,
        }
        if with_log:
            d["log_tail"] = list(self.log)[max(0, len(self.log) - LOG_TAIL):]
        return d


def _tail_results(job: Job) -> None:
    """后台线程：增量读 tasks/results.jsonl，统计本作业的逐曲进度。"""
    res = job.cwd / "tasks" / "results.jsonl"
    while not job._stop_tail.wait(0.8):
        try:
            if not res.exists() or res.stat().st_size <= job._res_offset:
                continue
            with res.open("r", encoding="utf-8", errors="replace") as f:
                f.seek(job._res_offset)
                new = f.read()
            job._res_offset = res.stat().st_size
            for line in new.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                job.done += 1
                st = str(rec.get("status") or "?")
                job.status_counts[st] = job.status_counts.get(st, 0) + 1
        except Exception:
            continue


class Runner:
    """单 worker 的作业队列：同一时间只跑一个作业，其余排队。"""

    def __init__(self, cfg):
        self.cfg = cfg
        self.jobs: dict[str, Job] = {}
        self.order: list[str] = []
        self.queue: deque[str] = deque()
        self.lock = threading.Lock()
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()

    def submit(self, jtype: str, cmd: list | None, total: int = 0,
               tracks_path: str | None = None, tracks_list: list | None = None,
               source: str = "auto", include_existing: bool = False,
               music_dir: str = "", audit_files: list[str] | None = None,
               download_cover: bool = True, download_lyrics: bool = True,
               list_text: str | None = None) -> dict:
        jid = uuid.uuid4().hex[:10]
        job = Job(jid, jtype, cmd, REPO, total=total, tracks_path=tracks_path,
                  tracks_list=tracks_list, source=source,
                  include_existing=include_existing, music_dir=music_dir,
                  audit_files=audit_files,
                  download_cover=download_cover, download_lyrics=download_lyrics,
                  list_text=list_text)
        with self.lock:
            self.jobs[jid] = job
            self.order.append(jid)
            self.queue.append(jid)
        return job.snapshot()

    def _loop(self) -> None:
        while True:
            jid = None
            with self.lock:
                if self.queue:
                    jid = self.queue.popleft()
            if jid is None:
                time.sleep(0.4)
                continue
            job = self.jobs[jid]
            if job.cancelled:
                # 已取消的排队作业：取出时直接跳过执行（契约①：queued 取消 → 不再开工）
                job.status = "cancelled"
                job.summary = "已取消（未执行）"
                job.ended = time.time()
                job._stop_tail.set()
                continue
            job.status = "running"
            try:
                if job.type == "audit":
                    self._run_audit(job)
                    if job.exit_code is None:
                        job.exit_code = 0
                elif job.type == "download" and job.tracks_list is not None:
                    self._run_download_pertrack(job)
                    if job.exit_code is None:
                        job.exit_code = 0
                elif job.type == "prepare" and job.cmd is None and job.list_text is not None:
                    self._run_prepare_list_search(job)
                    if job.exit_code is None:
                        job.exit_code = 0
                else:
                    self._run_subproc(job)
                if job.cancelled:
                    job.status = "cancelled"
                else:
                    job.status = "done" if job.exit_code == 0 else "error"
                if job.audit:
                    job.summary = (f"{job.audit['total']} 个 FLAC："
                                   f"通过 {job.audit['pass']} · 不合格 {job.audit['fail']}")
                    if job.cancelled:
                        job.summary += "（已取消，保留已完成部分）"
                elif job.status_counts:
                    job.summary = ("已取消 · " if job.cancelled else "完成 · ") + " ".join(
                        f"{k}:{v}" for k, v in sorted(job.status_counts.items()))
                elif job.cancelled:
                    job.summary = "已取消"
                else:
                    job.summary = "完成" if job.exit_code == 0 else f"失败 exit={job.exit_code}"
                if job.exit_code != 0 and not job.cancelled:
                    job.summary += "（看日志末尾找原因）"
            except Exception as e:  # noqa: BLE001
                job.status = "error"
                job.summary = f"异常: {str(e)[:160]}"
                job.log.append(f"[runner] 异常: {e}")
            finally:
                job.ended = time.time()
                job._stop_tail.set()

    def _run_subproc(self, job: Job) -> None:
        job.log.append(f"[runner] {' '.join(job.cmd)}")
        t = threading.Thread(target=_tail_results, args=(job,), daemon=True)
        t.start()
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            job.cmd, cwd=str(job.cwd), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        job.current_proc = proc
        assert proc.stdout is not None
        for raw in iter(proc.stdout.readline, b""):
            if job.cancel_requested:
                # 契约②：子进程作业取消 → 终止进程并 wait（取消端点同时已 kill，此处兜底）
                _kill_proc_tree(proc)
                break
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line:
                job.log.append(line)
                m = re.match(r"^\[upgrade\]\s*\((\d+)/(\d+)\)\s*(.*)$", line)
                if m:
                    cur, tot, detail = int(m.group(1)), int(m.group(2)), m.group(3)
                    job.total = max(job.total, tot)
                    if "->" in detail:
                        job.done = max(job.done, cur)
                    job.summary = f"无损升级 {cur}/{tot} · {detail[:48]}"
                ms = re.match(r"^\[upgrade\]\s*汇总:\s*共\s*(\d+)\s*个\s*·\s*已升级\s*(\d+)\s*·\s*跳过/保留\s*(\d+)\s*·\s*失败\s*(\d+)", line)
                if ms:
                    tot, up_n, kept_n, fail_n = (int(ms.group(i)) for i in range(1, 5))
                    job.total = max(job.total, tot)
                    job.done = tot
                    counts = {"upgraded": up_n}
                    if kept_n:
                        counts["kept"] = kept_n
                    if fail_n:
                        counts["failed"] = fail_n
                    job.status_counts = counts
        proc.wait()
        job.current_proc = None
        job.exit_code = proc.returncode
        job._stop_tail.set()

    def _download_cmd(self, job: Job, only_key: str) -> list:
        cmd = [PY, "-X", "utf8", "cli.py", "download", "--tracks", job.tracks_path,
               "--source", job.source, "--only", only_key]
        if job.include_existing:
            cmd.append("--include-existing")
        if not job.download_cover:
            cmd.append("--no-cover")
        if not job.download_lyrics:
            cmd.append("--no-lyrics")
        if job.music_dir:
            cmd.extend(["--music-dir", job.music_dir])
        return cmd

    def _append_ledger(self, job: Job, track: dict, status: str) -> None:
        """GUI 侧补写台账行（跳过的曲目），results.jsonl 保持逐曲一条的约定。"""
        try:
            res = job.cwd / "tasks" / "results.jsonl"
            res.parent.mkdir(parents=True, exist_ok=True)
            rec = {"uri": track.get("uri"), "status": status, "source": "gui",
                   "track": {"name": track.get("name"), "artists": track.get("artists")},
                   "ts": _now_h()}
            with res.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _cancel_rest(self, job: Job, rest: list) -> None:
        """取消收尾（契约①）：剩余未开工曲目逐条补 cancelled 台账，与 skip 补台账同范式。"""
        for t in rest:
            self._append_ledger(job, t, "cancelled")
        if rest:
            job.log.append(f"[runner] 已取消：剩余 {len(rest)} 首补写 cancelled 台账")

    def _run_download_pertrack(self, job: Job) -> None:
        """逐曲模式：每首歌一个 --only 子进程。

        暂停 = 干完当前首后不再开下一首；跳过 = 立即终止当前首、开下一首；
        取消 = 终止当前首 + 停止发新曲，剩余曲目逐条补 cancelled 台账。
        断点续跑由 results.jsonl 的 downloaded 台账天然支持。
        """
        n = len(job.tracks_list)
        job.log.append(f"[runner] 逐曲模式：共 {n} 首（支持 ⏸ 暂停 / ⏭ 跳过 / ⏹ 取消）")
        t_tail = threading.Thread(target=_tail_results, args=(job,), daemon=True)
        t_tail.start()
        for i, t in enumerate(job.tracks_list):
            # 暂停/跳过/取消闸门：当前没有子进程在跑时的状态处理
            while True:
                if job.cancel_requested or job.skip_requested or not job.paused:
                    break
                job.summary = "已暂停（点「继续」恢复）"
                time.sleep(0.5)
            if job.cancel_requested:
                # 契约①：停止发新曲，未开工曲目（含当前这首）逐条补 cancelled 台账
                self._cancel_rest(job, job.tracks_list[i:])
                break
            if job.skip_requested:
                job.skip_requested = False
                job.log.append(f"[runner] 已跳过：{t.get('name')}")
                self._append_ledger(job, t, "skipped")
                continue

            uri = str(t.get("uri") or "")
            only_key = uri.split(":")[-1] if uri else str(t.get("name") or "")
            job.summary = f"正在处理 {i + 1}/{n}：{t.get('name')}"
            job.current = {"uri": uri, "name": t.get("name")}
            job.log.append(f"[runner] ({i + 1}/{n}) {t.get('name')}")
            before = job.done
            proc = subprocess.Popen(self._download_cmd(job, only_key),
                                    cwd=str(job.cwd),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            job.current_proc = proc
            job._started_tracks += 1
            assert proc.stdout is not None
            killed = False
            for raw in iter(proc.stdout.readline, b""):
                if job.skip_requested or job.cancel_requested:
                    _kill_proc_tree(proc)
                    killed = True
                    break
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if line:
                    job.log.append(line)
            proc.wait()
            job.current = None
            job.current_proc = None
            if not killed and job.cancel_requested and proc.returncode != 0:
                # 取消请求到达时子进程恰好静默无输出：stdout EOF 直接结束循环，
                # kill 已由取消端点对 job.current_proc 完成，这里补终止语义
                killed = True
            if killed:
                # 等台账尾巴追上来；确认这条曲没有台账记录才补 skipped/cancelled
                time.sleep(1.3)
                if job.done == before:
                    self._append_ledger(job, t,
                                        "cancelled" if job.cancel_requested else "skipped")
            elif proc.returncode != 0:
                job.log.append(f"[runner] 退出码 {proc.returncode}（台账已记录）")
        job._stop_tail.set()

    @staticmethod
    def _parse_list_lines(raw_text: str) -> list[dict]:
        import cli as _cli
        rows: list[dict] = []
        for idx, line in enumerate((raw_text or "").splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            rows.append(_cli._list_track_map(s, idx))
        return rows

    def _run_prepare_list_search(self, job: Job) -> None:
        """文本清单含无歌手行时，自动联网搜索多个版本候选并与目标曲库三层查重。"""
        from flac_hunter.library import LibraryIndex
        from flac_hunter.match.normalize import sanitize
        from flac_hunter.upgrade import _netease_search

        cfg = self.cfg
        music = Path(job.music_dir or cfg.paths.music).expanduser()
        out_path = Path(job.tracks_path or "")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        raw_tracks = self._parse_list_lines(job.list_text or "")
        expanded: list[dict] = []
        for t in raw_tracks:
            name = str(t.get("name") or "").strip()
            artists = [str(a).strip() for a in (t.get("artists") or []) if str(a).strip()]
            if artists or not name:
                expanded.append(t)
                continue
            job.log.append(f"[prepare] 正在搜索「{name}」的多版本候选…")
            cands = []
            try:
                cands = _netease_search(name, cfg=cfg) or []
            except Exception as exc:
                job.log.append(f"[prepare] 搜索失败（{exc}），保留原条目")
            if not cands:
                expanded.append(t)
                continue
            for item in cands[:8]:
                sid = str(item.get("id") or "").strip()
                if not sid:
                    continue
                raw_art = str(item.get("artists") or "")
                art_list = [a.strip() for a in raw_art.split(",") if a.strip()]
                dur_s = item.get("dur")
                dur_ms = int(round(float(dur_s) * 1000)) if dur_s else None
                expanded.append({
                    "type": "netease",
                    "uri": f"netease:{sid}",
                    "name": str(item.get("name") or name),
                    "artists": art_list,
                    "album": None,
                    "duration_ms": dur_ms,
                    "image_url": None,
                    "from_search": True,
                })
            job.log.append(f"[prepare] 「{name}」展开为 {min(len(cands), 8)} 个候选版本")

        idx = LibraryIndex(str(music), cfg)
        if music.is_dir():
            idx.scan()
        records: list[dict] = []
        for pos, t in enumerate(expanded, 1):
            artists = [str(a) for a in (t.get("artists") or [])]
            name_clean = sanitize(str(t.get("name") or ""))
            artist_parts = [sanitize(a) for a in artists if str(a).strip()]
            artist_parts = [a for a in artist_parts if a]
            rec = {
                "type": t.get("type") or "list",
                "uri": t.get("uri"),
                "name": str(t.get("name") or ""),
                "artists": artists,
                "album": t.get("album"),
                "position": pos,
                "duration_ms": t.get("duration_ms"),
                "image_url": t.get("image_url"),
                "filename_stem": f"{name_clean} - {' _ '.join(artist_parts)}" if artist_parts else name_clean,
                "from_search": bool(t.get("from_search")),
                "existing": False,
                "existing_file": None,
                "dedupe_reason": None,
            }
            res = idx.dedupe_track(rec) if music.is_dir() else None
            entry, reason = (res[0], res[1]) if isinstance(res, tuple) else (None, None)
            if isinstance(entry, dict):
                entry = entry.get("path") or entry.get("file")
            if reason in ("artist", "duration") and entry:
                rec["existing"] = True
                rec["existing_file"] = entry
                rec["dedupe_reason"] = reason
            elif reason == "same_title_other":
                rec["dedupe_reason"] = "same_title_other"
            records.append(rec)

        out_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        job.log.append(f"[prepare] tracks.json 写入 {len(records)} 条 -> {out_path}")

    def _run_audit(self, job: Job) -> None:
        """服务内直跑四项质量门：全量结构化结果，逐文件推进度。"""
        from flac_hunter.audit import audit_one

        cfg = self.cfg
        music = Path(job.music_dir or cfg.paths.music)
        if not music.is_dir():
            job.log.append(f"[audit] 曲库目录不存在: {music}")
            job.exit_code = 1
            return
        if job.audit_files is not None:
            wanted = []
            seen = set()
            for raw in job.audit_files:
                nm = Path(str(raw)).name
                if nm and nm not in seen and (music / nm).is_file():
                    seen.add(nm)
                    wanted.append(music / nm)
            files = wanted
        else:
            files = sorted(music.glob("*.flac"))
        job.total = len(files)
        job.log.append(f"[audit] {len(files)} 个 .flac，逐个四项门检查…")
        try:
            params = set(inspect.signature(audit_one).parameters)
        except (TypeError, ValueError):
            params = set()
        kwargs = {}
        for name in ("duration_ms", "expect_ms"):
            if name in params:
                kwargs[name] = None  # 无期望时长来源，时长门交由调用方配置
                break
        if "dur_tol" in params:
            kwargs["dur_tol"] = getattr(cfg.match, "verify_win", 15.0)

        passed = failed = 0
        by_issue: dict = {}
        files_out: list = []
        for f in files:
            if job.cancel_requested:
                # 契约③：audit 取消 → 逐文件协作检查，break 后已完成部分保留在 job.audit
                job.log.append(f"[audit] 已取消：完成 {job.done}/{len(files)}，保留已完成结果")
                break
            try:
                r = audit_one(str(f), **kwargs)
            except TypeError:
                try:
                    r = audit_one(str(f))
                except Exception as exc:
                    r = {"path": str(f), "dur_ok": True, "tags_ok": True, "jpg_ok": True,
                         "flac_ok": False, "issues": [f"扫描异常: {exc}"]}
            except Exception as exc:
                r = {"path": str(f), "dur_ok": True, "tags_ok": True, "jpg_ok": True,
                     "flac_ok": False, "issues": [f"扫描异常: {exc}"]}
            issues = [str(x) for x in (r.get("issues") or [])]
            if not issues:
                failed_gates = [GATE_ZH[g] for g in ("dur_ok", "tags_ok", "jpg_ok", "flac_ok")
                                if r.get(g) is not True]
                issues = failed_gates
            if issues:
                failed += 1
                for it in issues:
                    by_issue[it] = by_issue.get(it, 0) + 1
                if len(files_out) < AUDIT_FILES_CAP:
                    files_out.append({"name": Path(str(r.get("path") or f)).name,
                                      "issues": issues})
            else:
                passed += 1
            job.done += 1
        job.audit = {"total": job.total, "pass": passed, "fail": failed,
                     "by_issue": by_issue, "files": files_out, "music_dir": str(music)}
        job.log.append(f"[audit] 完成：通过 {passed}，不合格 {failed}（明细见审计页）")
        # 持久化最近一次审计结果：服务重启后审计页仍能回显
        try:
            out_dir = job.cwd / "tasks" / "gui"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "last_audit.json").write_text(
                json.dumps({"audit": job.audit, "when": job.started_h, "id": job.id},
                           ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def _library_counts(music_dir: str) -> dict:
    """曲库统计：只数音频文件（jpg/lrc 侧车不计入）。"""
    counts = {"flac": 0, "mp3": 0, "ogg": 0, "other": 0}
    audio = {"flac", "mp3", "ogg", "m4a", "opus", "wav"}
    total = 0
    try:
        for e in __import__("os").scandir(music_dir):
            if not e.is_file():
                continue
            ext = e.name.rsplit(".", 1)[-1].lower() if "." in e.name else ""
            if ext not in audio:
                continue
            total += 1
            if ext in counts:
                counts[ext] += 1
            else:
                counts["other"] += 1
    except OSError:
        pass
    return {"total": total, **counts}


def _lyric_issue_text(kind: str, entry) -> str:
    """把 check_lyrics_dir（audit.py:447）的单条目渲染为人类可读 issue 串。

    纯展示包装，不改判定逻辑；条目形态随 kind 而异（audit.py:478-518）：
    orphan/empty/no_timestamps 为 lrc 文件名 str；meta_title/meta_artist 为
    (lrc名, 元数据值, 音频段) 元组；too_long/too_short 为 (lrc名, 末行秒, 音频秒)
    元组（单位秒，audit.py:512-514）；dup_content 为重复文件名列表。
    """
    if kind in ("orphan", "empty", "no_timestamps"):
        return f"{kind}: {entry}"
    if kind == "meta_title":
        return f"meta_title: lrc ti={entry[1]} ≠ 音频标题 {entry[2]}"
    if kind == "meta_artist":
        return f"meta_artist: lrc ar={entry[1]} ≠ 音频歌手 {entry[2]}"
    if kind == "too_long":
        return f"too_long: 末行 {entry[1]}s > 音频 {entry[2]}s"
    if kind == "too_short":
        return f"too_short: 末行 {entry[1]}s << 音频 {entry[2]}s"
    if kind == "dup_content":
        return "dup_content: " + "/".join(str(x) for x in entry) + " 内容重复"
    return f"{kind}: {entry}"


def _kill_proc_tree(proc: subprocess.Popen) -> None:
    """终止子进程及其派生进程（Windows 下避免 yt-dlp / ffmpeg 残留）。"""
    if os.name == "nt" and proc.pid:
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except Exception:
            pass
    try:
        if proc.poll() is None:
            proc.kill()
    except Exception:
        pass


def _resolve_tracks_path(path: str) -> Path:
    """校验 tracks.json 位于仓库目录内，防前缀/大小写/兄弟目录绕过。"""
    if not path:
        raise ValueError("tracks.json 路径为空")
    p = Path(path)
    if not p.is_absolute():
        p = REPO / p
    p = p.resolve()
    if not (p.is_relative_to(REPO) and p.name == "tracks.json" and p.is_file()):
        raise ValueError("tracks.json 路径不合法")
    return p


def _read_tracks(path: str, include_existing: bool, only: list | None) -> tuple[list, int]:
    """读 prepare 产出的 tracks.json，返回 (目标曲目列表, 目标数)。"""
    p = _resolve_tracks_path(path)
    d = json.loads(p.read_text(encoding="utf-8"))
    records = d if isinstance(d, list) else d.get("records") or []
    targets = [r for r in records if isinstance(r, dict)]
    if only is not None:
        wanted = {str(x).strip() for x in only if str(x).strip()}

        def _match(r: dict) -> bool:
            uri = str(r.get("uri") or "")
            tail = uri.split(":")[-1] if uri else ""
            name = str(r.get("name") or "")
            pos = f"pos:{r.get('position')}"
            return bool(
                (uri and uri in wanted)
                or (tail and tail in wanted)
                or (name and name in wanted)
                or (pos in wanted)
            )

        targets = [r for r in targets if _match(r)]
    if not include_existing:
        targets = [r for r in targets if not r.get("existing")]
    return targets, len(targets)


_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_MAX_BODY_BYTES = 4 * 1024 * 1024


class _LocalServer(ThreadingHTTPServer):
    allow_reuse_address = True


def _list_dirs(raw_path: str, fallback: str) -> dict:
    """列出本地磁盘盘符与指定目录下的子文件夹，供网页目录选择器浏览。"""
    drives: list[str] = []
    if os.name == "nt":
        for ch in "CDEFGHIJKLMNOPQRSTUVWXYZAB":
            d = f"{ch}:\\"
            if os.path.isdir(d):
                drives.append(d)
    p = Path(raw_path.strip() or fallback or str(REPO)).expanduser()
    try:
        p = p.resolve()
    except OSError:
        p = REPO
    while not p.is_dir() and p.parent != p:
        p = p.parent
    if not p.is_dir():
        p = REPO
    dirs: list[dict[str, str]] = []
    try:
        for entry in sorted(p.iterdir(), key=lambda x: x.name.lower()):
            if entry.is_dir() and not entry.name.startswith("."):
                dirs.append({"name": entry.name, "path": str(entry)})
                if len(dirs) >= 200:
                    break
    except OSError:
        pass
    parent = str(p.parent) if p.parent != p else ""
    return {"current": str(p), "parent": parent, "drives": drives, "dirs": dirs}


def _save_default_music_dir(new_dir: str) -> str:
    """校验并持久化默认曲库目录到 config.toml [paths].music。"""
    import re

    p = Path(new_dir.strip()).expanduser()
    if not p.is_dir():
        raise ValueError(f"曲库目录不存在或不是文件夹: {p}")
    resolved = str(p.resolve())
    cfg_path = REPO / "config.toml"
    escaped = resolved.replace("\\", "\\\\").replace('"', '\\"')
    new_line = f'music = "{escaped}"'
    if cfg_path.exists():
        lines = cfg_path.read_text(encoding="utf-8").splitlines()
        out_lines = []
        in_paths = False
        replaced = False
        inserted_section = False
        for ln in lines:
            stripped = ln.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if in_paths and not replaced:
                    out_lines.append(new_line)
                    replaced = True
                in_paths = stripped == "[paths]"
                if in_paths:
                    inserted_section = True
            elif in_paths and re.match(r'^music\s*=', stripped):
                ln = new_line
                replaced = True
            out_lines.append(ln)
        if in_paths and not replaced:
            out_lines.append(new_line)
            replaced = True
        if not inserted_section and not replaced:
            out_lines.extend(["", "[paths]", new_line])
        cfg_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    else:
        cfg_path.write_text(f"[paths]\n{new_line}\n", encoding="utf-8")
    return resolved


class Handler(BaseHTTPRequestHandler):
    runner: Runner

    def log_message(self, fmt, *args):  # 静默访问日志
        pass

    def _no_cache(self) -> None:
        """禁止一切缓存：页面与 API 永远拿最新（浏览器曾缓存 v1 页面导致新版打不开）。"""
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")

    def _is_local_request(self, check_origin: bool = False) -> bool:
        host = (self.headers.get("Host") or "").strip()
        if host:
            parsed_host = urlparse(f"http://{host}").hostname
            if parsed_host not in _LOCAL_HOSTS:
                return False
        if check_origin:
            fetch_site = (self.headers.get("Sec-Fetch-Site") or "").strip().lower()
            if fetch_site == "cross-site":
                return False
            origin = (self.headers.get("Origin") or "").strip()
            if origin:
                if origin == "null":
                    return False
                parsed = urlparse(origin)
                if parsed.scheme not in ("http", "https") or parsed.hostname not in _LOCAL_HOSTS:
                    return False
        return True

    def _json(self, obj, code: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._no_cache()
        self._security_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        raw_len = self.headers.get("Content-Length")
        if raw_len is None or raw_len == "":
            return {}
        try:
            n = int(raw_len)
        except ValueError as exc:
            raise ValueError("Content-Length 非法") from exc
        if n < 0 or n > _MAX_BODY_BYTES:
            raise ValueError("请求体大小超出限制")
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self):  # noqa: N802
        if not self._is_local_request(check_origin=False):
            self._json({"error": "forbidden"}, 403)
            return
        if self.path == "/" or self.path.startswith("/index"):
            body = PAGE_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._no_cache()
            self._security_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/state":
            with self.runner.lock:
                jobs = [self.runner.jobs[i].snapshot()
                        for i in reversed(self.runner.order)]
            self._json({"library": _library_counts(self.runner.cfg.paths.music),
                        "music_dir": str(self.runner.cfg.paths.music),
                        "jobs": jobs})
        elif self.path.startswith("/api/job/"):
            jid = self.path.rsplit("/", 1)[-1]
            job = self.runner.jobs.get(jid)
            if job is None:
                self._json({"error": "no such job"}, 404)
                return
            self._json(job.snapshot(with_log=True))
        elif self.path.startswith("/api/audit/files"):
            qs = parse_qs(urlparse(self.path).query)
            raw_dir = (qs.get("dir", [""])[0] or "").strip()
            mdir = Path(raw_dir or str(self.runner.cfg.paths.music)).expanduser()
            if not mdir.is_dir():
                self._json({"error": f"目录不存在: {mdir}"}, 400)
                return
            flist = sorted(f.name for f in mdir.glob("*.flac"))
            self._json({"music_dir": str(mdir), "files": flist})
        elif self.path.startswith("/api/upgrade/files"):
            qs = parse_qs(urlparse(self.path).query)
            raw_dir = (qs.get("dir", [""])[0] or "").strip()
            ext = (qs.get("ext", ["all"])[0] or "all").lower()
            mdir = Path(raw_dir or str(self.runner.cfg.paths.music)).expanduser()
            if not mdir.is_dir():
                self._json({"error": f"目录不存在: {mdir}"}, 400)
                return
            exts = {
                "mp3": (".mp3",),
                "ogg": (".ogg",),
                "all": (".mp3", ".ogg"),
                "flac": (".flac",),
            }.get(ext, (".mp3", ".ogg"))
            items = [
                {"name": f.name, "ext": f.suffix.lower().lstrip(".")}
                for f in sorted(mdir.iterdir(), key=lambda x: x.name.lower())
                if f.is_file() and f.suffix.lower() in exts
            ]
            self._json({"music_dir": str(mdir), "files": items})
        elif self.path.startswith("/api/dedupe"):
            from flac_hunter.library import find_dups_candidates
            qs = parse_qs(urlparse(self.path).query)
            raw_dir = (qs.get("dir", [""])[0] or "").strip()
            if "\x00" in raw_dir:
                self._json({"error": "查重目录路径非法"}, 400)
                return
            mdir = Path(raw_dir or str(self.runner.cfg.paths.music)).expanduser()
            if not mdir.is_dir():
                self._json({"error": f"目录不存在: {mdir}"}, 400)
                return
            groups = find_dups_candidates(mdir, self.runner.cfg)
            enriched = []
            for g in groups:
                mems = []
                for m in g.get("members") or []:
                    fname = str(m.get("file") or "")
                    fp = mdir / fname
                    sz = fp.stat().st_size if fp.is_file() else 0
                    br = m.get("bit_rate")
                    kbps = round(float(br) / 1000) if br else 0
                    mems.append({
                        "file": fname,
                        "ext": fp.suffix.lower().lstrip("."),
                        "size": sz,
                        "duration": m.get("duration"),
                        "bitrate_kbps": kbps,
                    })
                enriched.append({
                    "title_key": g.get("title_key") or "",
                    "artist_key": g.get("artist_key") or "",
                    "reason": g.get("reason") or "",
                    "members": mems,
                })
            self._json({
                "music_dir": str(mdir),
                "groups": enriched,
                "total_groups": len(enriched),
                "total_files": sum(len(g["members"]) for g in enriched),
            })
        elif self.path.startswith("/api/library/files"):
            # 曲库音频文件索引（侧车 .jpg/.lrc 与子目录不计，口径同 _library_counts）
            from flac_hunter.library import AUDIO_EXT  # library.py:21
            qs = parse_qs(urlparse(self.path).query)
            mdir = Path(str(self.runner.cfg.paths.music)).expanduser()
            if not mdir.is_dir():
                self._json({"error": f"目录不存在: {mdir}"}, 400)
                return
            q = (qs.get("q", [""])[0] or "").strip().lower()
            ext = (qs.get("ext", [""])[0] or "").strip().lower().lstrip(".")
            try:
                page = max(1, int(qs.get("page", ["1"])[0] or 1))
            except ValueError:
                page = 1
            try:
                page_size = int(qs.get("page_size", ["50"])[0] or 50)
            except ValueError:
                page_size = 50
            page_size = min(max(1, page_size), 500)  # 上限 500（契约冻结）
            files: list[dict] = []
            try:
                for e in os.scandir(mdir):
                    if not e.is_file():
                        continue
                    suf = Path(e.name).suffix.lower().lstrip(".")
                    if f".{suf}" not in AUDIO_EXT:
                        continue
                    if q and q not in e.name.lower():
                        continue  # q = 文件名大小写不敏感子串过滤
                    if ext and suf != ext:
                        continue  # ext = 小写格式过滤（兼容 ".mp3" 传参）
                    try:
                        st = e.stat()
                    except OSError:
                        continue
                    # 单位纪律：size_mb = 字节 / 1048576 保留 1 位；mtime 精确到分
                    files.append({
                        "name": e.name, "ext": suf,
                        "size_mb": round(st.st_size / 1048576, 1),
                        "mtime_h": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
                    })
            except OSError:
                pass
            files.sort(key=lambda d: d["name"].lower())  # 文件名不区分大小写排序
            start = (page - 1) * page_size
            self._json({"music_dir": str(mdir), "total": len(files),
                        "page": page, "page_size": page_size,
                        "files": files[start:start + page_size]})
        elif self.path.startswith("/api/lyrics/report"):
            # 包装 audit.py:447 check_lyrics_dir 八类歌词体检 → 结构化分组（纯包装，不加判定）
            from flac_hunter.audit import check_lyrics_dir
            mdir = str(self.runner.cfg.paths.music)
            if not Path(mdir).expanduser().is_dir():
                self._json({"error": f"目录不存在: {mdir}"}, 400)
                return
            raw = check_lyrics_dir(mdir, self.runner.cfg)
            groups = []
            total = 0
            for kind in ("orphan", "meta_title", "meta_artist", "too_long",
                         "too_short", "dup_content", "empty", "no_timestamps"):
                files = []
                for e in (raw.get(kind) or []):
                    if isinstance(e, (list, tuple)):
                        name = str(e[0]) if e else ""  # 元组/列表统一取 lrc 文件名（首元素）
                    else:
                        name = str(e)
                    files.append({"name": name, "issue": _lyric_issue_text(kind, e)})
                groups.append({"kind": kind, "count": len(files), "files": files})
                total += len(files)
            self._json({"music_dir": mdir, "total": total, "groups": groups})
        elif self.path.startswith("/api/rename/scan"):
            # 包装 audit.py:161 scan_rename（dry-run 计划）→ [{old,new,kinds}]，不自加匹配逻辑
            from flac_hunter.audit import scan_rename
            mdir = str(self.runner.cfg.paths.music)
            if not Path(mdir).expanduser().is_dir():
                self._json({"error": f"目录不存在: {mdir}"}, 400)
                return
            plans = scan_rename(mdir, self.runner.cfg)
            items = [{"old": p.get("old"),
                      "new": p.get("new") or p.get("proposal"),
                      "kinds": [str(k) for k in (p.get("issues") or [])]}
                     for p in plans if isinstance(p, dict)]
            self._json(items)
        elif self.path.startswith("/api/fingerprint"):
            # 包装 ffmpeg.py:147 pcm_md5（stdout 形如 "MD5=hex"）→ {a_md5,b_md5,match}
            from flac_hunter.ffmpeg import pcm_md5
            qs = parse_qs(urlparse(self.path).query)
            a = (qs.get("a", [""])[0] or "").strip()
            b = (qs.get("b", [""])[0] or "").strip()
            if not a or not b:
                self._json({"error": "缺少 a/b 两个音频路径参数"}, 400)
                return
            pa, pb = Path(a).expanduser(), Path(b).expanduser()
            if not pa.is_file():
                self._json({"error": f"文件不存在: {a}"}, 400)
                return
            if not pb.is_file():
                self._json({"error": f"文件不存在: {b}"}, 400)
                return
            try:
                ra, rb = pcm_md5(str(pa)), pcm_md5(str(pb))
            except Exception as exc:  # noqa: BLE001
                self._json({"error": f"指纹计算失败: {str(exc)[:200]}"}, 400)
                return

            def _md5_clean(s: str) -> str:
                """剥 "MD5=" 前缀与空白 → 32 位小写 hex。"""
                s = str(s or "").strip()
                if s.upper().startswith("MD5="):
                    s = s[len("MD5="):]
                return s.strip().lower()

            ma, mb = _md5_clean(ra), _md5_clean(rb)
            self._json({"a_md5": ma, "b_md5": mb,
                        "match": bool(ma and mb and ma == mb)})
        elif self.path == "/api/audit/last":
            p = REPO / "tasks" / "gui" / "last_audit.json"
            if p.exists():
                try:
                    self._json(json.loads(p.read_text(encoding="utf-8")))
                except Exception as e:
                    self._json({"error": str(e)}, 500)
            else:
                self._json({"audit": None})
        elif self.path.startswith("/api/dirs"):
            qs = parse_qs(urlparse(self.path).query)
            raw_p = qs.get("path", [""])[0]
            self._json(_list_dirs(raw_p, str(self.runner.cfg.paths.music)))
        elif self.path.startswith("/api/tracks"):
            qs = parse_qs(urlparse(self.path).query)
            path = (qs.get("path") or [""])[0]
            try:
                p = _resolve_tracks_path(path)
                d = json.loads(p.read_text(encoding="utf-8"))
                records = d if isinstance(d, list) else d.get("records") or []
                slim = [{"position": r.get("position"), "name": r.get("name"),
                         "artists": r.get("artists"), "album": r.get("album"),
                         "duration_ms": r.get("duration_ms"),
                         "existing": bool(r.get("existing")),
                         "existing_file": Path(str(r.get("existing_file"))).name if r.get("existing_file") else "",
                         "from_search": bool(r.get("from_search")),
                         "uri": r.get("uri")}
                        for r in records if isinstance(r, dict)]
                self._json({"records": slim})
            except Exception as e:
                self._json({"error": str(e)}, 400)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):  # noqa: N802
        if not self._is_local_request(check_origin=True):
            self._json({"error": "forbidden"}, 403)
            return
        r = self.runner
        try:
            body = self._body()
            if self.path == "/api/prepare":
                out = REPO / "tasks" / "gui" / time.strftime("%Y%m%d_%H%M%S") / "tracks.json"
                prep_dir = str(body.get("music_dir") or "").strip()
                if "\x00" in prep_dir:
                    raise ValueError("查重目录路径非法")
                if body.get("uri"):
                    cmd = [PY, "-X", "utf8", "cli.py", "prepare",
                           "--uri", str(body["uri"]), "--out", str(out)]
                elif body.get("list_text"):
                    raw_text = str(body["list_text"])
                    out.parent.mkdir(parents=True, exist_ok=True)
                    lst = out.parent / "list.txt"
                    lst.write_text(raw_text, encoding="utf-8")
                    parsed_rows = Runner._parse_list_lines(raw_text)
                    has_bare_title = any(not (row.get("artists") or []) for row in parsed_rows)
                    if has_bare_title:
                        norm_dir = str(Path(prep_dir).expanduser()) if prep_dir else ""
                        job = r.submit("prepare", None, tracks_path=str(out),
                                       music_dir=norm_dir, list_text=raw_text)
                        self._json(job)
                        return
                    cmd = [PY, "-X", "utf8", "cli.py", "prepare",
                           "--list", str(lst), "--out", str(out)]
                else:
                    raise ValueError("需要 uri 或 list_text")
                if prep_dir:
                    cmd.extend(["--music-dir", str(Path(prep_dir).expanduser())])
                job = r.submit("prepare", cmd, tracks_path=str(out))
                self._json(job)
            elif self.path == "/api/download":
                tracks = str(body.get("tracks") or "")
                raw_only = body.get("only")
                only = None if raw_only is None else list(raw_only)
                music_dir = str(body.get("music_dir") or "").strip()
                if "\x00" in music_dir:
                    raise ValueError("下载目录路径非法")
                if music_dir:
                    md = Path(music_dir).expanduser()
                    if md.exists() and not md.is_dir():
                        raise ValueError("下载目录已存在且不是文件夹")
                    music_dir = str(md)
                targets, total = _read_tracks(
                    tracks, bool(body.get("include_existing")), only)
                if total == 0:
                    raise ValueError("没有可下载的目标（全部已存在或选择为空）")
                job = r.submit("download", None, total=total, tracks_path=tracks,
                               tracks_list=targets,
                               source=str(body.get("source") or "auto"),
                               include_existing=bool(body.get("include_existing")),
                               music_dir=music_dir,
                               download_cover=bool(body.get("download_cover", True)),
                               download_lyrics=bool(body.get("download_lyrics", True)))
                self._json(job)
            elif self.path == "/api/upgrade":
                ext = str(body.get("ext") or "mp3")
                if ext not in ("mp3", "ogg", "all"):
                    raise ValueError("ext 仅支持 mp3/ogg/all")
                cmd = [PY, "-X", "utf8", "cli.py", "upgrade", "--ext", ext]
                if body.get("full_retry"):
                    cmd.append("--full-retry")
                up_dir = str(body.get("music_dir") or "").strip()
                if "\x00" in up_dir:
                    raise ValueError("曲库目录路径非法")
                if up_dir:
                    cmd.extend(["--music-dir", str(Path(up_dir).expanduser())])
                up_total = 0
                raw_files = body.get("files")
                if isinstance(raw_files, list):
                    cleaned = [Path(str(x)).name for x in raw_files if str(x).strip()]
                    if not cleaned:
                        raise ValueError("待升级文件列表为空")
                    up_total = len(cleaned)
                    fpath = REPO / "tasks" / "gui" / f"upgrade_files_{uuid.uuid4().hex[:8]}.json"
                    fpath.parent.mkdir(parents=True, exist_ok=True)
                    fpath.write_text(json.dumps(cleaned, ensure_ascii=False), encoding="utf-8")
                    cmd.extend(["--files", str(fpath)])
                job = r.submit("upgrade", cmd, total=up_total, music_dir=up_dir)
                self._json(job)
            elif self.path.endswith("/pause") and self.path.startswith("/api/job/"):
                jid = self.path.split("/")[3]
                job = r.jobs.get(jid)
                if job is None or job.type != "download" or job.tracks_list is None:
                    raise ValueError("仅下载作业支持暂停/继续")
                job.paused = bool(body.get("paused"))
                self._json(job.snapshot())
            elif self.path.endswith("/skip") and self.path.startswith("/api/job/"):
                jid = self.path.split("/")[3]
                job = r.jobs.get(jid)
                if job is None or job.type != "download" or job.tracks_list is None:
                    raise ValueError("仅下载作业支持跳过")
                job.skip_requested = True
                self._json(job.snapshot())
            elif self.path.endswith("/cancel") and self.path.startswith("/api/job/"):
                # 契约①：取消作业（逐曲=停发新曲+终止当前曲+剩余补 cancelled 台账；
                # 子进程=terminate；audit=协作标志逐文件检查；queued=取出时跳过）
                jid = self.path.split("/")[3]
                job = r.jobs.get(jid)
                if job is None:
                    raise ValueError(f"作业不存在: {jid}")
                if job.ended is not None:
                    raise ValueError("作业已结束，无法取消")
                job.cancel_requested = True
                job.cancelled = True
                tracks = job.tracks_list or []
                # 被终止的当前曲也会补一条 cancelled 台账，计入剩余口径
                inflight = 1 if job.current_proc is not None else 0
                job.cancelled_remaining = max(0, len(tracks) - job._started_tracks + inflight)
                proc = job.current_proc
                if proc is not None and proc.poll() is None:
                    # 立即终止当前子进程：readline 阻塞期也能生效（EOF 唤醒作业线程）
                    _kill_proc_tree(proc)
                self._json(job.snapshot())
            elif self.path == "/api/audit":
                aud_dir = str(body.get("music_dir") or "").strip()
                if "\x00" in aud_dir:
                    raise ValueError("审计目录路径非法")
                raw_files = body.get("files")
                aud_files = None
                if isinstance(raw_files, list):
                    aud_files = [Path(str(x)).name for x in raw_files if str(x).strip()]
                job = r.submit("audit", None, music_dir=aud_dir, audit_files=aud_files)  # 服务内直跑，不走子进程
                self._json(job)
            elif self.path == "/api/dedupe/delete":
                from flac_hunter.library import AUDIO_EXT
                from flac_hunter.util import cross_move
                raw_dir = str(body.get("music_dir") or "").strip()
                if "\x00" in raw_dir:
                    raise ValueError("查重目录路径非法")
                mdir = Path(raw_dir or str(r.cfg.paths.music)).expanduser()
                if not mdir.is_dir():
                    raise ValueError(f"目录不存在: {mdir}")
                raw_files = body.get("files")
                if not isinstance(raw_files, list) or not raw_files:
                    raise ValueError("请先勾选要清理的重复文件")
                trash_dir = Path(r.cfg.paths.staging) / "dedupe_trash" / time.strftime("%Y%m%d_%H%M%S")
                trash_dir.mkdir(parents=True, exist_ok=True)
                moved: list[str] = []
                errs: list[str] = []
                mdir_resolved = mdir.resolve()
                for item in raw_files:
                    fname = Path(str(item)).name
                    if not fname:
                        continue
                    fp = (mdir / fname)
                    if not fp.is_file() or fp.resolve().parent != mdir_resolved:
                        errs.append(f"跳过不存在或越界文件: {fname}")
                        continue
                    if fp.suffix.lower() not in AUDIO_EXT:
                        errs.append(f"跳过非音频文件: {fname}")
                        continue
                    try:
                        cross_move(fp, trash_dir / fname)
                        moved.append(fname)
                    except Exception as exc:
                        errs.append(f"{fname}: {exc}")
                self._json({
                    "moved": moved,
                    "trash_dir": str(trash_dir),
                    "errors": errs,
                    "library": _library_counts(r.cfg.paths.music),
                })
            elif self.path == "/api/lyrics/delete":
                # 契约④：{files:[绝对路径]} → cross_move 移入 staging/lrc_trash/<ts>/（可恢复，绝不 unlink）
                from flac_hunter.util import cross_move  # util.py:99
                raw_files = body.get("files")
                if not isinstance(raw_files, list) or not raw_files:
                    raise ValueError("请提供要删除的 .lrc 文件路径列表")
                trash_dir = Path(r.cfg.paths.staging) / "lrc_trash" / time.strftime("%Y%m%d_%H%M%S")
                mdir_res = Path(str(r.cfg.paths.music)).expanduser().resolve()
                moved: list[str] = []
                failed: list[str] = []
                for item in raw_files:
                    p = Path(str(item or "").strip())
                    try:
                        if not p.name or not p.is_absolute():
                            failed.append(f"非绝对路径: {p.name or item}")
                            continue
                        if p.suffix.lower() != ".lrc":
                            failed.append(f"非 .lrc 文件: {p.name}")
                            continue
                        if not p.is_file():
                            failed.append(f"文件不存在: {p.name}")
                            continue
                        if p.resolve().parent != mdir_res:
                            # 曲库边界：只允许移曲库顶层的 .lrc（与 dedupe/delete 同范式）
                            failed.append(f"越界（仅限曲库目录）: {p.name}")
                            continue
                        trash_dir.mkdir(parents=True, exist_ok=True)
                        # 同名不覆盖：trash 内已存在则加序号（可恢复铁律，绝不静默覆盖副本）
                        dest = trash_dir / p.name
                        k = 1
                        while dest.exists():
                            dest = trash_dir / f"{p.stem}_{k}{p.suffix}"
                            k += 1
                        cross_move(p, dest)
                        moved.append(p.name)
                    except Exception as exc:  # noqa: BLE001
                        failed.append(f"{p.name}: {str(exc)[:120]}")
                self._json({"moved": moved, "failed": failed,
                            "trash_dir": str(trash_dir) if moved else ""})
            elif self.path == "/api/rename/apply":
                # 契约⑥：{items:[{old,new}]} → audit.py:183 apply_rename（改名+sidecar 同步，目标已存在则跳过）
                from flac_hunter.audit import apply_rename
                from flac_hunter.library import AUDIO_EXT  # library.py:21
                raw_items = body.get("items")
                if not isinstance(raw_items, list) or not raw_items:
                    raise ValueError("请提供重命名计划 items")
                mdir = Path(str(r.cfg.paths.music)).expanduser()
                if not mdir.is_dir():
                    raise ValueError(f"目录不存在: {mdir}")

                def _has_stem(stem: str) -> bool:
                    return any(q.is_file() and q.stem == stem and q.suffix.lower() in AUDIO_EXT
                               for q in mdir.iterdir())

                # 预检：old 已无音频而 new 已被占用（重放已应用计划）→ 与 apply_rename 的
                # 「目标已存在→skip/name exists」语义对齐（audit.py:230-231），直接产出记录
                records: list = [None] * len(raw_items)
                deferred_idx: list[int] = []
                deferred_plans: list[dict] = []
                for idx, it in enumerate(raw_items):
                    if not isinstance(it, dict):
                        records[idx] = {"old": "", "new": "", "status": "skip", "detail": "非法计划项"}
                        continue
                    old = str(it.get("old") or "").strip()
                    new = str(it.get("new") or it.get("proposal") or "").strip()
                    if not old or not new:
                        records[idx] = {"old": old, "new": new, "status": "skip",
                                        "detail": "计划项缺 old/new"}
                        continue
                    if Path(new).name != new:
                        # new 含路径分隔符/盘符：apply_rename 会在中途抛错留下无痕半成品，
                        # 预检直接拒绝该项（不阻断其余项）
                        records[idx] = {"old": old, "new": new, "status": "skip",
                                        "detail": "new 含路径分隔符，已拒绝"}
                        continue
                    if old and old != new and not _has_stem(old) and _has_stem(new):
                        records[idx] = {"old": old, "new": new,
                                        "status": "skip", "detail": "name exists"}
                        continue
                    deferred_idx.append(idx)
                    deferred_plans.append({"old": old, "new": new})
                # 去重计划后送 apply_rename：其对重复计划/renamed_olds 分支可能少产记录，
                # 裸 zip 会错配——按 (old,new) 键回填，短少时 skip 占位补齐
                uniq_keys: list = []
                for plan in deferred_plans:
                    key = (str(plan.get("old") or ""), str(plan.get("new") or ""))
                    if key not in uniq_keys:
                        uniq_keys.append(key)
                recs = apply_rename(r.cfg, [{"old": k[0], "new": k[1]} for k in uniq_keys]) \
                    if uniq_keys else []
                rec_by_key: dict = {}
                for key, rec in zip(uniq_keys, recs):
                    if isinstance(rec, dict):
                        rec_by_key.setdefault(key, rec)
                for idx, plan in zip(deferred_idx, deferred_plans):
                    key = (str(plan.get("old") or ""), str(plan.get("new") or ""))
                    records[idx] = rec_by_key.get(key) or {
                        "old": plan.get("old"), "new": plan.get("new"),
                        "status": "skip", "detail": "apply_rename 未返回记录"}
                self._json({"records": [rec for rec in records if rec is not None]})
            elif self.path == "/api/config/music-dir":
                raw_dir = str(body.get("music_dir") or "").strip()
                if not raw_dir or "\x00" in raw_dir:
                    raise ValueError("请提供有效的默认曲库文件夹路径")
                saved = _save_default_music_dir(raw_dir)
                r.cfg.paths.music = saved
                self._json({"music_dir": saved, "library": _library_counts(saved)})
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001
            self._json({"error": str(e)}, 400)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="flac-hunter 本地 Web GUI")
    ap.add_argument("--port", type=int, default=8756)
    ap.add_argument("--no-browser", action="store_true", help="不自动开浏览器")
    args = ap.parse_args(argv)

    cfg = load_config()
    # 相对路径/含 ~ 的配置统一展开为绝对路径：所有端点与 apply_rename 共用同一基准
    # （此前 music_dir 为相对值时歌词删除链路整体不可用——独立审查 M3）
    cfg.paths.music = str(Path(cfg.paths.music).expanduser().resolve())
    cfg.paths.staging = str(Path(cfg.paths.staging).expanduser().resolve())
    url = f"http://127.0.0.1:{args.port}"

    class H(Handler):
        pass

    H.runner = Runner(cfg)
    srv = _LocalServer(("127.0.0.1", args.port), H)
    print(f"flac-hunter GUI → {url}（曲库 {cfg.paths.music}，Ctrl+C 退出）", flush=True)
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, [url]).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nGUI 已退出", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
