# D파트 — 리뷰 키워드 분석 AI 프롬프트
> 이 파일의 내용을 MASTER_PROMPT.md 아래에 붙여넣어서 AI에게 전달하세요.

---

## 📋 AI에게 붙여넣을 내용

```
[D파트 — 리뷰 키워드 분석 작업]

내가 구현해야 할 파일:
- routers/review_keyword.py  (API 로직)
- templates/b2b/review.html  (화면 뼈대 있음, {% block content %} 안만 수정 가능)

[HTML이 기대하는 API 명세]
POST /api/review
- 입력: { "url": "https://shopee.vn/product/..." }
- 출력: {
    "negative_keywords": [
      { "vn": "베트남어 키워드", "ko": "한국어 번역", "count": 42 }
    ],
    "positive_keywords": [
      { "vn": "베트남어 키워드", "ko": "한국어 번역", "count": 87 }
    ],
    "seo_suggestions": ["SEO 추천 문구1", "SEO 추천 문구2"]
  }

[데이터 수집 방법 — 단계별]
1단계 (MVP): 하드코딩 샘플 데이터로 UI 먼저 완성
2단계: Apify API로 Shopee/Lazada 리뷰 수집
  - Apify Actor: "drobnikj/shopee-scraper" 또는 "apify/web-scraper"
  - API 키: os.getenv("APIFY_API_KEY")
  - Apify 무료 티어: 월 $5 크레딧 (약 1,000회 요청)
3단계: services/web_scraper.py (Playwright) 직접 크롤링

[OpenAI 처리 흐름]
리뷰 원문(베트남어 텍스트 묶음)
→ GPT-4o-mini: "부정/긍정 키워드 추출 + 한국어 번역"
→ DeepL: 번역 품질 보정 (os.getenv("DEEPL_API_KEY"))

[키워드 추출 프롬프트 힌트]
"다음은 베트남 이커머스 플랫폼의 식품 리뷰들입니다.
고객이 자주 언급한 부정적인 키워드 상위 10개와
긍정적인 키워드 상위 10개를 추출해서 JSON 형식으로 반환해줘.
각 키워드는 베트남어 원문과 한국어 번역, 언급 횟수를 포함해줘."

[.env에 추가할 키]
APIFY_API_KEY=여기에_Apify_API_키

[화면 수정 시 규칙]
- CSS 클래스명에 .d- prefix 사용 (예: .d-keyword-row, .d-result-box)
- {% extends "base_b2b.html" %} 줄 절대 삭제 금지

이제 routers/review_keyword.py 를 완성해줘.
1단계(샘플 데이터)부터 구현하고, 이후 Apify 연결을 추가해줘.
```

---

## 📁 D파트 담당 파일

| 파일 | 상태 | 할 일 |
|------|------|--------|
| `routers/review_keyword.py` | 뼈대만 있음 | **핵심 작업 위치** |
| `services/web_scraper.py` | 뼈대 있음 | Playwright 크롤링 구현 |
| `templates/b2b/review.html` | 뼈대 있음 | `{% block content %}` 안만 수정 가능 |

## ⚠️ D파트 주의사항
- Apify 무료 티어 소진 주의 — 테스트할 때 샘플 URL 사용 권장
- Playwright 사용 시: `playwright install chromium` 별도 실행 필요
- DeepL 무료 티어: 월 50만 자 제한
