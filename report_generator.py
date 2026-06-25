"""
리포트 생성기
- SEO 분석 결과 + 순위 결과를 HTML / 마크다운 리포트 파일로 출력
- main.py 에서 generate_html_report / generate_markdown_report 로 호출됨

(원본 프로젝트에서 누락되어 있던 모듈 — main.py 의 import 대상이라 없으면 실행이 즉시 중단됨)
"""

from datetime import datetime
from html import escape


# ──────────────────────────────────────────────────────────────
#  공통 헬퍼
# ──────────────────────────────────────────────────────────────
def _score_color(score: int) -> str:
    if score >= 70:
        return "#16a34a"   # green
    if score >= 40:
        return "#d97706"   # amber
    return "#dc2626"       # red


def _score_emoji(score: int) -> str:
    if score >= 70:
        return "🟢"
    if score >= 40:
        return "🟡"
    return "🔴"


def _rank_badge(rank):
    if not rank:
        return "미발견"
    if rank <= 3:
        return f"{rank}위 (상위 노출)"
    if rank <= 10:
        return f"{rank}위 (1페이지)"
    return f"{rank}위"


# ──────────────────────────────────────────────────────────────
#  HTML 리포트
# ──────────────────────────────────────────────────────────────
_HTML_STYLE = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Apple SD Gothic Neo", "Malgun Gothic",
               "Noto Sans KR", sans-serif;
  margin: 0; padding: 0; background: #f6f7f9; color: #1f2937; line-height: 1.6;
}
.wrap { max-width: 920px; margin: 0 auto; padding: 32px 20px 64px; }
header.hero {
  background: linear-gradient(135deg, #15803d, #16a34a);
  color: #fff; border-radius: 16px; padding: 28px 32px; margin-bottom: 28px;
}
header.hero h1 { margin: 0 0 6px; font-size: 24px; }
header.hero p { margin: 0; opacity: .9; font-size: 14px; }
.card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 14px;
  padding: 22px 24px; margin-bottom: 22px; box-shadow: 0 1px 2px rgba(0,0,0,.04);
}
.card h2 { margin: 0 0 14px; font-size: 18px; }
.score-pill {
  display: inline-flex; align-items: center; gap: 8px;
  font-weight: 700; font-size: 15px; padding: 6px 14px; border-radius: 999px;
  color: #fff;
}
.meta-line { color: #6b7280; font-size: 13px; margin: 8px 0 16px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 9px 10px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }
th { color: #6b7280; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .03em; }
.ok { color: #16a34a; font-weight: 700; }
.no { color: #dc2626; font-weight: 700; }
.val { color: #374151; word-break: break-word; }
.rec { background: #fef2f2; border-left: 3px solid #dc2626; padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 8px 0; font-size: 14px; }
.rank-grid { display: grid; grid-template-columns: 1fr auto auto; gap: 0; }
footer { text-align: center; color: #9ca3af; font-size: 12px; margin-top: 32px; }
code { background: #f3f4f6; padding: 1px 6px; border-radius: 5px; font-size: 13px; }
"""


def _html_rank_section(rank_results) -> str:
    if not rank_results:
        return ""
    found = rank_results[0]
    all_results = rank_results[1]
    reliable = rank_results[2] if len(rank_results) > 2 else True

    warn = ""
    if not reliable:
        warn = (
            "<div style='background:#fef3c7;border-left:4px solid #d97706;"
            "padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:12px;font-size:13px'>"
            "⚠️ 네이버가 봇 차단/구조 변경으로 정식 검색 결과 파싱에 실패했습니다. "
            "아래 순위 수치는 신뢰할 수 없어 비워둡니다. "
            "'이후' 단독보다 <b>'이후 소설가'</b>로 직접 검색해 확인하시는 것을 권장합니다."
            "</div>"
        )

    rows = []
    for name, info in found.items():
        rank = info.get("rank")
        url = info.get("url") or "-"
        cls = "ok" if rank and rank <= 10 else "no"
        rank_label = _rank_badge(rank) if reliable else (info.get("note") or "측정 불가")
        rows.append(
            f"<tr><td>{escape(str(name))}</td>"
            f"<td class='{cls}'>{escape(rank_label)}</td>"
            f"<td class='val'>{escape(url[:70])}</td></tr>"
        )
    count_note = f"총 {len(all_results)}개 결과 수집" if reliable else "파싱 실패"
    return f"""
    <div class="card">
      <h2>📊 네이버 검색 순위 ('이후' 검색 · {count_note})</h2>
      {warn}
      <table>
        <thead><tr><th>페이지</th><th>순위</th><th>URL</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>"""


def _html_seo_section(r: dict) -> str:
    score = r.get("score", 0)
    meta = r.get("meta", {})
    color = _score_color(score)
    emoji = _score_emoji(score)

    check_rows = []
    for c in r.get("checks", []):
        if c.get("passed"):
            val = escape(c.get("value") or "통과")
            check_rows.append(
                f"<tr><td class='ok'>✅</td><td>{escape(c['label'])}</td>"
                f"<td class='val'>{val[:90]}</td></tr>"
            )
        else:
            detail = escape(c.get("detail") or "")
            check_rows.append(
                f"<tr><td class='no'>❌</td><td><b>{escape(c['label'])}</b></td>"
                f"<td class='val'>{detail[:120]}</td></tr>"
            )

    recs = "".join(
        f"<div class='rec'>{escape(rec)}</div>" for rec in r.get("recommendations", [])
    ) or "<p class='ok'>🎉 모든 SEO 항목 통과!</p>"

    meta_line = (
        f"HTTP {meta.get('status', '?')} · "
        f"응답 {meta.get('response_time', '?')}ms · "
        f"{meta.get('content_length', 0) // 1024}KB"
    )

    return f"""
    <div class="card">
      <h2>{escape(r.get('label', ''))}</h2>
      <span class="score-pill" style="background:{color}">{emoji} {score}점
        &nbsp;<span style="opacity:.85;font-weight:500">
        ({r.get('passed', 0)}/{r.get('total', 0)} 통과)</span></span>
      <div class="meta-line">{escape(r.get('url', ''))} · {meta_line}</div>
      <table>
        <thead><tr><th>상태</th><th>SEO 항목</th><th>현재값 / 권고</th></tr></thead>
        <tbody>{''.join(check_rows)}</tbody>
      </table>
      <h3 style="font-size:14px;margin:18px 0 6px;color:#374151">개선 권고
        ({len(r.get('recommendations', []))}건)</h3>
      {recs}
    </div>"""


def generate_html_report(analysis_results, rank_results=None,
                         output_path="seo_report.html") -> str:
    """SEO 분석 결과를 HTML 리포트 파일로 저장하고 경로를 반환."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = [_html_rank_section(rank_results)]
    body += [_html_seo_section(r) for r in (analysis_results or [])]

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>이후 소설가 — 네이버 SEO 분석 리포트</title>
<style>{_HTML_STYLE}</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <h1>📈 이후 소설가 — 네이버 SEO 분석 리포트</h1>
    <p>네이버 검색 '이후' 키워드 상위 노출 분석 · 생성: {ts}</p>
  </header>
  {''.join(body)}
  <footer>seoblue0342 · 이후 소설가 네이버 SEO 최적화 도구</footer>
</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


# ──────────────────────────────────────────────────────────────
#  마크다운 리포트
# ──────────────────────────────────────────────────────────────
def generate_markdown_report(analysis_results, rank_results=None,
                             output_path="seo_report.md") -> str:
    """SEO 분석 결과를 마크다운 리포트 파일로 저장하고 경로를 반환."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 📈 이후 소설가 — 네이버 SEO 분석 리포트",
        "",
        f"> 생성: {ts}",
        "",
    ]

    # 순위 섹션
    if rank_results:
        found = rank_results[0]
        all_results = rank_results[1]
        reliable = rank_results[2] if len(rank_results) > 2 else True
        lines += [
            f"## 📊 네이버 검색 순위 (총 {len(all_results)}개 결과)",
            "",
        ]
        if not reliable:
            lines += [
                "> ⚠️ 네이버 파싱 실패(봇 차단/구조 변경) — 순위 수치 신뢰 불가. "
                "'이후 소설가'로 직접 검색 확인 권장.",
                "",
            ]
        lines += [
            "| 페이지 | 순위 | URL |",
            "|--------|------|-----|",
        ]
        for name, info in found.items():
            rank = info.get("rank")
            url = (info.get("url") or "-")[:70]
            label = _rank_badge(rank) if reliable else (info.get("note") or "측정 불가")
            lines.append(f"| {name} | {label} | {url} |")
        lines.append("")

    # SEO 섹션
    for r in (analysis_results or []):
        score = r.get("score", 0)
        lines += [
            f"## {_score_emoji(score)} {r.get('label', '')} — {score}점 "
            f"({r.get('passed', 0)}/{r.get('total', 0)} 통과)",
            "",
            f"- URL: {r.get('url', '')}",
            "",
            "| 상태 | SEO 항목 | 현재값 / 권고 |",
            "|------|----------|----------------|",
        ]
        for c in r.get("checks", []):
            mark = "✅" if c.get("passed") else "❌"
            detail = (c.get("value") if c.get("passed") else c.get("detail")) or ""
            detail = detail.replace("|", "\\|").replace("\n", " ")[:110]
            lines.append(f"| {mark} | {c.get('label', '')} | {detail} |")
        lines.append("")

        recs = r.get("recommendations", [])
        if recs:
            lines.append(f"### ⚠️ 개선 권고 ({len(recs)}건)")
            lines.append("")
            for i, rec in enumerate(recs, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        else:
            lines += ["### 🎉 모든 SEO 항목 통과", ""]

    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


if __name__ == "__main__":
    # 단독 실행 시 목 데이터로 샘플 리포트 생성
    demo = [{
        "label": "데모 페이지",
        "url": "https://example.com",
        "meta": {"status": 200, "response_time": 120, "content_length": 20480},
        "checks": [
            {"label": "Title", "passed": True, "value": "데모 제목", "detail": ""},
            {"label": "JSON-LD", "passed": False, "value": "", "detail": "구조화 데이터 추가 필요"},
        ],
        "score": 50, "passed": 1, "total": 2,
        "recommendations": ["[JSON-LD] 구조화 데이터 추가 필요"],
    }]
    print(generate_html_report(demo, None, "demo_report.html"))
    print(generate_markdown_report(demo, None, "demo_report.md"))
