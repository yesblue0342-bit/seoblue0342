"""
설정 파일 - 이후(소설가) 네이버 SEO 최적화 도구
"""

# 검색 키워드
SEARCH_KEYWORD = "이후"

# 내 페이지 URL 목록 (순위 체크 대상)
MY_PAGES = {
    "naver_profile": "search.naver.com",
    "wikipedia": "ko.wikipedia.org/wiki/%EC%9D%B4%ED%9B%84_(%EC%86%8C%EC%84%A4%EA%B0%80)",
    "homepage": "xn--hu5b23z.com",  # 이후.com
    "namu": "namu.wiki",            # 나무위키
    "daum": "search.daum.net",      # 다음 검색
    "kyobo": "store.kyobobook.co.kr",  # 교보문고 작가 페이지
    "youtube": "youtube.com",       # 유튜브 채널
}

# 홈페이지 실제 URL
HOMEPAGE_URL = "https://xn--hu5b23z.com/"
WIKIPEDIA_URL = "https://ko.wikipedia.org/wiki/%EC%9D%B4%ED%9B%84_(%EC%86%8C%EC%84%A4%EA%B0%80)"
NAVER_PROFILE_URL = "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=bjky&pkid=1&os=215161&qvt=0&query=%EC%9D%B4%ED%9B%84"

# 추가 정보 소스 URL (나무위키 / 다음 / 교보문고 / 구글 / 유튜브)
NAMU_URL = "https://namu.wiki/w/%EC%9D%B4%ED%9B%84(%EC%86%8C%EC%84%A4%EA%B0%80)"
DAUM_URL = "https://search.daum.net/search?w=tot&q=%EC%86%8C%EC%84%A4%EA%B0%80%EC%9D%B4%ED%9B%84"
KYOBO_URL = "https://store.kyobobook.co.kr/person/detail/1000809404"
GOOGLE_URL = "https://www.google.com/search?q=%EC%86%8C%EC%84%A4%EA%B0%80%EC%9D%B4%ED%9B%84"

# 구글 SERP 노출 체크용 검색어 (Serper.dev API에 전달).
# GOOGLE_URL 은 대시보드 카드의 링크 표시용으로만 유지한다.
GOOGLE_SEARCH_QUERY = "소설가 이후"
# 실제 운영 채널(약 690명 구독·동영상 다수). 이전 값은 유튜브가 음원 유통으로 자동 생성한
# Topic("주제") 채널이라 소개글이 없어 메타 디스크립션 등 평가가 원리적으로 불가능했음.
YOUTUBE_URL = "https://www.youtube.com/channel/UC3iQTM8DVgzRhgArrSIPp2g"

# 대시보드 분석 대상 (라벨, URL, 페이지 유형).
# 대시보드의 카드/메뉴는 이 목록을 그대로 따른다 — 여기에 추가하면 카드·메뉴·배치잡 모두 반영됨.
#
# 페이지 유형 (seo_analyzer 가 유형별로 체크 항목·권고 내용을 다르게 적용):
#   owned   : 우리가 직접 수정 가능한 페이지 → 전체 온페이지 SEO 체크리스트
#   profile : 외부 플랫폼 프로필/문서 (HTML 직접 수정 불가) → 콘텐츠·노출 중심 체크
#   serp    : 검색 결과 페이지 → 페이지 자체가 아니라 '검색결과에 노출되는지'를 체크
ANALYSIS_TARGETS = [
    ("이후 공식 홈페이지 (이후.com)", HOMEPAGE_URL, "owned"),
    ("위키백과 - 이후 (소설가)", WIKIPEDIA_URL, "profile"),
    ("나무위키 - 이후(소설가)", NAMU_URL, "profile"),
    ("다음 검색 - 소설가 이후", DAUM_URL, "serp"),
    ("구글 검색 - 소설가 이후", GOOGLE_URL, "serp"),
    ("교보문고 - 작가 이후", KYOBO_URL, "profile"),
    ("유튜브 - 이후 채널", YOUTUBE_URL, "profile"),
]

# 네이버 검색 URL (대시보드의 '직접 검색' 링크 표시용으로만 유지)
NAVER_SEARCH_URL = "https://search.naver.com/search.naver"

# 네이버 오픈API 노출 체크용 검색어. '이후' 단독은 동명이인에 밀리므로 '소설가 이후' 사용.
NAVER_SEARCH_QUERY = "소설가 이후"

# 요청 헤더 (브라우저 에뮬레이션)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.naver.com/",
}

# DB 경로
DB_PATH = "rank_history.db"

# 크롤링 딜레이 (초) - 서버 부하 방지
CRAWL_DELAY = 2

# 순위 체크 최대 페이지 수
MAX_PAGES = 5
