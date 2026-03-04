# C파트 — 뉴스 요약 AI 프롬프트
> 이 파일의 내용을 MASTER_PROMPT.md 아래에 붙여넣어서 AI에게 전달하세요.

---

## 📋 AI에게 붙여넣을 내용

```
[C파트 — 뉴스 요약 작업]

내가 구현해야 할 파일:
- routers/news_summary.py  (API 로직)
- templates/b2b/news.html  (화면 — 이미 뼈대 있음, {% block content %} 안만 수정 가능)

[HTML이 기대하는 API 명세]
POST /api/news
- 입력: 없음 (body 없이 호출)
- 출력: {
    "issues": [
      {
        "title": "원문 제목",
        "title_ko": "한국어 번역",
        "summary_ko": "한국어 요약 2-3줄",
        "source": "VnExpress",
        "date": "2025-01-15",
        "url": "https://..."
      }
    ],
    "seo_tips": [
      { "keyword": "추천 키워드", "reason": "추천 이유" }
    ]
  }

[데이터 수집 방법 — 우선순위 순서]
1순위: feedparser로 베트남 뉴스 RSS 수집
  - VnExpress 식품 RSS: https://vnexpress.net/rss/kinh-doanh.rss
  - Tuoi Tre: https://tuoitre.vn/rss/kinh-doanh.rss
2순위: httpx로 직접 크롤링 (RSS 없을 때)

[OpenAI 처리 흐름]
뉴스 원문(베트남어) → GPT-4o-mini로 한국어 번역+요약 → SEO 키워드 추천

[SEO 추천 프롬프트 힌트]
"위 뉴스들을 분석해서 K-푸드 소스 브랜드가 베트남에서 사용하면 좋을
SEO 검색 키워드 3-5개를 추천하고 이유를 한국어로 설명해줘."

[화면 수정 시 규칙]
- templates/b2b/news.html 에서 {% block content %} ~ {% endblock %} 안만 수정 가능
- {% extends "base_b2b.html" %} 줄은 절대 삭제하지 않는다
- CSS 클래스명에 .c- prefix 사용 (예: .c-news-card, .c-news-title)

이제 routers/news_summary.py 를 완성해줘.
```

---

## 📁 C파트 담당 파일

| 파일 | 상태 | 할 일 |
|------|------|--------|
| `routers/news_summary.py` | 뼈대만 있음 | **핵심 작업 위치** |
| `templates/b2b/news.html` | 뼈대 있음 | `{% block content %}` 안만 수정 가능 |
| `static/css/portal.css` | 공용 | `.c-` prefix로 스타일 추가 가능 |

## ⚠️ C파트 주의사항
- `base_b2b.html` 수정 금지
- HTML의 `switchTab()`, `loadNews()` 함수는 이미 있으므로 이름 겹치지 않게 주의
- RSS 크롤링은 외부 서버에 부담 주지 않도록 결과를 캐싱 권장 (간단하게는 딕셔너리 변수에 저장)
