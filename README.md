# ★ Three Star (쓰리스타) — Da-Mi Food Tech Platform

> **버전**: main_8_fix1 → Render 배포 완료
> **배포 URL**: Render.com (Web Service)
> **스택**: FastAPI · Jinja2 · ChromaDB · OpenAI · LangGraph · Render.com

---

## 목차

1. [프로젝트 개요 및 평가항목 대응](#1-프로젝트-개요-및-평가항목-대응)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [주요 기능 상세](#3-주요-기능-상세)
4. [폴더 구조](#4-폴더-구조)
5. [라우팅 구조](#5-라우팅-구조)
6. [챗봇 동작 흐름](#6-챗봇-동작-흐름)
7. [인증 미들웨어](#7-인증-미들웨어)
8. [최근 변경사항](#8-최근-변경사항)
9. [Render 배포 가이드 (완전판)](#9-render-배포-가이드-완전판)

---

## 1. 프로젝트 개요 및 평가항목 대응

### 서비스 개요

| 항목 | 내용 |
|---|---|
| 서비스명 | 쓰리스타 (Three Star) / Da-Mi Food Tech Platform |
| 대상 시장 | 베트남 K-푸드 시장 |
| 사용자 | B2C: 베트남 현지 소비자 / B2B: 한국 수출 담당 직원 |
| 언어 지원 | 한국어 · English · Tiếng Việt |
| 배포 환경 | Render.com (Free Tier, Python 3.11.7) |

### 평가항목별 대응

#### ① 제품 선정의 합리성
- 베트남 K-푸드 시장 성장세 데이터 기반으로 **소스·시즈닝·코인육수** 3개 라인업 선정
- `data/products.json` — 카테고리별 제품 구조화 데이터 보유
- `data/competitor_history.xlsx` — 경쟁사 키워드 히스토리 누적 분석

#### ② 페인포인트 분석 및 타겟팅
| 페인포인트 | 해결 기능 |
|---|---|
| 현지 레시피 정보 부족 | AI 레시피 챗봇 (3개국어, RAG 기반 103개 문서) |
| 뉴스 수작업 모니터링 | B2B 자동 뉴스 요약 (피드 + AI 요약) |
| 경쟁사 리뷰 분석 어려움 | 유튜브/SNS 키워드 자동 분석 |
| SNS 콘텐츠 제작 공수 | AI 기반 SNS 포스트·쇼츠 기획 자동 생성 |
| 유통망 파악 어려움 | Google Maps 연동 베트남 유통망 지도 |

#### ③ AI 기술 구현 및 프롬프트
- **RAG (Retrieval-Augmented Generation)**: ChromaDB + `text-embedding-3-large`로 103개 문서 벡터화
- **LangGraph**: 챗봇 대화 흐름을 그래프 기반 상태 머신으로 관리 (`services/chatbot_graph.py`)
- **고도화 프롬프트**: `data/system_prompt.txt` — CoT(Chain-of-Thought) 및 Few-shot 예시 포함
- **멀티모달**: OpenAI 이미지 생성 API로 레시피 이미지 자동 생성
- **출력 안전 필터**: `services/output_guardrail.py` — 부적절 응답 차단

#### ④ 데이터 활용 및 실무 적합성
| 외부 API | 활용 기능 |
|---|---|
| OpenAI API | 챗봇 응답, 레시피 AI 생성, 이미지 생성 |
| YouTube Data API v3 | 베트남 먹방 트렌드 수집, 쇼츠 바이럴 분석 |
| SerpAPI | 베트남 실시간 구글 검색어 수집 |
| DeepL API | 베트남어 리뷰 키워드 한국어 번역 |
| yfinance | USD/KRW/VND 실시간 환율 (1시간 캐싱) |
| Apify | 경쟁사 리뷰 크롤링 |
| Google Maps API | 베트남 유통망 위치 정보 |

#### ⑤ 창의성 및 혁신성
- **B2C + B2B 통합 단일 플랫폼**: 소비자용 자사몰과 직원용 인트라넷을 하나의 FastAPI 앱으로 운영
- **3개국어 실시간 전환 챗봇**: 언어 변경 시 대화 맥락 유지
- **챗봇 → 장바구니 직접 연동**: 레시피 추천에서 구매까지 원스톱
- **인분 조절 인터랙티브 기능**: 챗봇 레시피 카드에서 재료 양 실시간 계산

#### ⑥ 사용자 편의성
- 3개국어 동적 전환 (페이지 리로드 없음)
- 직원 포탈: 코드 입력 방식 간편 로그인 (STAR01~STAR08)
- 챗봇 3가지 모드: 💬 대화 / 📋 가이드 / 🎲 랜덤
- 주간 리포트 PDF 자동 생성 및 다운로드
- 모바일 반응형 UI

#### ⑦ 협업 및 발표
- 파트별 역할 분리: A(자사몰) · B(챗봇) · C(뉴스) · D(리뷰) · E(SNS) · F(지도)
- `routers/` 폴더 기준 파트 독립 개발 후 `main.py`에서 통합
- `prompts/` 폴더에 파트별 프롬프트 문서 보관

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                        사용자 (Browser)                              │
│           B2C 소비자                        B2B 직원                 │
└────────────┬──────────────────────────────────┬─────────────────────┘
             │  HTTP/HTTPS                       │  HTTP/HTTPS
             ▼                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Render.com Web Service                           │
│                  uvicorn main:app --host 0.0.0.0                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI (main.py)                         │   │
│  │                                                              │   │
│  │   PortalAuthMiddleware  ←→  SessionMiddleware                │   │
│  │         (B2B 인증)             (쿠키 세션)                    │   │
│  │                                                              │   │
│  │  ┌──────────────────┐    ┌──────────────────────────────┐   │   │
│  │  │   B2C 라우터      │    │      B2B 라우터               │   │   │
│  │  │  GET /           │    │  GET /portal/*               │   │   │
│  │  │  GET /product    │    │  GET /portal/news            │   │   │
│  │  │  GET /chatbot    │    │  GET /portal/review          │   │   │
│  │  │  GET /company    │    │  GET /portal/sns             │   │   │
│  │  └─────────┬────────┘    │  GET /portal/map             │   │   │
│  │            │             │  GET /portal/report          │   │   │
│  │            │             └──────────────┬───────────────┘   │   │
│  │            │                            │                   │   │
│  │  ┌─────────▼────────────────────────────▼───────────────┐   │   │
│  │  │                  API 라우터                            │   │   │
│  │  │  /api/chat        → recipe_chatbot.py  (B 파트)       │   │   │
│  │  │  /api/news        → news_summary.py   (C 파트)       │   │   │
│  │  │  /api/review      → review_keyword.py (D 파트)       │   │   │
│  │  │  /api/sns         → sns_generator.py  (E 파트)       │   │   │
│  │  │  /api/market      → market_map.py     (F 파트)       │   │   │
│  │  │  /api/exchange-rate → main.py (yfinance 캐싱)         │   │   │
│  │  └─────────────────────────┬─────────────────────────────┘   │   │
│  │                            │                                  │   │
│  │  ┌─────────────────────────▼─────────────────────────────┐   │   │
│  │  │                 Services Layer                          │   │   │
│  │  │                                                         │   │   │
│  │  │  chatbot_graph.py   recipe_search.py   recipe_ai.py    │   │   │
│  │  │  (LangGraph DAG)    (ChromaDB RAG)     (OpenAI 생성)   │   │   │
│  │  │                                                         │   │   │
│  │  │  output_guardrail.py  image_ai.py  analytics.py        │   │   │
│  │  │  (안전 필터)           (이미지 생성)  (사용 로그)         │   │   │
│  │  └─────────────────────────┬─────────────────────────────┘   │   │
│  └────────────────────────────┼──────────────────────────────────┘   │
│                               │                                       │
│  ┌────────────────────────────▼──────────────────────────────────┐   │
│  │                   데이터 / 스토리지 (ephemeral)                  │   │
│  │  data/chromadb/    data/recipes/*.md    data/products.json    │   │
│  │  (벡터 인덱스)       (103개 RAG 문서)     (제품 카탈로그)         │   │
│  │  data/admins.json  data/analytics/     data/markets.json      │   │
│  │  (직원 계정)         (사용 로그 .jsonl)   (유통망 좌표)           │   │
│  └───────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
             │
             ▼  외부 API 호출
┌────────────────────────────────────────────────────────────────┐
│                      External APIs                              │
│                                                                  │
│  OpenAI          YouTube API      SerpAPI       DeepL           │
│  (GPT-4.1-mini   (먹방 트렌드      (구글 검색어    (베트남어        │
│   임베딩 생성)     쇼츠 분석)       수집)          번역)           │
│                                                                  │
│  yfinance        Apify            Google Maps   Groq Cloud       │
│  (USD/KRW/VND    (리뷰 크롤링)     (유통망 지도)   (베트남어        │
│   환율)                                          분석)            │
└────────────────────────────────────────────────────────────────┘
```

### 프론트엔드 구조

```
┌─────────────────────────────────────────────────────────┐
│                   B2C 자사몰                              │
│                                                          │
│  index.html (독립 SPA)     base_b2c.html 상속 페이지     │
│  ├─ 3개국어 클라이언트 전환  ├─ company.html              │
│  ├─ 제품 모달               ├─ product.html              │
│  ├─ 자체 장바구니(dami_cart) ├─ chatbot.html (전페이지)   │
│  └─ 챗봇 FAB 직접 포함       └─ contact.html             │
│                                                          │
│  chatbot-widget.js: YONGDAM 브랜드 챗봇 UI               │
│  ├─ 헤더: YONGDAM (Nunito 900 둥근볼드체)                 │
│  ├─ 버튼 우측 정렬 (언어·모드 2줄)                        │
│  └─ 용담이 GIF 110px + mix-blend-mode 배경 블렌딩         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   B2B 직원 포탈                           │
│                                                          │
│  base_b2b.html 상속                                      │
│  ├─ dashboard.html  (뉴스·키워드 대시보드)                │
│  ├─ news.html       (AI 뉴스 요약)                       │
│  ├─ review.html     (리뷰 키워드 분석)                    │
│  ├─ sns.html        (SNS 콘텐츠 생성 + 유튜브 트렌드*)    │
│  ├─ map.html        (베트남 유통망 Google Maps)           │
│  ├─ ideas.html      (아이디어 게시판)                     │
│  ├─ customers.html  (고객 관리)                          │
│  └─ report.html     (주간 리포트 + PDF 다운로드)          │
│                                                          │
│  * sns.html: 유튜브 트렌드 썸네일 클릭 시 새 탭으로 열림  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 주요 기능 상세

### A. B2C 자사몰

| 기능 | 설명 |
|---|---|
| 3개국어 전환 | 한국어·English·Tiếng Việt 버튼 클릭으로 즉시 전환 |
| 제품 카탈로그 | 소스 6종·시즈닝 4종·코인육수 4종·가공식품 2종 |
| 제품 모달 | 상세 이미지·영양정보·설명 팝업 |
| 장바구니 | localStorage 기반, 챗봇 추천에서 직접 추가 가능 |
| 문의 폼 | `POST /api/contact` 처리 |

### B. AI 레시피 챗봇 (YONGDAM)

| 항목 | 내용 |
|---|---|
| 모델 | GPT-4.1-mini (응답) + text-embedding-3-large (벡터화) |
| RAG 소스 | 레시피 81개 + 제품상세 16개 + 회사정보 1개 + 비교문서 5개 + 요리팁 5개 = **108개** |
| 대화 모드 | 💬 자유대화 / 📋 카테고리·맛 가이드 / 🎲 랜덤 추천 |
| 언어 | 한국어·베트남어·영어 실시간 전환 |
| 레시피 카드 | 재료·조리법·팁 + 인분 조절 인터랙티브 + 장바구니 추가 버튼 |
| 안전 필터 | `output_guardrail.py` — 음식 외 주제 차단 |
| 속도 제한 | slowapi 적용 (관리자 API rate limit) |

### C. 뉴스 요약 (직원 포탈)

- RSS 피드 + Apify 크롤링으로 K-푸드·베트남 관련 뉴스 수집
- OpenAI로 핵심 요약 자동 생성
- `data/news_cache.json` 캐싱 → 대시보드에 최신 5개 표시

### D. 리뷰 키워드 분석

- 유튜브 댓글 + 리뷰 데이터 수집
- DeepL로 베트남어 → 한국어 번역
- 긍정/부정/중립 키워드 분류 후 `competitor_history.xlsx`에 누적 저장
- 대시보드에 상위 5개 키워드 막대 그래프로 표시

### E. SNS 콘텐츠 생성

| 탭 | 기능 |
|---|---|
| 베트남 유튜브 먹방 트렌드 | YouTube API로 트렌드 영상 수집, **썸네일 클릭 시 유튜브 새 탭 열림** |
| 쇼츠 바이럴 스캔 | 최근 N개월 내 바이럴 쇼츠 분석 + AI 기획안 |
| 인스타 캡션 생성 | 제품 선택 → AI 다국어 캡션 자동 생성 |
| 밈 영상 기획 | Magic Hour API 연동 쇼츠 영상 생성 |

### F. 유통망 지도

- Google Maps API + Folium으로 베트남 유통망 마커 시각화
- `data/markets.json` — 마켓별 위치·카테고리·연락처

---

## 4. 폴더 구조

```
3star_real_main/
│
├── main.py                    ← FastAPI 앱 진입점
├── render.yaml                ← Render.com 배포 설정
├── requirements.txt           ← Python 패키지 목록
├── .python-version            ← Python 3.11.7 고정 (Render용)
├── .env                       ← 환경변수 (git 제외)
├── .gitignore
│
├── routers/                   ← 기능별 API 라우터
│   ├── auth.py                ← 직원 로그인/로그아웃 (세션 기반)
│   ├── contact.py             ← B2C 문의 폼
│   ├── recipe_chatbot.py      ← 챗봇 API (RAG + AI)
│   ├── recipe_admin.py        ← 챗봇 관리자 (rate limit)
│   ├── recipe_analytics.py    ← 챗봇 사용 통계
│   ├── news_summary.py        ← 뉴스 요약
│   ├── review_keyword.py      ← 리뷰 키워드 분석
│   ├── sns_generator.py       ← SNS 콘텐츠 생성
│   ├── market_map.py          ← 유통망 지도
│   ├── ideas.py               ← 아이디어 게시판
│   └── search.py              ← 통합 검색
│
├── services/                  ← AI 서비스 레이어
│   ├── chatbot_graph.py       ← LangGraph 대화 흐름
│   ├── recipe_search.py       ← ChromaDB RAG 검색
│   ├── recipe_ai.py           ← 레시피 AI 생성
│   ├── output_guardrail.py    ← 챗봇 안전 필터
│   ├── image_ai.py            ← 이미지 AI 생성
│   ├── init_vectordb.py       ← ChromaDB 초기화 스크립트
│   ├── analytics.py           ← 사용 로그 집계
│   ├── pdf_maker.py           ← 주간 리포트 PDF 생성
│   ├── web_scraper.py         ← 뉴스 스크래핑
│   └── youtube_api.py         ← YouTube 연동
│
├── templates/
│   ├── base_b2c.html          ← B2C 공통 레이아웃
│   ├── base_b2b.html          ← B2B 공통 레이아웃
│   ├── b2c/
│   │   ├── index.html         ← 자사몰 홈 (독립 SPA)
│   │   ├── product.html       ← 제품 페이지
│   │   ├── chatbot.html       ← 전페이지 챗봇
│   │   ├── company.html
│   │   └── contact.html
│   └── b2b/
│       ├── login.html         ← 직원 로그인
│       ├── dashboard.html     ← 포탈 대시보드
│       ├── news.html
│       ├── review.html
│       ├── sns.html           ← SNS 생성 (유튜브 트렌드 링크 포함)
│       ├── map.html
│       ├── ideas.html
│       ├── customers.html
│       └── report.html
│
├── static/
│   ├── css/style.css          ← B2C CSS + 챗봇 위젯 CSS
│   ├── css/portal.css         ← B2B 포탈 CSS
│   └── js/
│       ├── chatbot-widget.js  ← 챗봇 위젯 로직 (YONGDAM UI)
│       ├── chatbot-float.js   ← 플로팅 챗봇
│       ├── cart.js            ← B2C 장바구니
│       ├── main.js            ← B2C 기본 JS
│       └── portal.js          ← B2B 포탈 JS
│
└── data/
    ├── products.json          ← 제품 카탈로그
    ├── admins.json            ← 직원 계정 (git 제외)
    ├── system_prompt.txt      ← 챗봇 시스템 프롬프트
    ├── recipes/               ← 레시피 MD 파일 (~80개)
    ├── product_details/       ← 제품 상세 MD (RAG 소스)
    ├── cooking_tips/          ← 요리팁 MD (RAG 소스)
    ├── product_comparisons/   ← 비교문서 MD (RAG 소스)
    ├── chromadb/              ← 벡터 DB (git 제외, 빌드 시 생성)
    └── analytics/             ← 사용 로그 .jsonl (일별)
```

---

## 5. 라우팅 구조

### B2C

| URL | 기능 |
|---|---|
| `GET /` | 자사몰 홈 SPA |
| `GET /product` | 제품 카탈로그 |
| `GET /chatbot` | 전페이지 챗봇 |
| `GET /company` | 브랜드 소개 |
| `GET /contact` | 문의 폼 |

### B2B (모두 세션 인증 필요)

| URL | 기능 |
|---|---|
| `GET /portal/login` | 직원 로그인 |
| `GET /portal` | 대시보드 |
| `GET /portal/news` | 뉴스 요약 |
| `GET /portal/review` | 리뷰 분석 |
| `GET /portal/sns` | SNS 생성 |
| `GET /portal/map` | 유통망 지도 |
| `GET /portal/ideas` | 아이디어 게시판 |
| `GET /portal/report` | 주간 리포트 |

### API

| Prefix | 기능 |
|---|---|
| `POST /api/chat` | 챗봇 응답 (RAG + AI) |
| `POST /api/news/*` | 뉴스 수집·요약 |
| `POST /api/review/*` | 리뷰 키워드 분석 |
| `POST /api/sns/*` | SNS 콘텐츠 생성 |
| `GET /api/exchange-rate` | 실시간 환율 (1시간 캐싱) |
| `GET /analytics/*` | 챗봇 사용 통계 |

---

## 6. 챗봇 동작 흐름

```
사용자 입력
    │
    ▼
chatbot-widget.js / chatbot-float.js
    ├─ 언어: 한국어 / Tiếng Việt / EN
    └─ 모드: 💬 대화 / 📋 가이드 / 🎲 랜덤
                    │
                    ▼ POST /api/chat
            recipe_chatbot.py
                    │
            chatbot_graph.py (LangGraph)
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
  recipe_search  recipe_ai  output_guardrail
  (ChromaDB RAG) (GPT-4.1)  (안전 필터)
  103개 문서 검색  레시피 생성  부적절 응답 차단
        │
        └──────────────────────┘
                    │
           레시피 카드 응답
           ├─ 제목·이미지
           ├─ 재료 (인분 조절 인터랙티브)
           ├─ 조리법·팁
           └─ 🛒 장바구니 추가 버튼
                    │
        window.addToCartFromChatbot(productId)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   index.html               다른 B2C 페이지
   dami_cart                threestar_cart
   (localStorage)           (localStorage)
```

---

## 7. 인증 미들웨어

```
모든 요청
    │
    ▼
PortalAuthMiddleware
    ├─ 경로 /portal/* 이고 /portal/login 이 아닌가?
    │   └─ YES → session["portal_auth"] == "authenticated" ?
    │               ├─ OK  → 통과
    │               └─ NG  → 302 Redirect → /portal/login
    └─ 그 외 → 통과

POST /portal/login
    ├─ data/admins.json에서 코드 확인 (STAR01~STAR08)
    ├─ 일치 → 세션 저장 → /portal 이동
    └─ 불일치 → 오류 메시지
```

---

## 8. 최근 변경사항

| 항목 | 내용 |
|---|---|
| `main.py` | `host="127.0.0.1"` → `host="0.0.0.0"` (Render 외부 접속) |
| `render.yaml` | buildCommand에 admins.json 복사 + ChromaDB 초기화 추가 |
| `requirements.txt` | `playwright` 제거 (미사용, 빌드 지연 원인) |
| `.python-version` | `3.11.7` 고정 파일 추가 (Render Python 3.14 충돌 방지) |
| `chatbot-widget.js` | YONGDAM UI 개편: 아이콘 제거, Nunito 볼드체, 버튼 우측 정렬, GIF 확대 |
| `templates/b2b/sns.html` | 유튜브 트렌드 썸네일 클릭 시 `target="_blank"` 링크 연결 |

---

## 9. Render 배포 가이드 (완전판)

### STEP 1 — GitHub push

```bash
git add .
git commit -m "Render 배포 설정"
git push origin main
```

**주의**: `.env`와 `data/admins.json`은 `.gitignore`에 있어 자동 제외됩니다. GitHub에 올라가지 않습니다.

---

### STEP 2 — Render 서비스 생성

1. [render.com](https://render.com) → 로그인
2. **New → Web Service**
3. GitHub 레포 연결
4. 기본 설정:

| 항목 | 값 |
|------|-----|
| **Runtime** | Python 3 |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

---

### STEP 3 — Build Command 직접 입력

> `render.yaml`이 자동 반영되지 않으므로 대시보드에서 직접 설정

**Settings → Build Command → Edit** 후 입력:

```
pip install -r requirements.txt && mkdir -p data && cp /etc/secrets/admins.json data/admins.json && python -m services.init_vectordb
```

이 명령이 순서대로 하는 일:
1. Python 패키지 설치
2. `data/` 폴더 생성
3. Secret File `admins.json` → `data/admins.json` 복사 (직원 로그인용)
4. ChromaDB 벡터 인덱스 초기화 (챗봇 RAG, OpenAI 임베딩 API 호출)

> ⚠️ **배포마다 OpenAI 임베딩 비용 소량 발생** (약 108개 문서 × text-embedding-3-large)

---

### STEP 4 — Secret Files 설정

**Settings → Secret Files → Add Secret File** (2개 추가)

**① `.env`**
- Filename: `.env`
- Contents: 로컬 `.env` 파일 내용 붙여넣기
- 아래 플레이스홀더는 **실제 값으로 교체 필수**:

```
SESSION_SECRET=여기에_랜덤_32자_이상_문자열
ADMIN_JWT_SECRET=여기에_랜덤_32자_이상_문자열
ADMIN_USERNAME=관리자_아이디
ADMIN_PASSWORD=강력한_비밀번호
TOGETHER_API_KEY=실제_키_입력
```

> 랜덤 문자열 생성: `python -c "import secrets; print(secrets.token_hex(32))"`

**② `admins.json`**
- Filename: `admins.json`
- Contents: 로컬 `data/admins.json` 내용 그대로 붙여넣기

---

### STEP 5 — 환경 변수 설정

**Settings → Environment → Add Environment Variable**

| Key | Value |
|-----|-------|
| `PYTHON_VERSION` | `3.11.7` |
| `OPENAI_API_KEY` | sk-... (실제 키) |

> 나머지 API 키들은 STEP 4의 `.env` Secret File에서 자동으로 로드됩니다.

---

### STEP 6 — 배포 실행

**Manual Deploy → Deploy latest commit**

빌드 로그에서 순서대로 확인:
```
==> pip install 완료
==> cp /etc/secrets/admins.json 성공
==> === ChromaDB 초기화 시작 ===
==> 레시피: 81개 / 제품: 16개 / ...
==> === 완료: 108개 문서 저장됨 ===
==> Running 'uvicorn main:app --host 0.0.0.0 --port ...'
==> Your service is live 🎉
```

---

### 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `pydantic.v1 ConfigError` | Python 3.14 + chromadb 비호환 | `.python-version` 파일로 3.11.7 강제 |
| 빌드 7분 이상 멈춤 | playwright 브라우저 다운로드 | `requirements.txt`에서 playwright 제거 (이미 완료) |
| 직원 로그인 불가 | `admins.json` 없음 | Secret Files에 `admins.json` 추가 후 재배포 |
| 챗봇 응답 없음 | ChromaDB 미초기화 | Build Command에 `init_vectordb` 추가 후 재배포 |
| 배포마다 챗봇 데이터 초기화 | Render 무료 플랜 ephemeral 디스크 | 유료 Render Disk 사용 또는 매 배포 시 재초기화 허용 |

---

*이 문서는 배포 환경 변경 시 업데이트 필요.*
*직원 코드: STAR01~STAR08 (data/admins.json 참조)*
