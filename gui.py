"""flac-hunter 本地 Web GUI（标准库 http.server，零 pip 依赖，仅绑 127.0.0.1 自用）。

用法：python gui.py [--port 8756]  → 自动开浏览器。
核心四件套：歌单导入（含查重预览）→ 勾选下载（实时进度）→ 无损升级 → 质量审计。
作业以子进程方式跑仓库自带的 cli.py（零侵入核心），同一时间只跑一个作业；
进度来自 tasks/results.jsonl 的增量行。其余子命令在更新目标清单里（README）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

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
PY = sys.executable or "python"


def _now_h() -> str:
    return time.strftime("%m-%d %H:%M:%S")


class Job:
    """一个 cli.py 子进程作业；progress 由 results.jsonl 增量行统计。"""

    def __init__(self, jid: str, jtype: str, cmd: list, cwd: Path,
                 total: int = 0, tracks_path: str | None = None):
        self.id = jid
        self.type = jtype
        self.cmd = cmd
        self.cwd = cwd
        self.total = total
        self.tracks_path = tracks_path
        self.status = "queued"
        self.exit_code: int | None = None
        self.started = time.time()
        self.started_h = _now_h()
        self.ended: float | None = None
        self.summary = ""
        self.log: deque[str] = deque(maxlen=LOG_CAP)
        self.done = 0
        self.status_counts: dict = {}
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

    def submit(self, jtype: str, cmd: list, total: int = 0,
               tracks_path: str | None = None) -> dict:
        jid = uuid.uuid4().hex[:10]
        job = Job(jid, jtype, cmd, REPO, total=total, tracks_path=tracks_path)
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
            job.status = "running"
            try:
                self._run(job)
                job.status = "done" if job.exit_code == 0 else "error"
                job.summary = f"exit={job.exit_code}"
                if job.status_counts:
                    job.summary += " · " + " ".join(
                        f"{k}:{v}" for k, v in sorted(job.status_counts.items()))
                if job.exit_code != 0:
                    job.summary += "（看日志末尾找原因）"
            except Exception as e:  # noqa: BLE001
                job.status = "error"
                job.summary = f"异常: {str(e)[:160]}"
                job.log.append(f"[runner] 异常: {e}")
            finally:
                job.ended = time.time()
                job._stop_tail.set()

    def _run(self, job: Job) -> None:
        job.log.append(f"[runner] {' '.join(job.cmd)}")
        t = threading.Thread(target=_tail_results, args=(job,), daemon=True)
        t.start()
        proc = subprocess.Popen(
            job.cmd, cwd=str(job.cwd),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert proc.stdout is not None
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line:
                job.log.append(line)
        proc.wait()
        job.exit_code = proc.returncode
        job._stop_tail.set()


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


def _read_tracks(path: str, include_existing: bool, only: list | None) -> tuple[list, int]:
    """读 prepare 产出的 tracks.json，返回 (目标曲目列表, 目标数)。"""
    p = Path(path)
    if not p.is_absolute():
        p = REPO / p
    p = p.resolve()
    if not (str(p).startswith(str(REPO)) and p.name == "tracks.json" and p.exists()):
        raise ValueError("tracks.json 路径不合法")
    d = json.loads(p.read_text(encoding="utf-8"))
    records = d if isinstance(d, list) else d.get("records") or []
    targets = [r for r in records if isinstance(r, dict)]
    if only:
        wanted = {str(x) for x in only}
        targets = [r for r in targets
                   if str(r.get("uri") or "").split(":")[-1] in wanted]
    if not include_existing:
        targets = [r for r in targets if not r.get("existing")]
    return targets, len(targets)


class Handler(BaseHTTPRequestHandler):
    runner: Runner

    def log_message(self, fmt, *args):  # 静默访问日志
        pass

    def _json(self, obj, code: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):  # noqa: N802
        if self.path == "/" or self.path.startswith("/index"):
            body = PAGE_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/state":
            with self.runner.lock:
                jobs = [self.runner.jobs[i].snapshot()
                        for i in reversed(self.runner.order)]
            self._json({"library": _library_counts(self.runner.cfg.paths.music),
                        "jobs": jobs})
        elif self.path.startswith("/api/job/"):
            jid = self.path.rsplit("/", 1)[-1]
            job = self.runner.jobs.get(jid)
            if job is None:
                self._json({"error": "no such job"}, 404)
                return
            self._json(job.snapshot(with_log=True))
        elif self.path.startswith("/api/tracks"):
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            path = (qs.get("path") or [""])[0]
            try:
                _, records_all = None, None
                p = Path(path)
                if not p.is_absolute():
                    p = REPO / p
                p = p.resolve()
                if not (str(p).startswith(str(REPO)) and p.name == "tracks.json" and p.exists()):
                    raise ValueError("路径不合法")
                d = json.loads(p.read_text(encoding="utf-8"))
                records = d if isinstance(d, list) else d.get("records") or []
                slim = [{"position": r.get("position"), "name": r.get("name"),
                         "artists": r.get("artists"), "album": r.get("album"),
                         "duration_ms": r.get("duration_ms"),
                         "existing": bool(r.get("existing")), "uri": r.get("uri")}
                        for r in records if isinstance(r, dict)]
                self._json({"records": slim})
            except Exception as e:
                self._json({"error": str(e)}, 400)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):  # noqa: N802
        body = self._body()
        r = self.runner
        try:
            if self.path == "/api/prepare":
                out = REPO / "tasks" / "gui" / time.strftime("%Y%m%d_%H%M%S") / "tracks.json"
                if body.get("uri"):
                    cmd = [PY, "-X", "utf8", "cli.py", "prepare",
                           "--uri", str(body["uri"]), "--out", str(out)]
                elif body.get("list_text"):
                    out.parent.mkdir(parents=True, exist_ok=True)
                    lst = out.parent / "list.txt"
                    lst.write_text(str(body["list_text"]), encoding="utf-8")
                    cmd = [PY, "-X", "utf8", "cli.py", "prepare",
                           "--list", str(lst), "--out", str(out)]
                else:
                    raise ValueError("需要 uri 或 list_text")
                job = r.submit("prepare", cmd, tracks_path=str(out))
                self._json(job)
            elif self.path == "/api/download":
                tracks = str(body.get("tracks") or "")
                targets, total = _read_tracks(
                    tracks, bool(body.get("include_existing")),
                    body.get("only") or None)
                if total == 0:
                    raise ValueError("没有可下载的目标（全部已存在或选择为空）")
                cmd = [PY, "-X", "utf8", "cli.py", "download",
                       "--tracks", tracks, "--source", str(body.get("source") or "auto")]
                if body.get("only"):
                    cmd += ["--only", ",".join(str(x) for x in body["only"])]
                if body.get("include_existing"):
                    cmd.append("--include-existing")
                job = r.submit("download", cmd, total=total, tracks_path=tracks)
                self._json(job)
            elif self.path == "/api/upgrade":
                ext = str(body.get("ext") or "mp3")
                if ext not in ("mp3", "ogg", "all"):
                    raise ValueError("ext 仅支持 mp3/ogg/all")
                cmd = [PY, "-X", "utf8", "cli.py", "upgrade", "--ext", ext]
                if body.get("full_retry"):
                    cmd.append("--full-retry")
                job = r.submit("upgrade", cmd)
                self._json(job)
            elif self.path == "/api/audit":
                job = r.submit("audit", [PY, "-X", "utf8", "cli.py", "audit"])
                self._json(job)
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
    url = f"http://127.0.0.1:{args.port}"

    class H(Handler):
        pass

    H.runner = Runner(cfg)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), H)
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
