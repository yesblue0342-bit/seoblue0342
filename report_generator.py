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
.menu { display:flex; flex-wrap:wrap; gap:8px; margin:0 0 24px; }
.menu a { display:inline-flex; align-items:center; gap:6px; text-decoration:none;
  background:#fff; border:1px solid #e5e7eb; border-radius:999px; padding:7px 14px;
  font-size:13px; font-weight:600; color:#15803d; box-shadow:0 1px 2px rgba(0,0,0,.04); }
.menu a:hover { background:#f0fdf4; border-color:#16a34a; }
.menu a .dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
.card { scroll-margin-top: 16px; }
@media (max-width: 600px) {
  .wrap { padding: 18px 14px 48px; }
  header.hero { padding: 20px 18px; border-radius: 12px; margin-bottom: 18px; }
  header.hero h1 { font-size: 19px; }
  .card { padding: 18px 16px; border-radius: 12px; }
  .card h2 { font-size: 16px; }
  th, td { padding: 8px 6px; }
  th:first-child, td:first-child { white-space: nowrap; }
  .menu { gap: 6px; }
  .menu a { padding: 6px 11px; font-size: 12px; }
  table { font-size: 13px; }
}
"""


def _html_rank_section(rank_results) -> str:
    if not rank_results:
        return ""
    found = rank_results[0]
    all_results = rank_results[1]
    reliable = rank_results[2] if len(rank_results) > 2 else True

    # 네이버 직접검색 링크 (스크래핑이 막혀도 사용자가 한 번에 실제 순위 확인 가능)
    from urllib.parse import quote
    link_ihu = f"https://search.naver.com/search.naver?query={quote('이후')}"
    link_novel = f"https://search.naver.com/search.naver?query={quote('이후 소설가')}"
    direct_links = (
        f"<div style='margin:10px 0;font-size:13px'>🔎 네이버에서 직접 확인: "
        f"<a href='{link_novel}' target='_blank' style='color:#16a34a;font-weight:700'>'이후 소설가' 검색</a> · "
        f"<a href='{link_ihu}' target='_blank' style='color:#6b7280'>'이후' 검색</a></div>"
    )

    # 네이버 오픈API는 통합검색 화면 순위와 순서가 달라 '몇 위'를 표시하면 거짓이 되므로
    # 노출 O/X 만 보여준다는 안내 (구글 카드와 동일한 노출 여부 모델)
    info_line = (
        "<div style='margin:2px 0 10px;font-size:12px;color:#6b7280'>"
        "ℹ️ 네이버 공식 오픈API 기준 <b>노출 여부</b>입니다. 오픈API 결과 순서는 통합검색 화면의 "
        "순위와 일치하지 않아 '몇 위'는 표시하지 않습니다.</div>"
    )

    warn = ""
    if not reliable:
        note = ""
        for _n, _i in found.items():
            note = _i.get("note") or note
        warn = (
            "<div style='background:#fef3c7;border-left:4px solid #d97706;"
            "padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:12px;font-size:13px'>"
            "⚠️ 네이버 오픈API로 노출 여부를 측정하지 못했습니다(측정 불가). "
            f"{escape(note)} 그동안은 아래 <b>'이후 소설가' 직접 검색</b>으로 확인하세요."
            "</div>"
        )

    rows = []
    for name, info in found.items():
        exposed = info.get("exposed")
        url = info.get("url") or "-"
        if not reliable or exposed is None:
            cls, label = "no", "측정 불가"
        elif exposed:
            cls, label = "ok", "✅ 노출됨"
        else:
            cls, label = "no", "❌ 미노출"
        rows.append(
            f"<tr><td>{escape(str(name))}</td>"
            f"<td class='{cls}'>{escape(label)}</td>"
            f"<td class='val'>{escape(url[:70])}</td></tr>"
        )
    count_note = f"총 {len(all_results)}개 결과 확인" if reliable else "측정 불가"
    return f"""
    <div class="card" id="rank-section">
      <h2>📊 네이버 노출 여부 ('소설가 이후' 검색 · {count_note})</h2>
      {info_line}
      {warn}
      {direct_links}
      <table>
        <thead><tr><th>페이지</th><th>노출</th><th>발견 URL</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>"""


def _menu_anchor(idx: int) -> str:
    """카드 앵커 id (상단 메뉴 점프용)."""
    return f"src-{idx}"


def _html_menu(analysis_results, has_rank: bool) -> str:
    """상단 정보 소스 메뉴 (각 카드로 점프하는 칩)."""
    if not analysis_results:
        return ""
    chips = []
    if has_rank:
        chips.append(
            "<a href='#rank-section'><span class='dot' style='background:#16a34a'></span>"
            "네이버 노출</a>"
        )
    for i, r in enumerate(analysis_results):
        score = r.get("score", 0)
        # 측정 불가(API 키 미설정·봇 차단 등)는 빨간 0점 대신 회색 점으로 표시
        color = _score_color(score) if r.get("measurable", True) else "#9ca3af"
        label = escape(r.get("label", f"소스 {i+1}"))
        chips.append(
            f"<a href='#{_menu_anchor(i)}'>"
            f"<span class='dot' style='background:{color}'></span>{label}</a>"
        )
    return f"<nav class='menu'>{''.join(chips)}</nav>"


# 페이지 유형 배지 (label, color, 설명) — seo_analyzer 의 kind 와 대응
_KIND_BADGES = {
    "owned": ("직접 관리", "#16a34a",
              "우리가 직접 수정할 수 있는 페이지 — 권고사항을 홈페이지에 바로 적용하세요."),
    "profile": ("외부 프로필", "#2563eb",
                "플랫폼이 관리하는 페이지 — HTML 직접 수정은 불가하며, "
                "프로필·본문 정보 보강 중심으로 평가합니다."),
    "serp": ("검색 노출", "#7c3aed",
             "검색 결과 페이지 자체의 SEO가 아니라, 검색결과에 '이후' 관련 "
             "페이지가 노출되는지를 평가합니다."),
}


def _kind_badge_html(kind: str) -> str:
    if kind not in _KIND_BADGES:
        return ""
    label, color, note = _KIND_BADGES[kind]
    return (
        f"<span style='display:inline-block;font-size:12px;font-weight:700;color:#fff;"
        f"background:{color};border-radius:999px;padding:3px 10px;margin-left:8px;"
        f"vertical-align:middle'>{label}</span>"
        f"<div style='font-size:13px;color:#6b7280;margin:8px 0 0'>ℹ️ {escape(note)}</div>"
    )


def _html_seo_section(r: dict, idx: int = 0) -> str:
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

    measurable = r.get("measurable", True)

    recs = "".join(
        f"<div class='rec'>{escape(rec)}</div>" for rec in r.get("recommendations", [])
    ) or "<p class='ok'>🎉 모든 SEO 항목 통과!</p>"

    meta_line = (
        f"HTTP {meta.get('status', '?')} · "
        f"응답 {meta.get('response_time', '?')}ms · "
        f"{meta.get('content_length', 0) // 1024}KB"
    )

    # 측정 불가: 빨간 0점 대신 회색 '측정 불가' 표시 (점수 왜곡 방지)
    if measurable:
        pill = (f'<span class="score-pill" style="background:{color}">{emoji} {score}점'
                f'&nbsp;<span style="opacity:.85;font-weight:500">'
                f'({r.get("passed", 0)}/{r.get("total", 0)} 통과)</span></span>')
    else:
        pill = '<span class="score-pill" style="background:#9ca3af">⚪ 측정 불가</span>'

    checks_table = f"""
      <table>
        <thead><tr><th>상태</th><th>SEO 항목</th><th>현재값 / 권고</th></tr></thead>
        <tbody>{''.join(check_rows)}</tbody>
      </table>""" if check_rows else ""

    recs_title = "개선 권고" if measurable else "안내"

    return f"""
    <div class="card" id="{_menu_anchor(idx)}">
      <h2>{escape(r.get('label', ''))}</h2>
      {pill}{_kind_badge_html(r.get('kind', ''))}
      <div class="meta-line">{escape(r.get('url', ''))} · {meta_line}</div>
      {checks_table}
      <h3 style="font-size:14px;margin:18px 0 6px;color:#374151">{recs_title}
        ({len(r.get('recommendations', []))}건)</h3>
      {recs}
    </div>"""


def generate_html_report(analysis_results, rank_results=None,
                         output_path="seo_report.html") -> str:
    """SEO 분석 결과를 HTML 리포트 파일로 저장하고 경로를 반환."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = analysis_results or []
    menu = _html_menu(results, has_rank=bool(rank_results))
    body = [menu, _html_rank_section(rank_results)]
    body += [_html_seo_section(r, i) for i, r in enumerate(results)]

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

    # 네이버 노출 여부 섹션 (순위 아님 — 오픈API 순서 ≠ 통합검색 순위)
    if rank_results:
        found = rank_results[0]
        all_results = rank_results[1]
        reliable = rank_results[2] if len(rank_results) > 2 else True
        lines += [
            f"## 📊 네이버 노출 여부 ('소설가 이후' 검색 · {len(all_results)}개 결과 확인)",
            "",
            "> ℹ️ 네이버 공식 오픈API 기준 노출 여부입니다. 오픈API 결과 순서는 통합검색 "
            "화면 순위와 일치하지 않아 '몇 위'는 표시하지 않습니다.",
            "",
        ]
        if not reliable:
            note = ""
            for _i in found.values():
                note = _i.get("note") or note
            lines += [
                f"> ⚠️ 네이버 오픈API 측정 불가. {note} '이후 소설가'로 직접 검색 확인 권장.",
                "",
            ]
        lines += [
            "| 페이지 | 노출 | 발견 URL |",
            "|--------|------|-----|",
        ]
        for name, info in found.items():
            exposed = info.get("exposed")
            url = (info.get("url") or "-")[:70]
            if not reliable or exposed is None:
                label = "측정 불가"
            else:
                label = "✅ 노출됨" if exposed else "❌ 미노출"
            lines.append(f"| {name} | {label} | {url} |")
        lines.append("")

    # SEO 섹션
    for r in (analysis_results or []):
        score = r.get("score", 0)
        if r.get("measurable", True):
            heading = (f"## {_score_emoji(score)} {r.get('label', '')} — {score}점 "
                       f"({r.get('passed', 0)}/{r.get('total', 0)} 통과)")
        else:
            heading = f"## ⚪ {r.get('label', '')} — 측정 불가"
        lines += [
            heading,
            "",
            f"- URL: {r.get('url', '')}",
        ]
        kind = r.get("kind", "")
        if kind in _KIND_BADGES:
            lines.append(f"- 유형: **{_KIND_BADGES[kind][0]}** — {_KIND_BADGES[kind][2]}")
        lines += [
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
