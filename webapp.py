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
import threading
from datetime import datetime

from flask import Flask, Response, redirect, send_file, jsonify

from config import SEARCH_KEYWORD
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
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:-apple-system,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif; background:#f6f7f9; }}
  .bar {{ position:sticky; top:0; z-index:10; display:flex; align-items:center; gap:14px;
          background:#16a34a; color:#fff; padding:12px 20px; box-shadow:0 1px 4px rgba(0,0,0,.15); }}
  .bar h1 {{ font-size:16px; margin:0; flex:1; }}
  .bar .meta {{ font-size:12px; opacity:.9; }}
  .btn {{ background:#fff; color:#15803d; border:none; border-radius:8px; padding:8px 16px;
          font-weight:700; cursor:pointer; font-size:14px; }}
  .btn:disabled {{ opacity:.6; cursor:default; }}
  iframe {{ width:100%; height:calc(100vh - 50px); border:none; background:#fff; }}
  .empty {{ max-width:560px; margin:80px auto; text-align:center; color:#374151; }}
  .empty h2 {{ color:#16a34a; }}
  .spinner {{ display:inline-block; width:14px; height:14px; border:2px solid rgba(255,255,255,.4);
              border-top-color:#fff; border-radius:50%; animation:spin .8s linear infinite; vertical-align:middle; }}
  @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
</style>
</head>
<body>
  <div class="bar">
    <h1>📈 이후 소설가 — 네이버 SEO 대시보드</h1>
    <span class="meta" id="meta">{meta}</span>
    <button class="btn" id="run" onclick="runAnalysis()">🔄 다시 분석</button>
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
        err = f'<p style="color:#dc2626">직전 오류: {STATUS["error"]}</p>' if STATUS.get("error") else ""
        content = (
            '<div class="empty"><h2>아직 분석 결과가 없습니다</h2>'
            '<p>오른쪽 위 <b>🔄 다시 분석</b> 버튼을 누르면 네이버 순위와 '
            '홈페이지·위키백과 SEO를 분석합니다.</p>'
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
    return jsonify({"ok": True})


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
