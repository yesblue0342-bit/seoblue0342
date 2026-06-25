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
}

# 홈페이지 실제 URL
HOMEPAGE_URL = "https://xn--hu5b23z.com/"
WIKIPEDIA_URL = "https://ko.wikipedia.org/wiki/%EC%9D%B4%ED%9B%84_(%EC%86%8C%EC%84%A4%EA%B0%80)"
NAVER_PROFILE_URL = "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=bjky&pkid=1&os=215161&qvt=0&query=%EC%9D%B4%ED%9B%84"

# 네이버 검색 URL
NAVER_SEARCH_URL = "https://search.naver.com/search.naver"

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
