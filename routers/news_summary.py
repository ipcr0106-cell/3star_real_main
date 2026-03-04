"""
★ C파트 — 뉴스 요약 라우터 (news_summary.py) ★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[담당 팀원] C파트 (PM 지수 작성)
[수정 가능 범위] 이 파일 전체 + templates/b2b/news.html의 {% block content %} 안

[엔드포인트 목록] (main.py에서 prefix="/api" 로 연결됨)
  POST /api/fetch          → Tab 1 B2C 베트남 소비 트렌드 뉴스 수집
  POST /api/fetch-gov      → Tab 2 B2B 베트남 정부·법규 수집
  POST /api/news/translate → Tab 1 전용 DeepL 번역 (베트남어 → 한국어)
  POST /api/fetch-seo      → Tab 3 SEO 키워드 분석
  POST /api/seo/translate  → Tab 3 전용 DeepL 번역 버튼 (베트남어 → 한국어)
  GET  /api/news/cache     → 대시보드용 캐시 뉴스 반환 (새로 수집 안 함)
  GET  /api/news/trending  → 대시보드용 베트남 실시간 검색어 (RSS만, 빠름)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[병합 규칙]
  · main.py 수정 금지
  · CSS 클래스명: .c- prefix 사용 (예: .c-news-card)
  · 과도한 RSS 호출 방지: 결과 캐싱 권장 (module-level 변수)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import time
import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import feedparser
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import ssl
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from fastapi import APIRouter
from pydantic import BaseModel
from openai import OpenAI
import deepl
from dotenv import load_dotenv
from urllib.parse import urljoin
import pdfplumber
from io import BytesIO

# ──────────────────────────────────────────────────────────────────
# 0. 초기 설정
# ──────────────────────────────────────────────────────────────────
load_dotenv()

router = APIRouter()

openai_client    = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
deepl_translator = deepl.Translator(os.getenv("DEEPL_API_KEY"))

# 서버 메모리 캐시
_news_cache: list[dict] = []
_gov_cache:  list[dict] = []
_seo_cache:  dict       = {}
_url_dates:  dict[str, str] = {}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest":  "document",
    "Sec-Fetch-Mode":  "navigate",
    "Sec-Fetch-Site":  "none",
    "Sec-Fetch-User":  "?1",
}

SOURCES = [
{"name": "Kênh 14",     "flag": "🎯", "type": "rss", "url": "https://kenh14.vn/index.rss",        "max": 5},
{"name": "Phụ Nữ Today","flag": "👩", "type": "rss", "url": "https://phunutoday.vn/rss/home.rss", "max": 5},
{"name": "Dân Trí",     "flag": "📰", "type": "rss", "url": "https://dantri.com.vn/rss/home.rss", "max": 5},
]

GOV_SOURCES = [
    {"name": "베트남 공식 포털", "flag": "🏛️", "type": "rss",  "url": "https://www.vietnam.vn/ko/sitemap.rss",                                          "max": 5},
    {"name": "산업통상부(MoIT)", "flag": "⚖️", "type": "html", "url": "https://moit.gov.vn/en/news/latest-news",                                         "max": 5},
    {"name": "식품위해평가원(VFSA)", "flag": "🔬", "type": "html", "url": "https://vfsa.org.vn/",                                                          "max": 5},
    {"name": "베트남 관세청",    "flag": "🛃", "type": "html", "url": "https://www.customs.gov.vn/index.jsp?ngon_ngu=en",                                  "max": 5},
    {"name": "H-Cargo 수입실무", "flag": "📦", "type": "html", "url": "https://www.hcargovn.com/post/food-import-procedures-detailed-process",            "max": 3},
]

SEO_SEED_KEYWORDS = [
    "nước sốt Hàn Quốc",
    "gia vị nấu ăn",
    "viên nước dùng",
    "nấu ăn nhanh",
    "món ăn Hàn Quốc",
]

# ── 폴백 소스: 기본 소스 결과 부족 시 사용 ─────────────────────
FALLBACK_B2C_SOURCES = [
    {"name": "VnExpress",  "flag": "📰", "type": "rss", "url": "https://vnexpress.net/rss/tin-moi-nhat.rss", "max": 6},
    {"name": "Thanh Niên", "flag": "📰", "type": "rss", "url": "https://thanhnien.vn/rss/home.rss",          "max": 4},
    {"name": "Tuổi Trẻ",   "flag": "📰", "type": "rss", "url": "https://tuoitre.vn/rss/tin-moi-nhat.rss",   "max": 4},
]

FALLBACK_B2B_SOURCES = [
    {"name": "구글뉴스-식품무역", "flag": "🔍", "type": "rss",
     "url": "https://news.google.com/rss/search?q=thực+phẩm+nhập+khẩu+quy+định+việt+nam&hl=vi&gl=VN&ceid=VN:vi",
     "max": 5},
    {"name": "VnExpress 비즈",   "flag": "💼", "type": "rss",
     "url": "https://vnexpress.net/rss/kinh-doanh.rss",
     "max": 5},
]


# ══════════════════════════════════════════════════════════════════
# 1. 공통 유틸리티 — HTTP 요청 & XML 파싱
# ══════════════════════════════════════════════════════════════════

class _WeakSSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def _get(url: str, timeout: int = 12, max_retries: int = 3) -> requests.Response | None:
    for attempt in range(max_retries):
        try:
            session = requests.Session()
            session.mount("https://", _WeakSSLAdapter())
            resp = session.get(url, headers=HEADERS, timeout=timeout, verify=False)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  [GET 최종 실패] {url[:70]} → {e}")
                return None
            print(f"  [GET 재시도 {attempt+1}/{max_retries}] {url[:70]}")
            time.sleep(2)


def _parse_xml_urls(xml_bytes: bytes) -> list[str]:
    urls = []
    try:
        root = ET.fromstring(xml_bytes)
        for el in root.iter():
            tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if tag == "loc" and el.text:
                text = el.text.strip()
                if text.startswith("http"):
                    urls.append(text)
    except ET.ParseError as e:
        print(f"  [XML 파싱 오류] {e}")
    return urls


# ══════════════════════════════════════════════════════════════════
# 2. Tab 1 — B2C URL 수집 레이어
# ══════════════════════════════════════════════════════════════════

def collect_urls_rss(source: dict) -> list[str]:
    global _url_dates
    parsed = feedparser.parse(source["url"])
    urls   = []
    for e in parsed.entries:
        url = e.get("link", "")
        if not url:
            continue
        urls.append(url)
        try:
            if hasattr(e, "published_parsed") and e.published_parsed:
                _url_dates[url] = time.strftime("%Y.%m.%d", e.published_parsed)
        except Exception:
            pass
    print(f"  [{source['name']}] RSS → {len(urls)}개 URL")
    return urls[: source["max"]]


def collect_urls_sitemap_news(source: dict) -> list[str]:
    resp = _get(source["url"])
    if not resp:
        return []
    urls = _parse_xml_urls(resp.content)
    print(f"  [{source['name']}] 사이트맵(뉴스) → {len(urls)}개 URL")
    return urls[: source["max"]]


def collect_urls_sitemap_index(source: dict) -> list[str]:
    resp = _get(source["url"])
    if not resp:
        return []
    sub_sitemaps = _parse_xml_urls(resp.content)
    print(f"  [{source['name']}] 인덱스 → 하위 사이트맵 {len(sub_sitemaps)}개 발견")
    if not sub_sitemaps:
        return []
    article_urls: list[str] = []
    for sm_url in sub_sitemaps[:3]:
        sub_resp = _get(sm_url)
        if not sub_resp:
            continue
        found    = _parse_xml_urls(sub_resp.content)
        articles = [u for u in found if not u.endswith(".xml")]
        article_urls.extend(articles)
        if len(article_urls) >= source["max"]:
            break
        time.sleep(0.3)
    print(f"  [{source['name']}] 최종 기사 URL {len(article_urls)}개")
    return article_urls[: source["max"]]


def collect_urls_sitemap(source: dict) -> list[str]:
    resp = _get(source["url"])
    if not resp:
        return []
    urls     = _parse_xml_urls(resp.content)
    articles = [u for u in urls if not u.endswith(".xml")]
    print(f"  [{source['name']}] 사이트맵 → {len(articles)}개 URL")
    return articles[: source["max"]]


URL_COLLECTORS = {
    "rss":           collect_urls_rss,
    "sitemap_news":  collect_urls_sitemap_news,
    "sitemap_index": collect_urls_sitemap_index,
    "sitemap":       collect_urls_sitemap,
}


# ══════════════════════════════════════════════════════════════════
# 3. 기사 본문 스크래핑 (Tab 1 & Tab 2 공용)
# ══════════════════════════════════════════════════════════════════

BODY_SELECTORS: dict[str, list[str]] = {
    "VnExpress": ["article.fck_detail", "div.sidebar-1 p"],
    "Kênh 14":   ["div.knc-content", "div.detail-content"],
    "Eva.vn":    ["div.content-body", "article.article-detail"],
    "Báo Mới":   ["div.body-text", "div[class*='content']"],
}

FALLBACK_SELECTORS = [
    "article", "div[class*='article']", "div[class*='content']",
    "div[class*='detail']", "main", ".detail-content", ".chi-tiet-tin"
]


def scrape_article_body(url: str, source_name: str, max_chars: int = 2000) -> str:
    resp = _get(url)
    if not resp:
        return ""

    content_type = resp.headers.get('Content-Type', '').lower()
    if url.lower().endswith(".pdf") or "application/pdf" in content_type:
        try:
            with pdfplumber.open(BytesIO(resp.content)) as pdf:
                pdf_text = "\n".join(
                    [page.extract_text() for page in pdf.pages[:5] if page.extract_text()]
                )
                return f"[PDF 문서 내용 시작]\n{pdf_text}"[:max_chars]
        except Exception as e:
            print(f"  [PDF 파싱 실패] {url[:50]} -> {e}")
            return "PDF 내용을 읽는 중 오류가 발생했습니다."

    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "figure", "iframe", "noscript"]):
        tag.decompose()

    body_text = ""
    selectors = BODY_SELECTORS.get(source_name, []) + FALLBACK_SELECTORS
    for sel in selectors:
        elem = soup.select_one(sel)
        if elem:
            body_text = elem.get_text(separator=" ", strip=True)
            if len(body_text) > 100:
                break

    if not body_text:
        body_text = soup.get_text(separator=" ", strip=True)

    body_text = re.sub(r"\s+", " ", body_text).strip()
    return body_text[:max_chars]


# ══════════════════════════════════════════════════════════════════
# 4. Tab 1 — OpenAI B2C 필터 & 요약
# ══════════════════════════════════════════════════════════════════

B2C_SYSTEM_PROMPT = """너는 베트남 시장에서 한국 식품(소스·시즈닝·코인육수)을 수출하는 마케터야.
주요 타겟은 베트남 SNS를 잘 사용하는 10-30대 소비자들과 주부야.

이 기사가 아래 중 하나라도 해당하면 그 뉴스의 url과 원문 제목을 베트남어로 띄워줘.
또, 해당 뉴스에서 마케팅에 활용할 수 있는 인사이트가 있다면 150자 내외로 간략히 설명해줘.
1. 소비 트렌드 / 유행 / 라이프스타일 변화
2. 경제 상황 / 물가 / 소득 변화 (소비 심리에 영향)
3. 사회적 사건·이슈 (불안심리, 비상식품 수요 등 간접 영향 포함)
4. 연예·문화·SNS 트렌드 (마케팅 소재 가능성)
5. 식품·요리·건강 관련 내용
6. K-콘텐츠·한류·한국 관련 내용
7. 날씨, 자연재해 등 소비 패턴에 영향 줄 수 있는 내용

각 줄은 반드시 "💡"로 시작하고, 총 150자 내외로 작성해.
마지막 줄은 반드시 "→ 마케팅 활용:" 으로 시작하는 구체적 제안 2-3줄을 넣어.

위 기사에 대해 마케팅 인사이트를 베트남어 3줄로 요약해.
SKIP은 순수 스포츠 경기 결과나 베트남과 완전히 무관한 내용일 때만 써."""

B2C_USER_TEMPLATE = """[기사 본문]
{body}

위 기사에 대해 마케팅 인사이트를 베트남어 3줄로 요약하거나, 무관하면 SKIP."""


def b2c_filter_and_summarize(body: str, url: str, source_name: str) -> dict | None:
    if not body.strip():
        return None
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": B2C_SYSTEM_PROMPT},
                {"role": "user",   "content": B2C_USER_TEMPLATE.format(body=body)},
            ],
            max_tokens=300,
            temperature=0.2,
        )
        result = resp.choices[0].message.content.strip()
        if result.upper().startswith("SKIP"):
            print(f"    → SKIP: {url[:60]}")
            return None
        print(f"    → ✅ 선택: {url[:60]}")
        summary_ko = result
        try:
            translated = deepl_translator.translate_text(result, target_lang="KO")
            summary_ko = translated.text
        except Exception as te:
            print(f"    [DeepL 번역 실패] {te}")
        title_ko = summary_ko.split("\n")[0].replace("💡", "").strip()[:60]
        return {
            "source":     source_name,
            "url":        url,
            "summary":    result,
            "summary_ko": summary_ko,
            "title_ko":   title_ko,
            "date":       _url_dates.get(url, ""),
        }
    except Exception as e:
        print(f"    [OpenAI B2C 오류] {e}")
        return None


B2C_FALLBACK_PROMPT = """너는 베트남 시장에서 한국 식품(소스·시즈닝·코인육수)을 수출하는 마케터야.
아래는 베트남 인기 뉴스야. 어떤 주제든 소비자 트렌드·라이프스타일·구매 심리와 연결해서 마케팅 인사이트를 한국어로 작성해.

[규칙]
1. 거의 모든 뉴스에서 인사이트를 찾을 수 있어. 식품·소비·문화·경제·SNS 무엇이든 연결해봐.
2. 💡 로 시작하는 2~3줄 요약 + "→ 마케팅 활용:" 구체적 제안 1줄
3. SKIP 기준: 순수 해외 스포츠 경기 결과처럼 베트남 소비자와 완전히 무관한 경우만"""


def b2c_fallback_summarize(body: str, url: str, source_name: str) -> dict | None:
    if not body.strip():
        return None
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": B2C_FALLBACK_PROMPT},
                {"role": "user",   "content": B2C_USER_TEMPLATE.format(body=body)},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        result = resp.choices[0].message.content.strip()
        if result.upper().startswith("SKIP"):
            print(f"    → SKIP(폴백): {url[:60]}")
            return None
        print(f"    → ✅ 선택(폴백): {url[:60]}")
        summary_ko = result
        try:
            translated = deepl_translator.translate_text(result, target_lang="KO")
            summary_ko = translated.text
        except Exception:
            pass
        title_ko = summary_ko.split("\n")[0].replace("💡", "").strip()[:60]
        return {
            "source":     source_name,
            "url":        url,
            "summary":    result,
            "summary_ko": summary_ko,
            "title_ko":   title_ko,
            "date":       _url_dates.get(url, ""),
        }
    except Exception as e:
        print(f"    [OpenAI 폴백B2C 오류] {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# 5. Tab 2 — 베트남 정부 포털 크롤링 & B2B 요약
# ══════════════════════════════════════════════════════════════════

def collect_gov_article_urls(source: dict) -> list[str]:
    source_url  = source["url"]
    source_type = source.get("type", "html")
    limit       = source.get("max", 5)

    if source_type == "rss":
        parsed = feedparser.parse(source_url)
        urls = [e.get("link", "") for e in parsed.entries if e.get("link", "")]
        print(f"  [{source['name']}] RSS → {len(urls)}개 URL")
        return urls[:limit]

    resp = _get(source_url)
    if not resp:
        return []
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    urls = []

    if "moit.gov.vn" in source_url:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/news/" in href or "/en/news" in href:
                full_url = urljoin("https://moit.gov.vn", href)
                if full_url not in urls and full_url != source_url:
                    urls.append(full_url)
    elif "vfsa.org.vn" in source_url:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(kw in href for kw in ["/news", "/activities", "/resources", ".html"]):
                full_url = urljoin("https://vfsa.org.vn", href)
                if full_url not in urls and full_url != source_url and "vfsa.org.vn" in full_url:
                    urls.append(full_url)
    elif "customs.gov.vn" in source_url:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and "customs.gov.vn" in href:
                if href not in urls:
                    urls.append(href)
            elif href.startswith("/") and len(href) > 5:
                full_url = urljoin("https://www.customs.gov.vn", href)
                if full_url not in urls:
                    urls.append(full_url)
    else:
        urls = [source_url]

    print(f"  [{source['name']}] URL 추출 완료 → {len(urls)}개 발견")
    return urls[:limit]


B2B_SYSTEM_PROMPT = """너는 베트남에 한국 식품(소스·시즈닝·코인육수)을 수출하는 기업의 법무·전략 분석가야.
이 텍스트는 베트남 정부 공식 포털 또는 물류·법규 사이트에서 가져온 원문이야.

[지시 사항]
1. 수출 기업 입장에서 알아야 할 핵심을 한국어로 3줄 요약해 (- 로 시작).
2. 아래 내용이 조금이라도 언급되면 반드시 포함해:
   - 식품 수입·통관·라벨링·위생 기준
   - 관세율·HS코드·수입 절차
   - 식품 안전·리콜·첨가물 기준
   - 광고·마케팅 규제
   - 무역·수출입 정책 변화
   - 소스, 시즈닝, 코인육수가 아니더라고 식품 관련 법령·정책·시장 변화
3. 수치 정보(세율, 기준치 등)가 있으면 HTML <table> 태그로 정리해.
4. 'SKIP'은 완전히 무관한 내용(순수 정치·군사·스포츠)일 때만 써. 하지만 만약에 정치, 군사 같은 경우 국제 외교와 관련해서 식품 등 법령에 영향을 준다면 그건 skip 하지 말고 핵심 요약에 포함해.
   애매하면 SKIP 하지 말고 요약해."""

B2B_USER_TEMPLATE = """[수집된 원문 내용]
{body}

위 내용을 바탕으로 수출 기업용 마케팅 부서에서 알아야 할 핵심 내용을 3줄로 요약하고, 필요한 경우 상세 수치 표를 작성해 주세요.
만약 너무 많이 포함되어 있거나 관련 정보가 없다면, 반드시 'SKIP'이라고만 출력해 주세요."""


def b2b_summarize(body: str, url: str, source_name: str) -> dict | None:
    if not body.strip():
        return None
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": B2B_SYSTEM_PROMPT},
                {"role": "user",   "content": B2B_USER_TEMPLATE.format(body=body)},
            ],
            max_tokens=600,
            temperature=0.2,
        )
        result = resp.choices[0].message.content.strip()
        if result.upper().startswith("SKIP"):
            print(f"    → SKIP (B2B): {url[:60]}")
            return None
        print(f"    → ✅ 선택 (B2B): {url[:60]}")
        return {"source": source_name, "url": url, "summary": result}
    except Exception as e:
        print(f"    [OpenAI B2B 오류] {e}")
        return None


B2B_FALLBACK_PROMPT = """너는 베트남에 한국 식품을 수출하는 기업의 전략 분석가야.
아래는 베트남 비즈니스·경제 뉴스야. 수출 기업 관점에서 유용한 인사이트를 한국어로 작성해.

[분석 관점]
- 베트남 경제·소비 환경·물가 변화
- 무역·물류·통관·관세 관련 내용
- 식품·소비재·유통 시장 변화
- 규정·법령·정책 변화 (무역·식품·소비자 관련)
- 시장 기회 또는 리스크

[형식]
- 로 시작하는 한국어 3줄 이내 요약. 수치가 있으면 반드시 포함.
SKIP 기준: 연예·스포츠 결과·군사·정치(무역·식품과 전혀 무관한 경우만)"""


def b2b_fallback_summarize(body: str, url: str, source_name: str) -> dict | None:
    if not body.strip():
        return None
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": B2B_FALLBACK_PROMPT},
                {"role": "user",   "content": B2B_USER_TEMPLATE.format(body=body)},
            ],
            max_tokens=400,
            temperature=0.2,
        )
        result = resp.choices[0].message.content.strip()
        if result.upper().startswith("SKIP"):
            print(f"    → SKIP(폴백B2B): {url[:60]}")
            return None
        print(f"    → ✅ 선택(폴백B2B): {url[:60]}")
        return {"source": source_name, "url": url, "summary": result}
    except Exception as e:
        print(f"    [OpenAI 폴백B2B 오류] {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# 6. 전체 파이프라인 실행 함수
# ══════════════════════════════════════════════════════════════════

def run_b2c_pipeline(target_per_source: int = 5) -> list[dict]:
    all_results: list[dict] = []
    for source in SOURCES:
        print(f"\n{'='*55}")
        print(f"[{source['flag']} {source['name']}] B2C 수집 시작")
        print(f"{'='*55}")
        collector = URL_COLLECTORS.get(source["type"])
        if not collector:
            print(f"  알 수 없는 타입: {source['type']}")
            continue
        urls = collector(source)
        if not urls:
            print(f"  URL 수집 실패, 다음 사이트로 이동")
            continue
        site_results = []
        for i, url in enumerate(urls[:target_per_source]):
            print(f"  [{i+1}/{len(urls[:target_per_source])}] 스크래핑: {url[:65]}")
            body = scrape_article_body(url, source["name"], max_chars=2000)
            if len(body) < 80:
                print(f"    → 본문 너무 짧음, 건너뜀")
                continue
            result = b2c_filter_and_summarize(body, url, source["name"])
            if result:
                result["flag"] = source["flag"]
                site_results.append(result)
            time.sleep(0.6)
        print(f"  → [{source['name']}] 최종 {len(site_results)}개 선택")
        all_results.extend(site_results)

    # ── 폴백: 결과 3개 미만이면 인기 뉴스 소스로 보충 ──────────
    if len(all_results) < 3:
        print(f"\n{'='*55}")
        print(f"[폴백] 기사 {len(all_results)}개 — 인기 뉴스 소스로 보충 시작")
        print(f"{'='*55}")
        for source in FALLBACK_B2C_SOURCES:
            if len(all_results) >= 8:
                break
            urls = collect_urls_rss(source)
            for url in urls:
                if len(all_results) >= 8:
                    break
                body = scrape_article_body(url, source["name"], max_chars=2000)
                if len(body) < 80:
                    continue
                result = b2c_fallback_summarize(body, url, source["name"])
                if result:
                    result["flag"] = source["flag"]
                    all_results.append(result)
                time.sleep(0.5)
        print(f"[폴백] B2C 보충 완료: 총 {len(all_results)}개")

    print(f"\n{'='*55}")
    print(f"B2C 파이프라인 완료: 총 {len(all_results)}개 기사")
    return all_results


def run_b2b_pipeline() -> list[dict]:
    all_results: list[dict] = []
    for source in GOV_SOURCES:
        print(f"\n{'='*55}")
        print(f"[{source['flag']} {source['name']}] B2B 수집 시작")
        print(f"{'='*55}")
        urls = collect_gov_article_urls(source)
        if not urls:
            print(f"  URL 수집 실패, 다음 소스로 이동")
            continue
        site_results = []
        for i, url in enumerate(urls[: source["max"]]):
            print(f"  [{i+1}/{len(urls[:source['max']])}] 스크래핑: {url[:65]}")
            body = scrape_article_body(url, source["name"], max_chars=2500)
            if len(body) < 80:
                print(f"    → 본문 너무 짧음, 건너뜀")
                continue
            result = b2b_summarize(body, url, source["name"])
            if result:
                result["flag"] = source["flag"]
                site_results.append(result)
            time.sleep(0.6)
        print(f"  → [{source['name']}] 최종 {len(site_results)}개 선택")
        all_results.extend(site_results)

    # ── 폴백: 결과 2개 미만이면 비즈니스·식품무역 뉴스로 보충 ──
    if len(all_results) < 2:
        print(f"\n{'='*55}")
        print(f"[폴백] 법령 기사 {len(all_results)}개 — 비즈니스 뉴스로 보충 시작")
        print(f"{'='*55}")
        for source in FALLBACK_B2B_SOURCES:
            if len(all_results) >= 6:
                break
            urls = collect_urls_rss(source)
            for url in urls:
                if len(all_results) >= 6:
                    break
                body = scrape_article_body(url, source["name"], max_chars=2500)
                if len(body) < 80:
                    continue
                result = b2b_fallback_summarize(body, url, source["name"])
                if result:
                    result["flag"] = source["flag"]
                    all_results.append(result)
                time.sleep(0.5)
        print(f"[폴백] B2B 보충 완료: 총 {len(all_results)}개")

    print(f"\n{'='*55}")
    print(f"B2B 파이프라인 완료: 총 {len(all_results)}개 기사")
    return all_results


# ══════════════════════════════════════════════════════════════════
# 7. Tab 3 — SEO 키워드 분석 파이프라인
# ══════════════════════════════════════════════════════════════════

def collect_seo_rss() -> list[dict]:
    """Google Trends RSS → 베트남어 원문만 반환 (번역 없음)"""
    print("  [SEO-1] Google Trends RSS 수집...")
    try:
        feed = feedparser.parse(
            "https://trends.google.com/trending/rss?geo=VN",
            agent=HEADERS["User-Agent"],
        )
        results = []
        for entry in feed.entries[:20]:
            traffic = getattr(entry, "ht_approx_traffic", "N/A")
            results.append({
                "keyword": entry.title,
                "traffic": traffic,
                "source":  "RSS",
            })
        print(f"  [SEO-1] RSS → {len(results)}개 수집")
        return results
    except Exception as e:
        print(f"  [SEO-1] RSS 실패: {e}")
        return []


def collect_seo_serpapi(keywords_vn: list[str]) -> list[dict]:
    """SerpAPI 연관 키워드 수집 → DeepL 배치 번역으로 keyword_ko 생성"""
    key = os.getenv("SERPAPI_KEY", "").strip()
    if not key:
        print("  [SEO-2] SERPAPI_KEY 없음, 건너뜀")
        return []
    print(f"  [SEO-2] SerpAPI 수집... ({len(keywords_vn)}개 키워드)")
    results = []
    for seed in keywords_vn[:5]:
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={
                    "engine":    "google_trends",
                    "q":         seed,
                    "geo":       "VN",
                    "data_type": "RELATED_QUERIES",
                    "api_key":   key,
                },
                timeout=30,
                verify=False,
            )
            resp.raise_for_status()
            data = resp.json()

            batch_kws   = []
            batch_items = []
            for qtype in ("top", "rising"):
                for item in data.get("related_queries", {}).get(qtype, [])[:8]:
                    kw = item.get("query", "")
                    if not kw:
                        continue
                    entry = {
                        "keyword":    kw,
                        "keyword_ko": "",
                        "value":      str(item.get("value", 0)),
                        "type":       qtype,
                        "seed":       seed,
                        "source":     "SerpAPI",
                    }
                    batch_kws.append(kw)
                    batch_items.append(entry)

            # DeepL 배치 번역 (API 1회)
            if batch_kws:
                try:
                    translated = deepl_translator.translate_text(
                        batch_kws, source_lang="VI", target_lang="KO"
                    )
                    trans_list = translated if isinstance(translated, list) else [translated]
                    for entry, t in zip(batch_items, trans_list):
                        entry["keyword_ko"] = t.text.strip()
                except Exception as te:
                    print(f"  [SEO-2] DeepL 배치 번역 실패 ({seed}): {te}")
                    for entry in batch_items:
                        entry["keyword_ko"] = entry["keyword"]

            results.extend(batch_items)
            time.sleep(1)

        except Exception as e:
            print(f"  [SEO-2] SerpAPI 오류 ({seed}): {e}")

    print(f"  [SEO-2] SerpAPI → {len(results)}개 수집")
    return results


SEO_SYSTEM_PROMPT = """너는 베트남 시장에 한국 식품(소스·시즈닝·코인육수)을 수출하는 마케터야.
주요 타겟은 베트남 20-30대와 주부야.

아래 SEO 데이터를 분석해서 마케팅에 실질적으로 쓸 수 있는 인사이트를 한국어로 작성해.

★ 반드시 지킬 규칙:
1. 아래 어느 하나라도 해당하면 분석 대상에 포함해:
   - 식품·요리·음식·레시피·배달·외식 관련
   - 라이프스타일·홈쿠킹·건강·다이어트·뷰티 관련
   - 엔터테인먼트·드라마·K-콘텐츠·SNS·인플루언서 관련 (콘텐츠 협업 기회)
   - 쇼핑·소비·경제·생활비·절약 관련
   - 계절·날씨·명절·이벤트 관련 (시즌 마케팅 기회)
   - 20-30대 또는 주부 타겟층이 관심 가질 만한 모든 트렌드
2. 명확히 무관한 키워드(순수 스포츠 경기결과·군사·정치·사건사고)는 제외하되, 소비심리나 외식 트렌드에 영향을 줄 수 있다면 포함해
3. 연관성이 약해 보여도 마케팅 관점에서 연결 가능하면 적극적으로 포함해. 환각·거짓말 금지.
4. 최대한 많은 키워드를 활용해 풍부하게 작성해. "관련 트렌드 없음" 응답은 진짜 아무것도 없을 때만.

[트렌드 요약]
- 오늘 베트남에서 주목할 만한 검색 트렌드 2~3줄 요약 (폭넓게)

[주목 키워드]
- 키워드1 : 마케팅 활용 방안
- 키워드2 : 마케팅 활용 방안
- 키워드3 : 마케팅 활용 방안
(최소 3개 이상, 가능하면 5개까지)

[마케팅 제안]
- 위 데이터를 바탕으로 당장 실행 가능한 구체적 제안 2~3줄"""

SEO_USER_TEMPLATE = """[Google Trends RSS — 베트남 오늘 실시간 인기 검색어]
{rss_data}

[제품 관련 연관 검색어 (SerpApi)]
{related_data}

위 데이터 전체를 폭넓게 검토해서 마케팅 인사이트를 작성해.
식품·소비·라이프스타일뿐 아니라 엔터테인먼트·SNS·쇼핑·계절 이벤트까지 마케팅 기회로 연결될 수 있는 모든 키워드를 활용해.
주목 키워드는 최소 3개 이상 뽑아줘."""


def run_seo_pipeline(input_keywords: list[str] | None = None) -> dict:
    # ① RSS 수집
    rss_trends = collect_seo_rss()

    # ② 시드 키워드 준비
    keywords_vn = []
    if input_keywords:
        print(f"  [SEO] 직원 입력 키워드: {input_keywords}")
        try:
            joined = "\n".join(input_keywords)
            translated = deepl_translator.translate_text(joined, source_lang="KO", target_lang="VI")
            keywords_vn = [l.strip() for l in translated.text.split("\n") if l.strip()]
            print(f"  [SEO] 베트남어 변환: {keywords_vn}")
        except Exception as e:
            print(f"  [SEO] 키워드 번역 실패: {e}")
            keywords_vn = input_keywords
    else:
        keywords_vn = SEO_SEED_KEYWORDS  # 전체 5개 사용

    # ③ SerpAPI 연관 키워드 수집
    related_kws = collect_seo_serpapi(keywords_vn)

    # ④ 데이터 소스 목록
    data_sources = []
    if rss_trends:
        data_sources.append("Google Trends RSS")
    if related_kws:
        data_sources += list({kw["source"] for kw in related_kws})

    # ⑤ OpenAI 인사이트용 텍스트 구성
    rss_text = "\n".join(
        f"- {t['keyword']} (검색량: {t['traffic']})" for t in rss_trends[:15]
    ) or "수집 실패"

    if related_kws:
        grouped: dict[str, list] = {}
        for kw in related_kws:
            grouped.setdefault(kw.get("seed", "기타"), []).append(kw)
        lines = []
        for seed, kws in grouped.items():
            lines.append(f"▶ '{seed}' 연관 검색어:")
            for kw in kws[:8]:
                tag = "급상승🔥" if kw["type"] == "rising" else "인기⭐"
                ko  = f" / {kw['keyword_ko']}" if kw.get("keyword_ko") and kw["keyword_ko"] != kw["keyword"] else ""
                lines.append(f"  [{tag}] {kw['keyword']}{ko} (연관도: {kw['value']})")
        related_text = "\n".join(lines)
    else:
        related_text = "수집 실패 또는 관련 데이터 없음"

    # ⑥ OpenAI 인사이트 생성 (반드시 마지막)
    insight = "데이터 수집 실패로 인사이트를 생성하지 못했습니다."
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SEO_SYSTEM_PROMPT},
                {"role": "user",   "content": SEO_USER_TEMPLATE.format(
                    rss_data=rss_text, related_data=related_text
                )},
            ],
            max_tokens=600,
            temperature=0.2,
        )
        insight = resp.choices[0].message.content.strip()
        print(f"  [SEO] OpenAI 인사이트 생성 완료")
    except Exception as e:
        print(f"  [SEO] OpenAI 오류: {e}")

    print(f"  [SEO] 완료 — 사용 소스: {data_sources}")

    # 반환 순서 고정: rss_trends → related_kws → data_sources → insight
    return {
        "rss_trends":   rss_trends,
        "related_kws":  related_kws,
        "data_sources": data_sources,
        "insight":      insight,
        "keywords_vn":  keywords_vn,
    }


# ══════════════════════════════════════════════════════════════════
# 8. FastAPI 엔드포인트
# ══════════════════════════════════════════════════════════════════

class TranslateRequest(BaseModel):
    text: str


@router.post("/fetch", tags=["C-뉴스요약"])
async def api_fetch():
    """Tab 1 — B2C 베트남 소비 트렌드 뉴스 수집"""
    global _news_cache
    try:
        _news_cache = run_b2c_pipeline(target_per_source=5)
        return {"success": True, "count": len(_news_cache), "articles": _news_cache}
    except Exception as e:
        print(f"[B2C 파이프라인 오류] {e}")
        return {"success": False, "error": str(e)}


@router.post("/fetch-gov", tags=["C-뉴스요약"])
async def api_fetch_gov():
    """Tab 2 — B2B 베트남 정부·법규 데이터 수집"""
    global _gov_cache
    try:
        _gov_cache = run_b2b_pipeline()
        return {"success": True, "count": len(_gov_cache), "gov_articles": _gov_cache}
    except Exception as e:
        print(f"[B2B 파이프라인 오류] {e}")
        return {"success": False, "error": str(e)}


@router.post("/news/translate", tags=["C-뉴스요약"])
async def translate(req: TranslateRequest):
    """Tab 1 전용 — DeepL 번역 (베트남어 → 한국어)"""
    text = req.text.strip()
    if not text:
        return {"success": False, "error": "텍스트가 비어있습니다."}
    try:
        result = deepl_translator.translate_text(text, source_lang="VI", target_lang="KO")
        return {"success": True, "translated": result.text}
    except deepl.DeepLException as e:
        return {"success": False, "error": f"DeepL 오류: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


class SeoRequest(BaseModel):
    keywords: list[str] = []


@router.post("/fetch-seo", tags=["C-뉴스요약"])
async def api_fetch_seo(req: SeoRequest = SeoRequest()):
    """Tab 3 — SEO 키워드 분석 (직원 한글 키워드 입력 가능)"""
    global _seo_cache
    try:
        keywords = [k.strip() for k in req.keywords if k.strip()] or None
        _seo_cache = run_seo_pipeline(input_keywords=keywords)
        return {"success": True, "data": _seo_cache}
    except Exception as e:
        print(f"[SEO 파이프라인 오류] {e}")
        return {"success": False, "error": str(e)}


class SeoTranslateRequest(BaseModel):
    keywords: list[str]


@router.post("/seo/translate", tags=["C-뉴스요약"])
async def api_seo_translate(req: SeoTranslateRequest):
    """Tab 3 전용 — RSS 키워드 DeepL 번역 버튼 (베트남어 → 한국어)"""
    if not req.keywords:
        return {"success": False, "error": "키워드가 비어있습니다."}
    try:
        results = []
        for kw in req.keywords:
            try:
                r = deepl_translator.translate_text(kw, source_lang="VI", target_lang="KO")
                results.append({"original": kw, "translated": r.text.strip()})
            except Exception:
                results.append({"original": kw, "translated": kw})
        return {"success": True, "translations": results}
    except deepl.DeepLException as e:
        return {"success": False, "error": f"DeepL 오류: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/news", tags=["C-뉴스요약"])
async def api_news_compat():
    """news.html 호환용"""
    global _news_cache
    try:
        _news_cache = run_b2c_pipeline(target_per_source=5)
        issues = [
            {
                "title_ko":   item.get("title_ko") or item.get("summary", "")[:40],
                "summary_ko": item.get("summary", ""),
                "source":     item.get("source", ""),
                "url":        item.get("url", ""),
                "date":       item.get("date", "방금 전"),
            }
            for item in _news_cache
        ]
        return {"issues": issues, "seo_tips": []}
    except Exception as e:
        return {"issues": [], "seo_tips": [], "error": str(e)}


@router.get("/news/cache", tags=["C-뉴스요약"])
async def api_news_cache():
    """대시보드용 — JSON 파일 캐시에서 뉴스 반환 (새로 수집 안 함, 빠름)"""
    try:
        cache_path = Path("data/news_cache.json")
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            issues = [
                {
                    "title_ko":   item.get("title_ko") or item.get("summary", "")[:40],
                    "summary_ko": item.get("summary", ""),
                    "source":     item.get("source", ""),
                    "url":        item.get("url", ""),
                    "date":       item.get("date", ""),
                }
                for item in cached[:5]
            ]
            return {"issues": issues, "cached": True}
        issues = [
            {
                "title_ko":   item.get("title_ko") or item.get("summary", "")[:40],
                "summary_ko": item.get("summary", ""),
                "source":     item.get("source", ""),
                "url":        item.get("url", ""),
                "date":       item.get("date", ""),
            }
            for item in _news_cache[:5]
        ]
        return {"issues": issues, "cached": False}
    except Exception as e:
        return {"issues": [], "error": str(e)}


@router.get("/news/trending", tags=["C-뉴스요약"])
async def api_news_trending():
    """대시보드용 — 베트남 Google Trends 실시간 검색어 (RSS만, 빠름)"""
    try:
        feed = feedparser.parse(
            "https://trends.google.com/trending/rss?geo=VN",
            agent=HEADERS["User-Agent"],
        )
        keywords = []
        for entry in feed.entries[:10]:
            traffic = getattr(entry, "ht_approx_traffic", "N/A")
            keywords.append({"keyword": entry.title, "traffic": traffic})
        return {"keywords": keywords}
    except Exception as e:
        print(f"[trending RSS 실패] {e}")
        return {"keywords": [], "error": str(e)}


# ══════════════════════════════════════════════════════════════════
# 9. 뉴스 캐시 자동 저장 (6시간 주기)
# ══════════════════════════════════════════════════════════════════

def _save_news_to_file():
    global _news_cache
    try:
        print("\n[⏰ 스케줄러] 뉴스 자동 수집 시작...")
        _news_cache = run_b2c_pipeline(target_per_source=5)
        try:
            texts = [item.get("summary", "")[:60] for item in _news_cache]
            if texts:
                result = deepl_translator.translate_text(texts, target_lang="KO", source_lang=None)
                translations = [r.text for r in result] if isinstance(result, list) else [result.text]
                for item, trans in zip(_news_cache, translations):
                    item["title_ko"] = trans
        except Exception as e:
            print(f"[DeepL 배치 번역 실패] {e}")
            for item in _news_cache:
                if "title_ko" not in item:
                    item["title_ko"] = item.get("summary", "")[:40]
        Path("data").mkdir(exist_ok=True)
        Path("data/news_cache.json").write_text(
            json.dumps(_news_cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("✅ news_cache.json 저장 완료")
    except Exception as e:
        print(f"[뉴스 캐시 저장 실패] {e}")


try:
    from apscheduler.schedulers.background import BackgroundScheduler
    news_scheduler = BackgroundScheduler()
    news_scheduler.add_job(func=_save_news_to_file, trigger="interval", hours=6)
    news_scheduler.start()
    print("✅ 뉴스 자동 수집 스케줄러 시작 (6시간 주기)")
except Exception as e:
    print(f"[스케줄러 시작 실패] {e}")
