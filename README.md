# ★ Three Star (쓰리스타) — 프로젝트 구조 & 로직 문서

> **작성일**: 2026-03-04
> **버전**: main_8_fix1 (자사몰 통합 완료)
> **스택**: FastAPI · Jinja2 · ChromaDB · OpenAI · Render.com 배포

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [폴더 트리](#2-폴더-트리)
3. [라우팅 구조](#3-라우팅-구조)
4. [인증 미들웨어](#4-인증-미들웨어)
5. [템플릿 상속 구조](#5-템플릿-상속-구조)
6. [JS 파일 사용처](#6-js-파일-사용처)
7. [챗봇 동작 흐름](#7-챗봇-동작-흐름)
8. [자사몰 홈 (index.html) 특이사항](#8-자사몰-홈-indexhtml-특이사항)
9. [이번 작업 내역 (main_8_fix1)](#9-이번-작업-내역-main_8_fix1)
10. [Render 배포 시 주의사항](#10-render-배포-시-주의사항)

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 서비스명 | 쓰리스타 (Three Star) / Da-Mi Food |
| 대상 시장 | 베트남 K-푸드 자사몰 + 직원 인트라넷 |
| 언어 지원 | 한국어 · English · Tiếng Việt (3개국어) |
| 주요 기능 | B2C 자사몰 · B2B 직원 포탈 · AI 레시피 챗봇 · 뉴스 요약 · 리뷰 분석 · SNS 생성 · 유통망 지도 |

### 두 개의 독립된 사이트

```
[B2C 자사몰]  /              → 일반 소비자용
[B2B 포탈]   /portal/login  → 직원 전용 (로그인 필요)
```

---

## 2. 폴더 트리

```
3star_main_8_fix1/
│
├── main.py                          ← FastAPI 앱 진입점 / 전체 라우트 정의
├── render.yaml                      ← Render.com 배포 설정
├── requirements.txt                 ← Python 패키지 목록
├── .env                             ← 환경변수 (API 키 등, git 제외)
│
├── routers/                         ← 기능별 API 라우터
│   ├── auth.py                      ← 직원 로그인/로그아웃 (세션 기반)
│   ├── contact.py                   ← B2C 문의 폼 처리
│   ├── recipe_chatbot.py            ← 챗봇 API (RAG + AI 응답)
│   ├── recipe_admin.py              ← 챗봇 관리자 API (rate limit 적용)
│   ├── recipe_analytics.py          ← 챗봇 사용 통계 API
│   ├── news_summary.py              ← 뉴스 요약 API
│   ├── review_keyword.py            ← 리뷰 키워드 분석 API
│   ├── sns_generator.py             ← SNS 콘텐츠 생성 API
│   ├── market_map.py                ← 유통망 지도 API
│   ├── ideas.py                     ← 아이디어 게시판 API
│   └── search.py                    ← 통합 검색 API
│
├── services/                        ← 비즈니스 로직 / AI 서비스 레이어
│   ├── recipe_ai.py                 ← 레시피 AI 생성 (OpenAI)
│   ├── recipe_search.py             ← RAG 벡터 검색 (ChromaDB)
│   ├── chatbot_graph.py             ← 챗봇 대화 흐름 그래프
│   ├── analytics.py                 ← 챗봇 사용 로그 집계
│   ├── openai_api.py                ← OpenAI API 래퍼
│   ├── output_guardrail.py          ← 챗봇 출력 안전 필터
│   ├── image_ai.py                  ← 레시피 이미지 AI 생성
│   ├── image_generator.py           ← 이미지 생성 관리
│   ├── ingredient_search.py         ← 재료 기반 레시피 검색
│   ├── init_vectordb.py             ← ChromaDB 초기화 스크립트
│   ├── admin_auth.py                ← 관리자 인증 로직
│   ├── pdf_maker.py                 ← 주간 리포트 PDF 생성
│   ├── web_scraper.py               ← K-푸드 뉴스 스크래핑
│   └── youtube_api.py               ← YouTube 연동
│
├── templates/
│   ├── base_b2c.html                ← B2C 공통 레이아웃 (PM 전용 파일)
│   │                                   navbar · 장바구니 모달 · 챗봇 FAB · footer
│   │                                   cart.js + main.js + chatbot-float.js 로드
│   ├── base_b2b.html                ← B2B 공통 레이아웃 (PM 전용 파일)
│   │                                   포탈 사이드바 · 헤더 · portal.js 로드
│   ├── b2c/
│   │   ├── index.html               ★ 자사몰 홈 SPA (독립형 — base_b2c 상속 없음)
│   │   │                               3개국어 · 자체 장바구니 · 제품 모달 · 챗봇 FAB 직접 포함
│   │   ├── company.html             ← base_b2c 상속
│   │   ├── product.html             ← base_b2c 상속 · products.json 데이터 주입
│   │   ├── contact.html             ← base_b2c 상속
│   │   └── chatbot.html             ← base_b2c 상속 · 전페이지 챗봇 UI
│   └── b2b/
│       ├── login.html               ← 직원 로그인 페이지 (base_b2b 상속 없음)
│       ├── dashboard.html           ← 포탈 메인 대시보드
│       ├── news.html                ← 뉴스 요약 페이지
│       ├── review.html              ← 리뷰 키워드 분석
│       ├── sns.html                 ← SNS 콘텐츠 생성
│       ├── map.html                 ← 유통망 지도 (Google Maps 연동)
│       ├── ideas.html               ← 아이디어 게시판
│       ├── customers.html           ← 고객 관리
│       └── report.html              ← 주간 리포트 (PDF 다운로드)
│
├── static/
│   ├── css/
│   │   ├── style.css                ← B2C 전용 CSS + 챗봇 플로팅 위젯 CSS
│   │   └── portal.css               ← B2B 포탈 전용 CSS
│   ├── js/
│   │   ├── chatbot-float.js         ← 플로팅 챗봇 위젯 로직 (905줄)
│   │   │                               모든 B2C 페이지에서 공통 사용
│   │   ├── chatbot-widget.js        ← /chatbot 전용 페이지 로직
│   │   ├── cart.js                  ← B2C 장바구니 (base_b2c 상속 페이지 전용)
│   │   ├── main.js                  ← B2C 기본 JS (base_b2c 상속 페이지 전용)
│   │   └── portal.js                ← B2B 포탈 전용 JS
│   ├── images/
│   │   ├── brand/                   ← 로고 · 배너 · 배경 · 용담이 GIF 등
│   │   │   ├── logo.png / logo.jpg
│   │   │   ├── yongdamiicon.gif     ← 챗봇 FAB 아이콘
│   │   │   ├── yongdami_thinking.gif ← 챗봇 웰컴 화면
│   │   │   ├── yongdami_cooking.gif
│   │   │   ├── yongdami_eating.gif
│   │   │   ├── 로고.png
│   │   │   ├── 배너 영상_최최종.mp4
│   │   │   ├── 배너_청양마요_월남쌈.png
│   │   │   ├── 배너_쌀국수_매실피시.png
│   │   │   ├── 배너_전복죽.png
│   │   │   ├── 배너_가족.png
│   │   │   ├── 홈페이지배경.png
│   │   │   └── ... (브랜드 이미지 전체)
│   │   ├── products/
│   │   │   ├── 소스 라인업.png      ★ 신규 추가
│   │   │   ├── 시즈닝 라인업.png    ★ 신규 추가
│   │   │   ├── 코인육수 라인업.png  ★ 신규 추가
│   │   │   ├── 소스/               ★ 신규 폴더 (18개 파일)
│   │   │   │   ├── 청양마요_2.png
│   │   │   │   ├── 청양마요_nutrition_facts.png
│   │   │   │   ├── 청양 라벨.png
│   │   │   │   └── ... (소스 제품 이미지)
│   │   │   ├── 시즈닝/             ★ 신규 폴더 (17개 파일)
│   │   │   │   ├── 감자탕_상품페이지.png
│   │   │   │   ├── MYOMI스틱_감자탕_소포장.png
│   │   │   │   └── ... (시즈닝 제품 이미지)
│   │   │   └── 코인육수/           ★ 신규 폴더 (16개 파일)
│   │   │       ├── 육개장.png
│   │   │       ├── 멸치 육수.png
│   │   │       └── ... (코인육수 제품 이미지)
│   │   └── recipes/                 ← AI 생성 레시피 이미지 (~80개 .png)
│   └── pdfs/                        ← 주간 리포트 PDF 저장소
│
├── data/
│   ├── products.json                ← 전 제품 데이터 (B2B /product 페이지용)
│   ├── admins.json                  ← 직원 계정 목록 (로그인 인증용)
│   ├── system_prompt.txt            ← 챗봇 시스템 프롬프트
│   ├── translations.json            ← 다국어 번역 데이터
│   ├── markets.json                 ← 유통망 지도 마커 데이터
│   ├── ideas.json                   ← 아이디어 게시판 데이터
│   ├── competitor_history.xlsx      ← 리뷰 키워드 히스토리
│   ├── recipes/                     ← 레시피 마크다운 파일 (~80개)
│   ├── product_details/             ← 제품별 상세 MD (챗봇 RAG 소스)
│   │   ├── coin_01.md ~ coin_04.md
│   │   ├── sauce_01.md ~ sauce_06.md
│   │   ├── season_01.md ~ season_04.md
│   │   └── food_01.md ~ food_02.md
│   ├── cooking_tips/                ← 요리 팁 MD (챗봇 RAG 소스)
│   ├── product_comparisons/         ← 제품 비교 MD (챗봇 RAG 소스)
│   ├── chromadb/                    ← 벡터 DB (RAG 검색 인덱스, 자동 생성)
│   └── analytics/                   ← 챗봇 사용 로그 (일별 .jsonl)
│
├── prompts/                         ← 팀 작업 프롬프트 문서
└── scripts/                         ← 데이터 관리 스크립트
    ├── generate_translations.py
    ├── regenerate_all_images.py
    └── evaluate_rag.py / evaluate_ragas.py
```

---

## 3. 라우팅 구조

### B2C (자사몰)

| URL | 핸들러 | 템플릿 | 비고 |
|---|---|---|---|
| `GET /` | `home()` | `b2c/index.html` | 자사몰 홈 SPA |
| `GET /company` | `company()` | `b2c/company.html` | 브랜드 소개 |
| `GET /product` | `product()` | `b2c/product.html` | products.json 주입 |
| `GET /contact` | `contact()` | `b2c/contact.html` | 문의 폼 |
| `GET /chatbot` | `chatbot()` | `b2c/chatbot.html` | 전페이지 챗봇 |

### B2B (직원 포탈) — 모두 인증 필요

| URL | 핸들러 | 템플릿 |
|---|---|---|
| `GET /portal/login` | `auth.router` | `b2b/login.html` |
| `GET /portal` | `portal_dashboard()` | `b2b/dashboard.html` |
| `GET /portal/news` | `portal_news()` | `b2b/news.html` |
| `GET /portal/review` | `portal_review()` | `b2b/review.html` |
| `GET /portal/sns` | `portal_sns()` | `b2b/sns.html` |
| `GET /portal/map` | `portal_map()` | `b2b/map.html` |
| `GET /portal/ideas` | `portal_ideas()` | `b2b/ideas.html` |
| `GET /portal/customers` | `portal_customers()` | `b2b/customers.html` |
| `GET /portal/report` | `portal_report()` | `b2b/report.html` |

### API 엔드포인트

| Prefix | Router | 기능 |
|---|---|---|
| `/api/chat` | recipe_chatbot | 챗봇 응답 (RAG + AI) |
| `/api/news` | news_summary | 뉴스 요약 |
| `/api/review` | review_keyword | 리뷰 키워드 분석 |
| `/api/sns` | sns_generator | SNS 콘텐츠 생성 |
| `/api/market` | market_map | 유통망 지도 데이터 |
| `/api/intranet` | ideas | 아이디어 게시판 |
| `/api/exchange-rate` | main.py | 환율 정보 (1시간 캐싱) |
| `/analytics/*` | recipe_analytics | 챗봇 사용 통계 |
| `/admin/*` | recipe_admin | 챗봇 관리자 |

---

## 4. 인증 미들웨어

```
모든 요청
    │
    ▼
PortalAuthMiddleware (main.py)
    │
    ├─ 경로가 /portal/* 이고 /portal/login 이 아닌가?
    │       └─ YES → session["portal_auth"] == "authenticated" 확인
    │                   ├─ OK  → 통과
    │                   └─ NG  → 302 Redirect → /portal/login
    └─ 그 외 경로 → 그대로 통과

SessionMiddleware (Starlette)
    └─ 쿠키 기반 서버 사이드 세션
       SECRET_KEY: 환경변수 SESSION_SECRET
```

### 로그인 흐름

```
POST /portal/login
    │
    ├─ data/admins.json 에서 계정 확인
    ├─ 일치 → session["portal_auth"] = "authenticated"
    │          session["user_name"] = 이름
    │          session["user_role"] = 역할
    │          → Redirect /portal (대시보드)
    └─ 불일치 → 로그인 페이지 (오류 메시지)
```

---

## 5. 템플릿 상속 구조

```
┌─────────────────────────────────┐
│         base_b2c.html           │  ← PM 전용, 수정 금지
│  navbar · 장바구니 모달 · footer │
│  챗봇 FAB + chat-widget HTML     │
│  cart.js + main.js + chatbot-float.js 로드
└──────────┬──────────────────────┘
           │  {% extends "base_b2c.html" %}
    ┌──────┼──────────────────────┐
    │      │                      │
company  product  contact    chatbot
.html    .html    .html       .html


┌─────────────────────────────────┐
│         base_b2b.html           │  ← PM 전용, 수정 금지
│  포탈 사이드바 · 헤더            │
│  portal.css + portal.js 로드    │
└──────────┬──────────────────────┘
           │  {% extends "base_b2b.html" %}
    ┌──────┼──────────────────────────────┐
    │      │       │       │       │      │
dashboard news  review   sns    map  ideas
 .html   .html  .html  .html  .html .html


★ index.html (자사몰 홈)
   └─ 독립 SPA — base_b2c.html 상속 없음
      chatbot-float.js 만 직접 로드
      챗봇 FAB HTML 직접 포함 (base_b2c에서 이식)
      자체 장바구니 시스템 (dami_cart)
```

---

## 6. JS 파일 사용처

| 파일 | 로드 위치 | 담당 역할 |
|---|---|---|
| `chatbot-float.js` | base_b2c.html + index.html | 플로팅 챗봇 위젯 전체 로직 (905줄) · 3개국어 · 3가지 모드 |
| `cart.js` | base_b2c.html | B2C 장바구니 (`threestar_cart` localStorage) · 챗봇 연동 (`addToCartFromChatbot`) |
| `main.js` | base_b2c.html | 장바구니 카운트 업데이트 · `addToCart()` |
| `portal.js` | base_b2b.html | 포탈 UI 동작 전반 |
| `chatbot-widget.js` | b2c/chatbot.html | 전페이지 챗봇 전용 UI |
| index.html 인라인 JS | b2c/index.html 만 | 자체 장바구니 (`dami_cart`) · 다국어 전환 · 제품 모달 · 슬라이드쇼 |

### index.html 장바구니 브릿지

```javascript
// chatbot-float.js 로드 직후 삽입됨
window.addToCartFromChatbot = function(productId, qty) {
  for (var i = 0; i < (qty || 1); i++) addToCartDirect(productId);
};
// → 챗봇에서 장바구니 추가 버튼 클릭 시
//   index.html 자체 장바구니(dami_cart)에 정상 추가됨
```

---

## 7. 챗봇 동작 흐름

```
사용자 입력 (어느 B2C 페이지에서든 챗봇 FAB 클릭)
    │
    ▼
chatbot-float.js
    ├─ 언어 선택: 한국어 / Tiếng Việt / EN
    ├─ 모드 선택: 💬 대화 / 📋 가이드 / 🎲 랜덤
    │
    └─ POST /api/chat  →  routers/recipe_chatbot.py
                                   │
                          services/chatbot_graph.py
                          (LangGraph 기반 대화 흐름)
                                   │
                 ┌─────────────────┼─────────────────┐
                 ▼                 ▼                   ▼
        recipe_search.py    recipe_ai.py      output_guardrail.py
        (ChromaDB RAG)      (OpenAI 생성)     (안전 필터)
        data/recipes/*.md
        data/product_details/*.md
        data/cooking_tips/*.md
                 │
                 └─────────────────┘
                           │
                    챗봇 응답 반환 (레시피 카드 + 퀵 답장)
                           │
            "🛒 장바구니 추가" 버튼 클릭 시
                           │
                 window.addToCartFromChatbot(productId)
                           │
              ┌────────────┴──────────────┐
              │ index.html 에서            │ 다른 B2C 페이지에서
              ▼                           ▼
     addToCartDirect(id)        cart.js의 addToCartFromChatbot()
     (dami_cart localStorage)   (threestar_cart localStorage)
```

---

## 8. 자사몰 홈 (index.html) 특이사항

### 일반 B2C 페이지와의 차이점

| 항목 | 일반 B2C (company 등) | index.html |
|---|---|---|
| 템플릿 상속 | `base_b2c.html` 상속 | 독립 SPA (상속 없음) |
| Jinja2 사용 | 있음 (`{{ }}`, `{% %}`) | 없음 (순수 HTML) |
| 장바구니 | cart.js (`threestar_cart`) | 인라인 JS (`dami_cart`) |
| 챗봇 FAB | base_b2c.html에서 제공 | 직접 포함 |
| 다국어 | 서버 사이드 | 클라이언트 사이드 (JS) |
| 로드하는 JS | cart.js + main.js + chatbot-float.js | chatbot-float.js 만 |

### index.html 스크립트 로딩 순서

```html
<!-- 하단 body 직전 -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="/static/js/chatbot-float.js"></script>
<script>
  // 챗봇 → index.html 장바구니 연동 브릿지
  window.addToCartFromChatbot = function(productId, qty) {
    for (var i = 0; i < (qty || 1); i++) addToCartDirect(productId);
  };
</script>
```

### 직원용 버튼

```html
<!-- line 991 -->
<button class="staff-btn" onclick="window.location.href='/portal/login'">직원용</button>
```

---

## 9. 이번 작업 내역 (main_8_fix1)

### 작업 배경

기존 3star 프로젝트(B2B 인트라넷 + 챗봇)에 새로운 자사몰 SPA(`index.html`)와 제품 이미지를 충돌 없이 병합.

### 완료된 작업

| # | 작업 내용 | 대상 |
|---|---|---|
| 1 | 이미지 폴더 3개 생성 | `static/images/products/소스·시즈닝·코인육수/` |
| 2 | 브랜드 이미지 복사 | `static copy/images/brand/` → `static/images/brand/` |
| 3 | 제품 이미지 복사 (총 221개) | `static copy/images/products/` → `static/images/products/` |
| 4 | `cart.js` 로드 제거 | `templates/b2c/index.html` line 3245 삭제 |
| 5 | `main.js` 로드 제거 | `templates/b2c/index.html` line 3246 삭제 |
| 6 | 챗봇 장바구니 브릿지 추가 | `templates/b2c/index.html` 하단 `<script>` 블록 |

### 제거 이유 (cart.js / main.js)

두 파일이 `index.html` 자체 함수를 덮어쓰는 충돌 발생:

| 충돌 함수 | index.html 역할 | cart.js/main.js 역할 |
|---|---|---|
| `addToCart()` | 제품 모달에서 장바구니 추가 | 다른 방식의 장바구니 추가 (덮어씀) |
| `changeQty()` | 모달 내 수량 조절 | 장바구니 모달 수량 조절 (덮어씀) |
| `showToast()` | `#toast` 엘리먼트 사용 | `#toast-message` 엘리먼트 사용 (덮어씀) |

> `cart.js`, `main.js` 파일 자체는 삭제하지 않음.
> `base_b2c.html`을 상속받는 다른 B2C 페이지들은 여전히 정상 사용.

### 변경하지 않은 것

- `main.py` — 라우팅 전혀 변경 없음
- `templates/base_b2c.html` — B2C 공통 레이아웃 그대로
- `templates/base_b2b.html` — B2B 공통 레이아웃 그대로
- `templates/b2b/*` — 포탈 페이지 전체 그대로
- `routers/auth.py` — 로그인 로직 그대로
- `static/js/chatbot-float.js` — 챗봇 JS 그대로 (한 줄도 수정 없음)
- `static/css/style.css` — CSS 그대로
- `static/css/portal.css` — 포탈 CSS 그대로
- `data/` — 모든 데이터 파일 그대로
- `services/` — AI 서비스 로직 전부 그대로

---

## 10. Render 배포 시 주의사항

### 기존 버그 (배포 전 수정 필요)

`main.py` 마지막 줄:

```python
# 현재 (로컬에서만 동작)
uvicorn.run("main:app", host="127.0.0.1", port=port)

# Render 배포 시 수정 필요
uvicorn.run("main:app", host="0.0.0.0", port=port)
```

> `127.0.0.1`은 로컬 루프백 주소로, Render 서버에서 외부 트래픽을 받을 수 없음.
> `0.0.0.0`으로 변경해야 배포 후 사이트가 정상 열림.

### 필수 환경변수 (Render 대시보드에서 설정)

| 변수명 | 설명 |
|---|---|
| `SESSION_SECRET` | 세션 암호화 키 (임의의 랜덤 문자열) |
| `OPENAI_API_KEY` | OpenAI API 키 (챗봇·이미지 생성) |
| `GOOGLE_MAPS_API_KEY` | Google Maps API 키 (유통망 지도) |
| `PORT` | Render 자동 주입 (별도 설정 불필요) |

### 한국어 파일명 (이미지)

Render는 Linux 서버 (Ubuntu) 기반으로 UTF-8을 기본 지원.
한국어·공백 포함 파일명 (`배너 영상_최최종.mp4` 등) 정상 서빙됨.

---

*이 문서는 `PROJECT_STRUCTURE.md` 로 저장됩니다.*
*프로젝트 구조가 변경될 때마다 업데이트해주세요.*
