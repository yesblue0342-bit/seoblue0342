"""
seoblue0342 — 웹 진입점 (OCI 서버 배포용)
- seo.이후.com 에서 Caddy reverse_proxy 뒤에 띄우는 가벼운 Flask 앱
- CLI 도구(main.py)는 그대로 두고, 웹에서 분석을 실행/표시만 함

실행(로컬 테스트):
    pip install -r requirements.txt
    python webapp.py            # 개발 서버 (http://127.0.0.1:8842)
운영(OCI):
    gunicorn -w 2 -b 127.0.0.1:8842 webapp:app --timeout 120
"""

import os
import json
import re
import secrets
import threading
from datetime import datetime
from urllib.parse import quote

from flask import Flask, Response, redirect, send_file, jsonify, render_template, request, stream_with_context
from werkzeug.exceptions import HTTPException

from auth import app_access_required, init_auth
from config import SEARCH_KEYWORD
from conversation_parser import ConversationError, convert_share_url
from drive_service import DriveError, get_drive_client
from seo_analyzer import run_full_analysis
from rank_monitor import init_db, check_my_rank, save_rank_result
from report_generator import generate_html_report

# ── 경로 설정 ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("SEO_DATA_DIR", os.path.join(BASE_DIR, "data"))
os.makedirs(DATA_DIR, exist_ok=True)
REPORT_PATH = os.path.join(DATA_DIR, "report.html")
STATUS_PATH = os.path.join(DATA_DIR, "status.json")
DB_PATH = os.path.join(DATA_DIR, "rank_history.db")

app = Flask(__name__)
app.config.update(
    DATA_DIR=DATA_DIR,
    AUTH_DB_PATH=os.environ.get("SEO_AUTH_DB_PATH", os.path.join(DATA_DIR, "auth.db")),
    MAX_CONTENT_LENGTH=25 * 1024 * 1024,
)
app.secret_key = os.environ.get("SEO_SESSION_SECRET") or secrets.token_bytes(48)
if not os.environ.get("SEO_SESSION_SECRET"):
    app.logger.warning("SEO_SESSION_SECRET is unset; sessions will reset when the process restarts.")
init_auth(app)


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; connect-src 'self'; frame-src 'self'; base-uri 'self'; "
        "form-action 'self'; object-src 'none'",
    )
    return response


@app.errorhandler(HTTPException)
def handle_http_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": error.description}), error.code
    return error

# ── 분석 상태 (메모리 + 파일 영속) ───────────────────────────
STATUS = {"running": False, "started": None, "finished": None, "error": None}
_LOCK = threading.Lock()
_SCHED = None   # 스케줄러 참조 (다음 실행시각 조회용)


def _save_status():
    try:
        with open(STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(STATUS, f, ensure_ascii=False)
    except OSError:
        pass


def _load_status():
    if os.path.exists(STATUS_PATH):
        try:
            with open(STATUS_PATH, encoding="utf-8") as f:
                STATUS.update(json.load(f))
                STATUS["running"] = False  # 재시작 시 running 플래그 초기화
        except (OSError, json.JSONDecodeError):
            pass


def _background_run():
    """백그라운드 스레드에서 SEO 분석 실행 후 report.html 생성."""
    with _LOCK:
        if STATUS["running"]:
            return
        STATUS.update(running=True, error=None,
                      started=datetime.now().isoformat(timespec="seconds"))
        _save_status()

    try:
        analysis = run_full_analysis()

        # 순위 체크는 네이버 봇 차단 등으로 실패할 수 있으므로 분리 처리
        rank = None
        try:
            conn = init_db(DB_PATH)
            found, all_results, reliable = check_my_rank(SEARCH_KEYWORD)
            save_rank_result(conn, SEARCH_KEYWORD, found, len(all_results))
            conn.close()
            rank = (found, all_results, reliable)
        except Exception as e:  # noqa: BLE001
            print(f"[rank] 건너뜀: {e}")

        generate_html_report(analysis, rank, REPORT_PATH)
        STATUS["finished"] = datetime.now().isoformat(timespec="seconds")
    except Exception as e:  # noqa: BLE001
        STATUS["error"] = str(e)
        print(f"[analysis] 실패: {e}")
    finally:
        STATUS["running"] = False
        _save_status()


# ── 셸 페이지 (헤더 + iframe으로 리포트 표시) ────────────────
SHELL_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>이후 소설가 — 네이버 SEO 대시보드</title>
<script>
  (() => {{
    const saved = localStorage.getItem('seoblue-theme');
    document.documentElement.dataset.theme = saved === 'dark' ? 'dark' : 'light';
  }})();
</script>
<style>
  :root {{ color-scheme:light; --bg:#fff; --surface:#fff; --text:#111; --muted:#666; --line:#d8d8d8; --soft:#f5f5f5; }}
  :root[data-theme="dark"] {{ color-scheme:dark; --bg:#000; --surface:#000; --text:#fff; --muted:#aaa; --line:#444; --soft:#111; }}
  * {{ box-sizing: border-box; }}
  html, body {{ height:100%; }}
  body {{ margin:0; font-family:-apple-system,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif;
          background:var(--bg); color:var(--text); display:flex; flex-direction:column; min-height:100vh; min-height:100dvh; }}
  .bar {{ position:sticky; top:0; z-index:10; display:flex; align-items:center; gap:8px 14px; flex-wrap:wrap;
          background:var(--surface); color:var(--text); padding:12px 18px; border-bottom:1px solid var(--line); }}
  .bar h1 {{ font-size:16px; margin:0; flex:1 1 auto; min-width:0; line-height:1.3; font-weight:700; }}
  .bar h1 .sub {{ font-weight:500; opacity:.92; }}
  .bar .meta {{ font-size:12px; opacity:.92; line-height:1.35; }}
  .app-nav {{ display:flex; align-items:center; gap:6px; flex:0 0 auto; }}
  .app-nav a {{ color:var(--text); background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:7px 10px; font-size:12px; font-weight:700; text-decoration:none; white-space:nowrap; }}
  .app-nav a:hover {{ background:var(--soft); }}
  .btn {{ background:var(--surface); color:var(--text); border:1px solid var(--line); border-radius:8px; padding:8px 16px;
          font-weight:700; cursor:pointer; font-size:14px; white-space:nowrap; }}
  .btn:hover {{ background:var(--soft); }}
  .btn:disabled {{ opacity:.6; cursor:default; }}
  iframe {{ flex:1 1 auto; width:100%; min-height:0; border:none; background:var(--bg); }}
  .empty {{ max-width:560px; margin:64px auto; padding:0 20px; text-align:center; color:var(--muted); }}
  .empty h2 {{ color:var(--text); }}
  .error {{ color:var(--text); border-left:3px double var(--text); padding-left:10px; }}
  .spinner {{ display:inline-block; width:14px; height:14px; border:2px solid var(--line);
              border-top-color:var(--text); border-radius:50%; animation:spin .8s linear infinite; vertical-align:middle; }}
  :focus-visible {{ outline:2px solid var(--text); outline-offset:2px; }}
  @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
  /* ── 모바일: 제목이 한 글자씩 세로로 깨지던 문제 수정 ── */
  @media (max-width:600px) {{
    .bar {{ padding:10px 14px; gap:4px 10px; }}
    .bar h1 {{ flex:1 1 100%; font-size:15px; }}
    .bar h1 .sub {{ display:block; font-size:12px; opacity:.85; margin-top:1px; }}
    .bar .meta {{ order:2; flex:1 1 auto; font-size:11px; }}
    .app-nav {{ order:3; flex:1 1 100%; overflow:auto; }}
    .app-nav a {{ font-size:11px; padding:6px 9px; }}
    .btn {{ order:4; margin-left:auto; padding:7px 12px; font-size:13px; }}
  }}
</style>
</head>
<body>
  <div class="bar">
    <h1>이후 소설가 <span class="sub">— 네이버 SEO 대시보드</span></h1>
    <nav class="app-nav" aria-label="앱 메뉴">
      <a href="/g-drive">파일</a>
      <a href="/obsidian-download">Obsidian Download</a>
    </nav>
    <span class="meta" id="meta">{meta}</span>
    <button class="btn" type="button" data-theme-toggle aria-pressed="false">Dark mode</button>
    <button class="btn" id="run" onclick="runAnalysis()">다시 분석</button>
  </div>
  {content}
<script>
  async function poll() {{
    try {{
      const r = await fetch('/status'); const s = await r.json();
      const btn = document.getElementById('run');
      const meta = document.getElementById('meta');
      if (s.running) {{
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> 분석 중...';
        meta.textContent = '분석 진행 중 (최대 1~2분 소요)';
        setTimeout(poll, 3000);
      }} else {{
        if (btn.disabled) location.reload();   // 방금 끝났으면 새 리포트 로드
      }}
    }} catch (e) {{ setTimeout(poll, 5000); }}
  }}
  async function runAnalysis() {{
    const btn = document.getElementById('run');
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> 시작 중...';
    await fetch('/refresh', {{ method: 'POST' }});
    setTimeout(poll, 1500);
  }}
  poll();
</script>
<script src="/static/theme.js" defer></script>
</body>
</html>"""


@app.route("/")
def index():
    has_report = os.path.exists(REPORT_PATH)
    if STATUS.get("finished"):
        meta = f"마지막 갱신: {STATUS['finished'].replace('T', ' ')}"
    elif STATUS.get("running"):
        meta = "분석 진행 중..."
    else:
        meta = "아직 분석 전"
    nxt = _next_run()
    if nxt:
        meta += f" · 다음 자동 분석: {nxt}"

    if has_report:
        content = '<iframe src="/report" title="SEO 리포트"></iframe>'
    else:
        err = f'<p class="error">직전 오류: {STATUS["error"]}</p>' if STATUS.get("error") else ""
        content = (
            '<div class="empty"><h2>아직 분석 결과가 없습니다</h2>'
            '<p>오른쪽 위 <b>다시 분석</b> 버튼을 누르면 네이버 순위와 '
            '홈페이지·위키백과·나무위키·교보문고·구글·유튜브 SEO를 분석합니다.</p>'
            f'{err}</div>'
        )
    return Response(SHELL_HTML.format(meta=meta, content=content), mimetype="text/html")


@app.route("/report")
def report():
    if os.path.exists(REPORT_PATH):
        return send_file(REPORT_PATH)
    return Response("<p>리포트가 아직 생성되지 않았습니다.</p>", mimetype="text/html")


@app.route("/refresh", methods=["POST", "GET"])
def refresh():
    if not STATUS["running"]:
        threading.Thread(target=_background_run, daemon=True).start()
    if request_is_get():
        return redirect("/")
    return jsonify({"started": True})


@app.route("/status")
def status():
    data = dict(STATUS)
    data["next_run"] = _next_run()
    return jsonify(data)


@app.route("/healthz")
def healthz():
    drive = get_drive_client()
    return jsonify({
        "ok": True,
        "drive_configured": drive.configured,
        "drive_writes_enabled": drive.writes_enabled,
        # Required accounts are seeded with the built-in admin hash when no override is set.
        "initial_seed_configured": True,
    })


@app.route("/g-drive")
@app_access_required
def g_drive_page():
    return render_template("g_drive.html")


def _drive_id(value, field="file_id", allow_root=False):
    value = str(value or "").strip()
    if allow_root and (not value or value == "root"):
        return "root"
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value):
        raise DriveError(f"{field} 형식이 올바르지 않습니다.", 400)
    return value


def _drive_name(value):
    value = str(value or "").strip()
    if not value or len(value) > 255 or any(ord(ch) < 32 for ch in value) or "/" in value or "\\" in value:
        raise DriveError("파일 또는 폴더 이름이 올바르지 않습니다.", 400)
    return value


def _drive_error(exc):
    return jsonify({"ok": False, "error": str(exc)}), exc.status


@app.get("/api/g-drive/capabilities")
@app_access_required
def drive_capabilities():
    return jsonify({"ok": True, **get_drive_client().capabilities()})


@app.get("/api/g-drive/files")
@app_access_required
def drive_files():
    try:
        folder_id = _drive_id(request.args.get("folder_id"), "folder_id", allow_root=True)
        search = request.args.get("q", "").strip()[:100]
        page_token = request.args.get("page_token", "").strip()
        if page_token and not re.fullmatch(r"[A-Za-z0-9_.=-]{1,1000}", page_token):
            raise DriveError("page_token 형식이 올바르지 않습니다.", 400)
        return jsonify({"ok": True, **get_drive_client().list_files(folder_id, search, page_token)})
    except DriveError as exc:
        return _drive_error(exc)


@app.get("/api/g-drive/download/<file_id>")
@app_access_required
def drive_download(file_id):
    try:
        result = get_drive_client().download(_drive_id(file_id))

        def generate():
            try:
                yield from result.response.iter_content(chunk_size=64 * 1024)
            finally:
                result.response.close()

        response = Response(stream_with_context(generate()), content_type=result.content_type)
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(result.filename)}"
        response.headers["Cache-Control"] = "private, no-store"
        return response
    except DriveError as exc:
        return _drive_error(exc)


@app.post("/api/g-drive/folder")
@app_access_required
def drive_create_folder():
    try:
        body = request.get_json(silent=True) or {}
        item = get_drive_client().create_folder(
            _drive_id(body.get("parent_id"), "parent_id", allow_root=True),
            _drive_name(body.get("name")),
        )
        return jsonify({"ok": True, "file": item}), 201
    except DriveError as exc:
        return _drive_error(exc)


@app.post("/api/g-drive/upload")
@app_access_required
def drive_upload():
    try:
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            raise DriveError("업로드할 파일을 선택해 주세요.", 400)
        name = _drive_name(uploaded.filename)
        item = get_drive_client().upload(
            _drive_id(request.form.get("parent_id"), "parent_id", allow_root=True),
            name,
            uploaded.mimetype or "application/octet-stream",
            uploaded.stream,
        )
        return jsonify({"ok": True, "file": item}), 201
    except DriveError as exc:
        return _drive_error(exc)


@app.post("/api/g-drive/rename")
@app_access_required
def drive_rename():
    try:
        body = request.get_json(silent=True) or {}
        item = get_drive_client().rename(_drive_id(body.get("file_id")), _drive_name(body.get("name")))
        return jsonify({"ok": True, "file": item})
    except DriveError as exc:
        return _drive_error(exc)


@app.post("/api/g-drive/move")
@app_access_required
def drive_move():
    try:
        body = request.get_json(silent=True) or {}
        item = get_drive_client().move(
            _drive_id(body.get("file_id")),
            _drive_id(body.get("target_parent_id"), "target_parent_id"),
        )
        return jsonify({"ok": True, "file": item})
    except DriveError as exc:
        return _drive_error(exc)


@app.post("/api/g-drive/delete")
@app_access_required
def drive_delete():
    try:
        body = request.get_json(silent=True) or {}
        if body.get("confirm") is not True:
            raise DriveError("삭제 확인이 필요합니다.", 400)
        item = get_drive_client().trash(_drive_id(body.get("file_id")))
        return jsonify({"ok": True, "file": item})
    except DriveError as exc:
        return _drive_error(exc)


@app.route("/obsidian-download")
@app_access_required
def obsidian_download_page():
    return render_template("obsidian_download.html")


@app.post("/api/obsidian/convert")
@app_access_required
def obsidian_convert():
    try:
        body = request.get_json(silent=True) or {}
        conversation, markdown, filename = convert_share_url(body.get("url", ""))
        return jsonify({
            "ok": True,
            "title": conversation.title,
            "provider": conversation.provider,
            "messageCount": len(conversation.messages),
            "filename": filename,
            "markdown": markdown,
        })
    except ConversationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), exc.status


def request_is_get():
    from flask import request
    return request.method == "GET"


_load_status()


# ── 자동 스케줄러 (매일 1회 자동 분석) ───────────────────────
# 환경변수로 제어:
#   SEO_SCHEDULE_HOUR (기본 4 = 새벽 4시), SEO_SCHEDULE_TZ (기본 Asia/Seoul)
#   SEO_SCHEDULE_ENABLED=0 으로 끌 수 있음
def _start_scheduler():
    global _SCHED
    if os.environ.get("SEO_SCHEDULE_ENABLED", "1") != "1":
        print("[scheduler] 비활성화됨 (SEO_SCHEDULE_ENABLED=0)")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        hour = int(os.environ.get("SEO_SCHEDULE_HOUR", "4"))
        tz = os.environ.get("SEO_SCHEDULE_TZ", "Asia/Seoul")
        sched = BackgroundScheduler(timezone=tz, daemon=True)
        # 매일 지정 시각 1회 (네이버 차단 위험을 줄이기 위해 하루 1회로 보수적 운영)
        sched.add_job(_background_run, CronTrigger(hour=hour, minute=0),
                      id="daily_seo", replace_existing=True, max_instances=1)
        sched.start()
        _SCHED = sched
        print(f"[scheduler] 매일 {hour}시({tz}) 자동 분석 예약됨")
    except Exception as e:  # noqa: BLE001  스케줄러 실패가 앱 자체를 막으면 안 됨
        print(f"[scheduler] 시작 실패(무시하고 계속): {e}")


def _next_run():
    """다음 자동 분석 예정 시각 (문자열) 또는 None."""
    try:
        if _SCHED:
            job = _SCHED.get_job("daily_seo")
            if job and job.next_run_time:
                return job.next_run_time.strftime("%Y-%m-%d %H:%M")
    except Exception:  # noqa: BLE001
        pass
    return None


# gunicorn 워커 1개 기준으로 한 번만 시작 (Dockerfile에서 -w 1)
_start_scheduler()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8842)))
