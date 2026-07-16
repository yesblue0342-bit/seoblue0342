"""
SEO 분석기
- 페이지 유형별로 다른 체크리스트를 적용해 '실행 가능한' 권고만 생성
  * owned   : 직접 관리하는 페이지(홈페이지) → 전체 온페이지 SEO 체크리스트
  * profile : 외부 플랫폼 프로필/문서(위키·교보문고·유튜브 등)
              → HTML을 직접 고칠 수 없으므로 콘텐츠·노출 중심 체크와
                "우리가 할 수 있는 행동" 위주의 권고 생성
  * serp    : 검색 결과 페이지(구글·다음 등)
              → 검색결과 페이지 자체의 메타태그는 평가 대상이 아님.
                '검색결과에 이후 관련 페이지가 노출되는지'를 체크
"""

import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

import serp_checker
from config import (
    HEADERS, HOMEPAGE_URL, WIKIPEDIA_URL, CRAWL_DELAY, ANALYSIS_TARGETS,
    GOOGLE_SEARCH_QUERY,
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
    "keyword_mentions": "본문 키워드 언급",
    "serp_relevance": "검색결과 관련성 (소설가 이후)",
}

KEYWORD = "이후"
KEYWORD_ALT = ["소설가", "소설", "작가"]

# 페이지 유형별 안내 문구 (리포트/대시보드에 표시)
PAGE_KIND_NOTES = {
    "owned": "직접 관리 페이지 — 아래 권고사항을 홈페이지에 바로 적용할 수 있습니다.",
    "profile": ("외부 플랫폼 페이지 — HTML(메타태그 등)은 직접 수정할 수 없어 "
                "콘텐츠·노출 중심으로만 평가합니다. 권고는 '우리가 할 수 있는 행동' 기준입니다."),
    "serp": ("검색 결과 페이지 — 검색결과 페이지 자체의 SEO는 평가 대상이 아니며, "
             "검색결과에 '이후' 관련 페이지들이 노출되는지를 평가합니다."),
}

# serp 유형: 검색결과에서 노출 여부를 확인할 대상 (이름, HTML에서 찾을 문자열들, 미노출 시 권고)
SERP_PRESENCE_TARGETS = [
    ("공식 홈페이지 (이후.com)", ["xn--hu5b23z.com", "이후.com"],
     None),  # None → 검색엔진별 등록 안내(_serp_engine_tip)로 대체
    ("위키백과 문서", ["ko.wikipedia.org"],
     "위키백과 문서에 출처·대표작·외부 링크를 보강해 문서 신뢰도를 높이세요."),
    ("나무위키 문서", ["namu.wiki"],
     "나무위키 문서 내용(약력·작품 목록)을 보강하고 다른 문서에서 링크되도록 하세요."),
    ("교보문고 작가 페이지", ["kyobobook.co.kr"],
     "출판사를 통해 교보문고 작가 정보(소개·사진·대표작) 등록/갱신을 요청하세요."),
    # 채널ID·@handle뿐 아니라 개별 영상(watch)·일반 youtube.com 링크도 노출로 인정
    # (Serper 결과에는 채널 홈이 아니라 영상 링크로 노출되는 경우가 많음)
    ("유튜브 채널", ["UCQdIJKAOKVI8pKIsvcFBEKA", "youtube.com/@",
                 "youtube.com/watch", "youtube.com"],
     "유튜브 채널명·소개에 '이후 소설가' 키워드를 포함하고 영상을 정기적으로 올리세요."),
]


def _serp_engine_tip(url: str) -> str:
    """검색엔진별 홈페이지 등록 안내."""
    host = urlparse(url).netloc
    if "google" in host:
        return ("Google Search Console(search.google.com/search-console)에 이후.com을 "
                "등록하고 사이트맵(sitemap.xml)을 제출하세요.")
    if "daum" in host:
        return "다음 검색등록(register.search.daum.net)에서 이후.com 사이트 등록을 신청하세요."
    if "naver" in host:
        return ("네이버 서치어드바이저(searchadvisor.naver.com)에 이후.com을 등록하고 "
                "사이트맵·RSS를 제출하세요.")
    return "해당 검색엔진의 웹마스터 도구에 이후.com을 등록하고 사이트맵을 제출하세요."


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


class _Collector:
    """체크 결과·권고 누적 헬퍼 (유형별 분석 함수 공용)."""

    def __init__(self):
        self.checks = []
        self.recommendations = []

    def add(self, key: str, passed: bool, value: str = "",
            detail: str = "", label: str = ""):
        self.checks.append({
            "key": key,
            "label": label or SEO_CHECKS.get(key, key),
            "passed": passed,
            "value": value[:120] if value else "",
            "detail": detail,
        })
        if not passed and detail:
            self.recommendations.append(f"[{label or SEO_CHECKS.get(key, key)}] {detail}")

    def result(self, page_label: str, url: str, meta: dict) -> dict:
        passed = sum(1 for c in self.checks if c["passed"])
        total = len(self.checks)
        return {
            "label": page_label,
            "url": url,
            "meta": meta,
            "checks": self.checks,
            "score": round(passed / total * 100) if total else 0,
            "passed": passed,
            "total": total,
            "recommendations": self.recommendations,
        }


# ──────────────────────────────────────────────────────────────
#  공통 파싱 헬퍼
# ──────────────────────────────────────────────────────────────
def _get_title(soup) -> str:
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else ""


def _get_meta_desc(soup) -> str:
    tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    return tag.get("content", "") if tag else ""


def _get_og(soup, prop: str) -> str:
    tag = soup.find("meta", property=f"og:{prop}")
    return tag.get("content", "") if tag else ""


# ──────────────────────────────────────────────────────────────
#  owned: 직접 관리 페이지 — 전체 온페이지 체크리스트
# ──────────────────────────────────────────────────────────────
def _analyze_owned(soup, url: str) -> _Collector:
    c = _Collector()

    # ── 1. Title 태그 ──────────────────────────────────────────
    title_text = _get_title(soup)
    c.add("title", bool(title_text) and len(title_text) >= 10,
          title_text,
          "Title 태그가 없거나 너무 짧습니다. 30~60자의 명확한 제목을 추가하세요.")
    c.add("keyword_in_title", KEYWORD in title_text,
          title_text,
          f"제목에 핵심 키워드 '{KEYWORD}'(소설가)를 포함하세요. 예: '이후 소설가 공식 홈페이지'")

    # ── 2. 메타 디스크립션 ──────────────────────────────────────
    desc_text = _get_meta_desc(soup)
    c.add("meta_description", bool(desc_text) and len(desc_text) >= 50,
          desc_text,
          "메타 디스크립션이 없거나 50자 미만입니다. 120~160자로 작성하세요.")
    c.add("keyword_in_desc", KEYWORD in desc_text,
          desc_text,
          "메타 디스크립션에 '이후', '소설가' 등 핵심 키워드를 자연스럽게 포함하세요.")

    # ── 3. 메타 키워드 ──────────────────────────────────────────
    meta_kw = soup.find("meta", attrs={"name": re.compile(r"keywords", re.I)})
    kw_text = meta_kw.get("content", "") if meta_kw else ""
    c.add("meta_keywords", bool(kw_text),
          kw_text,
          "메타 키워드를 추가하세요. 예: '이후, 소설가, 한국소설, 문학'")

    # ── 4. H1 태그 ──────────────────────────────────────────────
    h1_tags = soup.find_all("h1")
    h1_texts = [h.get_text(strip=True) for h in h1_tags]
    c.add("h1", bool(h1_tags),
          " / ".join(h1_texts[:3]),
          "H1 태그가 없습니다. 페이지당 H1 하나, 핵심 키워드 포함 권장.")

    # ── 5. H2/H3 구조 ───────────────────────────────────────────
    h2_h3 = soup.find_all(["h2", "h3"])
    c.add("h2_h3", len(h2_h3) >= 2,
          f"H2: {len(soup.find_all('h2'))}개, H3: {len(soup.find_all('h3'))}개",
          "H2/H3 헤딩으로 콘텐츠 구조를 명확히 하면 SEO에 유리합니다.")

    # ── 6. Canonical ────────────────────────────────────────────
    canonical = soup.find("link", attrs={"rel": "canonical"})
    can_href = canonical.get("href", "") if canonical else ""
    c.add("canonical", bool(can_href),
          can_href,
          "Canonical URL을 설정하세요. 중복 콘텐츠 문제를 방지합니다.")

    # ── 7. Open Graph ───────────────────────────────────────────
    c.add("og_title", bool(_get_og(soup, "title")), _get_og(soup, "title"),
          "og:title을 추가하세요. SNS 공유 시 제목으로 사용됩니다.")
    c.add("og_description", bool(_get_og(soup, "description")), _get_og(soup, "description"),
          "og:description을 추가하세요.")
    c.add("og_image", bool(_get_og(soup, "image")), _get_og(soup, "image"),
          "og:image를 추가하세요. SNS 공유 시 썸네일로 사용됩니다.")

    # ── 8. 구조화 데이터 (JSON-LD) ──────────────────────────────
    json_ld = soup.find_all("script", attrs={"type": "application/ld+json"})
    schema_types = []
    for jl in json_ld:
        text = jl.string or ""
        schema_types.extend(re.findall(r'"@type"\s*:\s*"([^"]+)"', text))
    c.add("structured_data", len(json_ld) > 0,
          ", ".join(schema_types) if schema_types else "",
          "JSON-LD 구조화 데이터를 추가하세요. Person/Author 스키마로 인물 정보를 명시하면 "
          "네이버 지식인/검색 결과에 노출이 유리합니다. (deploy/structured-data.jsonld 참고)")

    # ── 9. lang 속성 ────────────────────────────────────────────
    html_tag = soup.find("html")
    lang = html_tag.get("lang", "") if html_tag else ""
    c.add("lang", bool(lang), lang,
          "HTML lang 속성을 'ko'로 설정하세요. 한국어 콘텐츠임을 검색엔진에 알립니다.")

    # ── 10. 모바일 Viewport ─────────────────────────────────────
    viewport = soup.find("meta", attrs={"name": re.compile(r"viewport", re.I)})
    vp_content = viewport.get("content", "") if viewport else ""
    c.add("mobile_viewport", bool(vp_content), vp_content,
          "Viewport 메타태그를 추가하세요. 모바일 검색 최적화에 필수입니다.")

    # ── 11. 내부 링크 ───────────────────────────────────────────
    base_domain = urlparse(url).netloc
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
    c.add("internal_links", len(internal) >= 3,
          f"내부링크 {len(internal)}개",
          "내부 링크를 늘려 페이지 간 연결성을 강화하세요.")

    return c


# ──────────────────────────────────────────────────────────────
#  profile: 외부 플랫폼 페이지 — 콘텐츠·노출 중심 체크
#  (메타키워드·canonical·viewport 등 플랫폼 소관 항목은 평가·권고에서 제외)
# ──────────────────────────────────────────────────────────────
def _analyze_profile(soup) -> _Collector:
    c = _Collector()

    title_text = _get_title(soup)
    c.add("keyword_in_title", KEYWORD in title_text,
          title_text,
          "페이지 제목에 '이후'가 없습니다. 프로필명/문서명이 '이후(소설가)' 형태로 "
          "표기되도록 편집하거나 플랫폼에 수정을 요청하세요.")

    # 플랫폼이 메타/OG 디스크립션을 소개글에서 자동 생성하는 경우가 많음
    desc_text = _get_meta_desc(soup) or _get_og(soup, "description")
    c.add("meta_description", bool(desc_text) and len(desc_text) >= 50,
          desc_text,
          "페이지 요약 정보가 부족합니다. 프로필 소개글/문서 첫 문단을 보강하면 "
          "검색결과에 표시되는 설명이 좋아집니다.")
    c.add("keyword_in_desc", KEYWORD in desc_text,
          desc_text,
          "소개글(첫 문단)에 '이후', '소설가' 키워드가 들어가도록 본문을 보강하세요. "
          "플랫폼이 이 내용으로 검색용 설명을 자동 생성합니다.")

    og_title = _get_og(soup, "title")
    og_img = _get_og(soup, "image")
    c.add("og_title", bool(og_title), og_title,
          "SNS 공유 시 제목 정보가 없습니다. 프로필명이 제대로 등록돼 있는지 확인하세요.")
    c.add("og_image", bool(og_img), og_img,
          "SNS 공유 썸네일이 없습니다. 프로필 사진/대표 이미지를 등록하세요.")

    # 본문에 인물 관련 키워드가 충분히 언급되는지
    body_text = soup.get_text(" ", strip=True)
    mentions = body_text.count(KEYWORD)
    has_context = any(alt in body_text for alt in KEYWORD_ALT)
    c.add("keyword_mentions", mentions >= 3 and has_context,
          f"'{KEYWORD}' {mentions}회 언급",
          "본문에 '이후'·'소설가' 언급이 적습니다. 약력·대표작 등 인물 정보를 "
          "본문(소개글/문서)에 보강하세요.")

    return c


# ──────────────────────────────────────────────────────────────
#  serp: 검색 결과 — '노출 여부' 체크
#  - 구글: Serper.dev API 사용 (스크래핑은 봇 차단으로 거짓 음성)
#  - 다음: 공식 API가 없어 스크래핑 유지, 봇 차단 감지 시 '측정 불가' 처리
# ──────────────────────────────────────────────────────────────
def _serp_unmeasurable(url: str, page_label: str, meta: dict, reason: str) -> dict:
    """측정 불가 결과 — 실패 체크로 0점을 찍는 대신 원인 안내만 남긴다."""
    return {
        "label": page_label,
        "url": url,
        "kind": "serp",
        "meta": meta,
        "checks": [],
        "score": 0,
        "passed": 0,
        "total": 0,
        "measurable": False,
        "recommendations": [reason],
    }


def _serp_collector(url: str, relevance_text: str, found: dict) -> _Collector:
    """SERP 체크 결과(관련성 + 노출 5건)를 공통 checks 구조로 변환."""
    c = _Collector()
    relevant = KEYWORD in relevance_text and any(alt in relevance_text for alt in KEYWORD_ALT)
    c.add("serp_relevance", relevant,
          f"'{KEYWORD}' {relevance_text.count(KEYWORD)}회 언급",
          "검색결과에 소설가 관련 내용이 부족합니다. 동명 키워드에 밀리고 있으므로 "
          "'이후 소설가' 표기를 모든 채널에서 일관되게 사용하고 콘텐츠 발행을 늘리세요.")
    for name, needles, advice in SERP_PRESENCE_TARGETS:
        detail = advice or _serp_engine_tip(url)
        c.add(f"serp_{needles[0]}", found.get(name, False),
              "노출됨" if found.get(name) else "",
              f"{name}이(가) 검색결과에 보이지 않습니다. {detail}",
              label=f"검색결과 노출: {name}")
    return c


def _analyze_serp_google_api(url: str, page_label: str) -> dict:
    """구글 SERP 노출 체크 — Serper.dev API (페이지 fetch 없음)."""
    api = serp_checker.check_google_presence(GOOGLE_SEARCH_QUERY)

    meta = {"url": url, "status": None, "response_time": None, "content_length": 0}
    if api["status"] == "no_api_key":
        return _serp_unmeasurable(url, page_label, meta,
            "SERPER_API_KEY 미설정: serper.dev에 가입해 API 키를 발급받아 "
            "환경변수(SERPER_API_KEY)로 설정하세요. 설정 방법은 deploy/README.md 참고.")
    if api["status"] != "ok":
        return _serp_unmeasurable(url, page_label, meta,
            f"Serper.dev API 호출 실패: {api.get('detail', '알 수 없는 오류')} "
            "— 일시적 오류면 다음 분석에서 재시도됩니다.")

    # Serper가 돌려준 상위 결과 링크/텍스트 안에서 각 대상 노출 여부를 판정
    haystack = " ".join(api.get("links", []))
    found = {name: any(n in haystack for n in needles)
             for name, needles, _ in SERP_PRESENCE_TARGETS}

    api_meta = api.get("api_meta", {})
    meta.update(status=200,
                response_time=api_meta.get("response_time"),
                content_length=api_meta.get("content_length", 0),
                final_url=url)
    collector = _serp_collector(url, api.get("relevance_text", ""), found)
    result = collector.result(page_label, url, meta)
    result["kind"] = "serp"
    result["measurable"] = True
    return result


def _analyze_serp(soup, url: str) -> _Collector:
    """스크래핑 기반 SERP 체크 (다음 등 공식 API가 없는 검색엔진용)."""
    html = str(soup)
    body_text = soup.get_text(" ", strip=True)
    found = {name: any(n in html for n in needles)
             for name, needles, _ in SERP_PRESENCE_TARGETS}
    return _serp_collector(url, body_text, found)


def analyze_seo(url: str, page_label: str, kind: str = "owned") -> dict:
    """
    단일 페이지 SEO 분석 (kind: owned | profile | serp)
    Returns: {"label", "url", "kind", "checks", "score", "recommendations", ...}
    serp 결과에는 "measurable" 필드가 추가된다 (False = 측정 불가, 점수 표시 안 함).
    """
    # 구글 SERP는 스크래핑이 봇 차단으로 거짓 음성을 내므로 Serper.dev API 사용
    if kind == "serp" and "google" in urlparse(url).netloc:
        return _analyze_serp_google_api(url, page_label)

    soup, meta = fetch_page(url)

    if soup is None:
        result = {
            "label": page_label,
            "url": url,
            "kind": kind,
            "meta": meta,
            "checks": [],
            "score": 0,
            "passed": 0,
            "total": 0,
            "recommendations": [f"페이지 접근 불가: {meta.get('error', '알 수 없는 오류')}"],
        }
        if kind == "serp":
            result["measurable"] = False
        return result

    if kind == "serp":
        # 봇 차단/동의 페이지 등으로 정상 SERP가 아니면
        # 실패 체크로 0점을 찍지 않고 '측정 불가'로 처리 (거짓 음성 방지)
        if meta.get("content_length", 0) < 20_000:
            return _serp_unmeasurable(url, page_label, meta,
                "검색엔진이 봇 요청을 차단했거나 축소된 페이지를 반환해 노출 여부를 "
                "측정할 수 없습니다. 브라우저에서 직접 검색해 확인하세요.")
        collector = _analyze_serp(soup, url)
        result = collector.result(page_label, url, meta)
        result["kind"] = kind
        result["measurable"] = True
        return result

    if kind == "profile":
        collector = _analyze_profile(soup)
    else:
        collector = _analyze_owned(soup, url)

    result = collector.result(page_label, url, meta)
    result["kind"] = kind
    return result


def run_full_analysis() -> list[dict]:
    """전체 정보 소스 분석 (홈페이지·위키백과·나무위키·교보문고·구글·유튜브).

    분석 대상은 config.ANALYSIS_TARGETS 가 단일 출처(single source of truth).
    여기에 항목을 추가하면 대시보드 카드·상단 메뉴·일일 배치잡에 자동 반영된다.
    """
    results = []
    for target in ANALYSIS_TARGETS:
        label, url = target[0], target[1]
        kind = target[2] if len(target) > 2 else "owned"
        print(f"\n🔎 분석 중: {label}")
        result = analyze_seo(url, label, kind)
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
