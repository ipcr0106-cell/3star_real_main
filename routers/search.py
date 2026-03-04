"""
★ 포탈 통합 검색 라우터 (search.py) ★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[엔드포인트]
  GET /api/search?q=검색어   → 포탈 내 전체 검색

[검색 대상]
  1. data/news_cache.json     → 수집된 베트남 뉴스
  2. data/competitor_history.xlsx → 리뷰 키워드 분석
  3. data/recipes/*.md        → RAG 레시피 문서

[외부 API 불필요] — 우리 서버 파일만 검색
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import re
from pathlib import Path
from fastapi import APIRouter, Query

router = APIRouter()


def _highlight(text: str, q: str) -> str:
    """검색어 앞뒤 20자 발췌 + 검색어 위치 표시"""
    text = text.strip()
    idx = text.lower().find(q.lower())
    if idx == -1:
        return text[:80] + ("..." if len(text) > 80 else "")
    start = max(0, idx - 20)
    end = min(len(text), idx + len(q) + 40)
    snippet = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")
    return snippet


@router.get("/search", tags=["검색"])
async def portal_search(q: str = Query(..., min_length=1, description="검색어")):
    """
    포탈 내 전체 검색
    - news_cache.json : 수집된 뉴스 요약
    - competitor_history.xlsx : 리뷰 분석 텍스트
    - data/recipes/*.md : 레시피 RAG 문서
    """
    q = q.strip()
    if not q:
        return {"query": q, "results": [], "total": 0}

    results = []

    # ── 1. 뉴스 캐시 검색 ──────────────────────────────
    try:
        news_path = Path("data/news_cache.json")
        if news_path.exists():
            news_data = json.loads(news_path.read_text(encoding="utf-8"))
            for item in news_data:
                summary = item.get("summary", "")
                source  = item.get("source", "")
                url     = item.get("url", "")
                if q.lower() in summary.lower() or q.lower() in source.lower():
                    results.append({
                        "type":    "news",
                        "icon":    "📰",
                        "title":   source or "베트남 뉴스",
                        "snippet": _highlight(summary, q),
                        "url":     url or "/portal/news",
                        "page":    "/portal/news",
                        "page_label": "뉴스 요약",
                    })
    except Exception as e:
        print(f"[검색-뉴스] {e}")

    # ── 2. 리뷰 Excel 검색 ─────────────────────────────
    try:
        xlsx_path = Path("data/competitor_history.xlsx")
        if xlsx_path.exists():
            import openpyxl
            wb = openpyxl.load_workbook(xlsx_path)
            ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not row[2]:
                    continue
                date_val = str(row[0]) if row[0] else ""
                cat_val  = str(row[1]) if row[1] else ""
                text_val = str(row[2])
                combined = f"{cat_val} {text_val}"
                if q.lower() in combined.lower():
                    results.append({
                        "type":    "review",
                        "icon":    "🔍",
                        "title":   f"리뷰 분석 — {cat_val}" if cat_val else "리뷰 키워드 분석",
                        "snippet": _highlight(text_val, q),
                        "url":     "/portal/review",
                        "page":    "/portal/review",
                        "page_label": "리뷰 키워드",
                        "date":    date_val[:10] if date_val else "",
                    })
    except Exception as e:
        print(f"[검색-리뷰] {e}")

    # ── 3. RAG 레시피 .md 검색 ─────────────────────────
    try:
        # 일반적인 레시피 저장 경로들 탐색
        md_dirs = [Path("data/recipes"), Path("data"), Path("static/recipes"), Path("recipes")]
        for md_dir in md_dirs:
            if not md_dir.exists():
                continue
            for md_file in md_dir.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if q.lower() in content.lower() or q.lower() in md_file.stem.lower():
                        # 첫 번째 헤딩을 제목으로
                        title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
                        title = title_match.group(1) if title_match else md_file.stem
                        results.append({
                            "type":    "recipe",
                            "icon":    "📄",
                            "title":   title,
                            "snippet": _highlight(content.replace("#", "").replace("\n", " "), q),
                            "url":     "/admin-page",
                            "page":    "/admin-page",
                            "page_label": "RAG 레시피",
                            "filename": md_file.name,
                        })
                except Exception:
                    continue
    except Exception as e:
        print(f"[검색-RAG] {e}")

    # ── 4. 포탈 페이지 정적 매핑 (항상 포함) ──────────
    PAGE_MAP = [
        {"keywords": ["뉴스", "news", "트렌드", "베트남"],   "type": "page", "icon": "🗞",  "title": "뉴스 요약 탭",    "snippet": "베트남 소비 트렌드 뉴스 및 정부 법규 요약",         "url": "/portal/news",   "page": "/portal/news",   "page_label": "뉴스 요약"},
        {"keywords": ["리뷰", "review", "키워드", "경쟁사"], "type": "page", "icon": "📊",  "title": "리뷰 키워드 분석", "snippet": "3사 경쟁사 리뷰 키워드 및 감성 분석",               "url": "/portal/review", "page": "/portal/review", "page_label": "리뷰 키워드"},
        {"keywords": ["sns", "콘텐츠", "틱톡", "tiktok"],   "type": "page", "icon": "🎬",  "title": "SNS 콘텐츠 생성", "snippet": "TikTok·Instagram 마케팅 콘텐츠 자동 생성",          "url": "/portal/sns",    "page": "/portal/sns",    "page_label": "SNS 콘텐츠"},
        {"keywords": ["지도", "map", "유통", "매장"],        "type": "page", "icon": "🗺",  "title": "유통 지도",        "snippet": "베트남 현지 유통망 및 매장 분포 지도",              "url": "/portal/map",    "page": "/portal/map",    "page_label": "유통 지도"},
        {"keywords": ["챗봇", "chatbot", "레시피", "recipe"],"type": "page", "icon": "🤖",  "title": "레시피 챗봇",      "snippet": "자사몰 AI 레시피 챗봇 — RAG 기반 응답",            "url": "/chatbot",       "page": "/chatbot",       "page_label": "레시피 챗봇"},
    ]
    for p in PAGE_MAP:
        if any(kw in q.lower() for kw in p["keywords"]):
            results.append({
                "type":       p["type"],
                "icon":       p["icon"],
                "title":      p["title"],
                "snippet":    p["snippet"],
                "url":        p["url"],
                "page":       p["page"],
                "page_label": p["page_label"],
            })

    # 중복 url 제거, 최대 15개
    seen_urls = set()
    deduped = []
    for r in results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            deduped.append(r)
    deduped = deduped[:15]

    # 타입 우선순위 정렬: news > review > recipe > page
    type_order = {"news": 0, "review": 1, "recipe": 2, "page": 3}
    deduped.sort(key=lambda x: type_order.get(x["type"], 9))

    return {
        "query":   q,
        "results": deduped,
        "total":   len(deduped),
    }