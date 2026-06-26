"""
SEO 분석기
- 홈페이지, 위키백과 페이지의 SEO 요소 분석
- 개선 권고사항 생성
"""

import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import (
    HEADERS, HOMEPAGE_URL, WIKIPEDIA_URL, CRAWL_DELAY, ANALYSIS_TARGETS,
)


# SEO 체크 항목 정의
SEO_CHECKS = {
    "title": "페이지 제목(Title) 태그",
    "meta_description": "메타 디스크립션",
    "meta_keywords": "메타 키워드",
    "h1": "H1 헤딩",
    "h2_h3": "H2/H3 헤딩 구조",
    "canonical": "Canonical URL",
    "og_title": "Open Graph 제목",
    "og_description": "Open Graph 설명",
    "og_image": "Open Graph 이미지",
    "structured_data": "구조화 데이터 (JSON-LD/Schema.org)",
    "lang": "HTML lang 속성",
    "mobile_viewport": "모바일 Viewport 메타태그",
    "internal_links": "내부 링크",
    "keyword_in_title": "제목에 핵심 키워드 포함",
    "keyword_in_desc": "디스크립션에 핵심 키워드 포함",
}

KEYWORD = "이후"
KEYWORD_ALT = ["소설가", "소설", "작가"]


def fetch_page(url: str) -> tuple[BeautifulSoup | None, dict]:
    """페이지 가져오기 + 기본 HTTP 정보"""
    meta = {"url": url, "status": None, "response_time": None, "content_length": 0}
    try:
        t0 = time.time()
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        meta["response_time"] = round((time.time() - t0) * 1000)
        meta["status"] = resp.status_code
        meta["content_length"] = len(resp.content)
        meta["final_url"] = resp.url
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        return soup, meta
    except requests.RequestException as e:
        meta["error"] = str(e)
        return None, meta


def analyze_seo(url: str, page_label: str) -> dict:
    """
    단일 페이지 SEO 분석
    Returns: {"label": str, "url": str, "checks": [...], "score": int, "recommendations": [...]}
    """
    soup, meta = fetch_page(url)
    checks = []
    recommendations = []

    def add_check(key: str, passed: bool, value: str = "", detail: str = ""):
        checks.append({
            "key": key,
            "label": SEO_CHECKS.get(key, key),
            "passed": passed,
            "value": value[:120] if value else "",
            "detail": detail,
        })
        if not passed:
            recommendations.append(f"[{SEO_CHECKS.get(key, key)}] {detail}")

    if soup is None:
        return {
            "label": page_label,
            "url": url,
            "meta": meta,
            "checks": [],
            "score": 0,
            "passed": 0,
            "total": 0,
            "recommendations": [f"페이지 접근 불가: {meta.get('error', '알 수 없는 오류')}"],
        }

    # ── 1. Title 태그 ──────────────────────────────────────────
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    has_title = bool(title_text)
    kw_in_title = KEYWORD in title_text
    add_check("title", has_title and len(title_text) >= 10,
              title_text,
              "Title 태그가 없거나 너무 짧습니다. 30~60자의 명확한 제목을 추가하세요.")
    add_check("keyword_in_title", kw_in_title,
              title_text,
              f"제목에 핵심 키워드 '{KEYWORD}'(소설가)를 포함하세요. 예: '이후 소설가 공식 홈페이지'")

    # ── 2. 메타 디스크립션 ──────────────────────────────────────
    meta_desc = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    desc_text = meta_desc.get("content", "") if meta_desc else ""
    kw_in_desc = KEYWORD in desc_text
    add_check("meta_description", bool(desc_text) and len(desc_text) >= 50,
              desc_text,
              "메타 디스크립션이 없거나 50자 미만입니다. 120~160자로 작성하세요.")
    add_check("keyword_in_desc", kw_in_desc,
              desc_text,
              f"메타 디스크립션에 '이후', '소설가' 등 핵심 키워드를 자연스럽게 포함하세요.")

    # ── 3. 메타 키워드 ──────────────────────────────────────────
    meta_kw = soup.find("meta", attrs={"name": re.compile(r"keywords", re.I)})
    kw_text = meta_kw.get("content", "") if meta_kw else ""
    add_check("meta_keywords", bool(kw_text),
              kw_text,
              "메타 키워드를 추가하세요. 예: '이후, 소설가, 한국소설, 문학'")

    # ── 4. H1 태그 ──────────────────────────────────────────────
    h1_tags = soup.find_all("h1")
    h1_texts = [h.get_text(strip=True) for h in h1_tags]
    has_single_h1 = len(h1_tags) == 1
    add_check("h1", bool(h1_tags),
              " / ".join(h1_texts[:3]),
              "H1 태그가 없습니다. 페이지당 H1 하나, 핵심 키워드 포함 권장.")

    # ── 5. H2/H3 구조 ───────────────────────────────────────────
    h2_h3 = soup.find_all(["h2", "h3"])
    add_check("h2_h3", len(h2_h3) >= 2,
              f"H2: {len(soup.find_all('h2'))}개, H3: {len(soup.find_all('h3'))}개",
              "H2/H3 헤딩으로 콘텐츠 구조를 명확히 하면 SEO에 유리합니다.")

    # ── 6. Canonical ────────────────────────────────────────────
    canonical = soup.find("link", attrs={"rel": "canonical"})
    can_href = canonical.get("href", "") if canonical else ""
    add_check("canonical", bool(can_href),
              can_href,
              "Canonical URL을 설정하세요. 중복 콘텐츠 문제를 방지합니다.")

    # ── 7. Open Graph ───────────────────────────────────────────
    og_title = soup.find("meta", property="og:title")
    og_title_text = og_title.get("content", "") if og_title else ""
    add_check("og_title", bool(og_title_text), og_title_text,
              "og:title을 추가하세요. SNS 공유 시 제목으로 사용됩니다.")

    og_desc = soup.find("meta", property="og:description")
    og_desc_text = og_desc.get("content", "") if og_desc else ""
    add_check("og_description", bool(og_desc_text), og_desc_text,
              "og:description을 추가하세요.")

    og_img = soup.find("meta", property="og:image")
    og_img_src = og_img.get("content", "") if og_img else ""
    add_check("og_image", bool(og_img_src), og_img_src,
              "og:image를 추가하세요. SNS 공유 시 썸네일로 사용됩니다.")

    # ── 8. 구조화 데이터 (JSON-LD) ──────────────────────────────
    json_ld = soup.find_all("script", attrs={"type": "application/ld+json"})
    has_schema = len(json_ld) > 0
    schema_types = []
    for jl in json_ld:
        text = jl.string or ""
        types = re.findall(r'"@type"\s*:\s*"([^"]+)"', text)
        schema_types.extend(types)
    add_check("structured_data", has_schema,
              ", ".join(schema_types) if schema_types else "",
              "JSON-LD 구조화 데이터를 추가하세요. Person/Author 스키마로 인물 정보를 명시하면 네이버 지식인/검색 결과에 노출이 유리합니다.")

    # ── 9. lang 속성 ────────────────────────────────────────────
    html_tag = soup.find("html")
    lang = html_tag.get("lang", "") if html_tag else ""
    add_check("lang", bool(lang), lang,
              "HTML lang 속성을 'ko'로 설정하세요. 한국어 콘텐츠임을 검색엔진에 알립니다.")

    # ── 10. 모바일 Viewport ─────────────────────────────────────
    viewport = soup.find("meta", attrs={"name": re.compile(r"viewport", re.I)})
    vp_content = viewport.get("content", "") if viewport else ""
    add_check("mobile_viewport", bool(vp_content), vp_content,
              "Viewport 메타태그를 추가하세요. 모바일 검색 최적화에 필수입니다.")

    # ── 11. 내부 링크 ───────────────────────────────────────────
    parsed = urlparse(url)
    base_domain = parsed.netloc
    all_links = soup.find_all("a", href=True)

    def _is_internal(href: str) -> bool:
        href = href.strip()
        if not href:
            return False
        if href.startswith("#"):           # 같은 페이지 내 앵커 네비게이션
            return True
        if href.startswith("/"):           # 루트 상대 경로
            return True
        if base_domain and base_domain in href:   # 같은 도메인 절대 경로
            return True
        if not href.startswith(("http://", "https://", "mailto:", "tel:", "javascript:")):
            return True                    # 일반 상대 경로 (about.html 등)
        return False

    internal = [a for a in all_links if _is_internal(a["href"])]
    add_check("internal_links", len(internal) >= 3,
              f"내부링크 {len(internal)}개",
              "내부 링크를 늘려 페이지 간 연결성을 강화하세요.")

    # ── 점수 계산 ───────────────────────────────────────────────
    passed = sum(1 for c in checks if c["passed"])
    score = round(passed / len(checks) * 100) if checks else 0

    return {
        "label": page_label,
        "url": url,
        "meta": meta,
        "checks": checks,
        "score": score,
        "passed": passed,
        "total": len(checks),
        "recommendations": recommendations,
    }


def run_full_analysis() -> list[dict]:
    """전체 정보 소스 분석 (홈페이지·위키백과·나무위키·교보문고·구글·유튜브).

    분석 대상은 config.ANALYSIS_TARGETS 가 단일 출처(single source of truth).
    여기에 항목을 추가하면 대시보드 카드·상단 메뉴·일일 배치잡에 자동 반영된다.
    """
    results = []
    for label, url in ANALYSIS_TARGETS:
        print(f"\n🔎 분석 중: {label}")
        result = analyze_seo(url, label)
        results.append(result)
        time.sleep(CRAWL_DELAY)
    return results


if __name__ == "__main__":
    results = run_full_analysis()
    for r in results:
        print(f"\n{'='*60}")
        print(f"📄 {r['label']}")
        print(f"   점수: {r['score']}점 ({r['passed']}/{r['total']} 항목 통과)")
        print(f"   권고사항 {len(r['recommendations'])}건")
        for rec in r["recommendations"]:
            print(f"   ⚠️  {rec}")
