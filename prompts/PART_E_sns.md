# E파트 — SNS 콘텐츠 자동 생성 AI 프롬프트
> 이 파일의 내용을 MASTER_PROMPT.md 아래에 붙여넣어서 AI에게 전달하세요.

---

## 📋 AI에게 붙여넣을 내용

```
[E파트 — SNS 콘텐츠 생성 작업]

내가 구현해야 할 파일:
- routers/sns_generator.py  (API 로직)
- templates/b2b/sns.html    (화면 뼈대 있음, {% block content %} 안만 수정 가능)
- services/youtube_api.py   (YouTube API 연동)

[HTML이 기대하는 API 명세 — 3개의 엔드포인트]

1) GET /api/sns/trends
   출력: {
     "trends": [
       {
         "title": "영상 제목",
         "channel": "채널명",
         "views": "100만",
         "thumbnail": "https://img.youtube.com/..."
       }
     ]
   }

2) POST /api/sns/tiktok
   입력: { "product": "코인육수" }
   출력: {
     "script_vn": "베트남어 틱톡 15초 대본",
     "prompt_ko": "쇼츠 영상 제작 프롬프트 (한국어)"
   }

3) POST /api/sns/dm
   입력: { "influencer_name": "@mukbang_hanoi", "product": "코인육수" }
   출력: {
     "dm_text": "인플루언서에게 보낼 DM 전문 (베트남어)"
   }

[YouTube API 사용법]
- API 키: os.getenv("YOUTUBE_API_KEY")
- 검색 쿼리 예시: "베트남 먹방 2025", "Vietnam mukbang Korean food"
- 인기 영상 기준: viewCount, likeCount 내림차순

[틱톡 대본 프롬프트 힌트]
"당신은 베트남 틱톡 식품 마케팅 전문가입니다.
{product} 제품으로 15초 틱톡 영상 대본을 베트남어로 작성해주세요.
현재 베트남에서 유행하는 먹방 밈 스타일로 작성하고,
시청자가 제품을 써보고 싶어지도록 유도하세요.
대본은 훅(0-3초) / 데모(3-12초) / CTA(12-15초) 구조로."

[DM 프롬프트 힌트]
"당신은 K-푸드 브랜드 마케터입니다.
{influencer_name} 인플루언서에게 {product} 제품 협찬을 제안하는
친근하고 자연스러운 DM을 베트남어로 작성해주세요.
과도하게 홍보적이지 않고, 먼저 채널을 칭찬하고, 협찬 조건을 간단히 제안하세요."

[틱톡 관련 현실적 제약]
- 틱톡 공식 API는 DM 발송을 지원하지 않음
- 따라서 DM 문구 생성 + 복사 버튼 방식으로만 구현 (HTML에 이미 반영됨)
- 틱톡 팔로워 수 필터링: 공식 방법 없음 → 유튜브로만 구현

[화면 수정 시 규칙]
- CSS 클래스명에 .e- prefix 사용 (예: .e-trend-card, .e-script-box)
- {% extends "base_b2b.html" %} 줄 절대 삭제 금지

이제 routers/sns_generator.py 와 services/youtube_api.py 를 완성해줘.
```

---

## 📁 E파트 담당 파일

| 파일 | 상태 | 할 일 |
|------|------|--------|
| `routers/sns_generator.py` | 뼈대만 있음 | **핵심 작업 위치** |
| `services/youtube_api.py` | 뼈대 있음 | YouTube API 연동 |
| `templates/b2b/sns.html` | 뼈대 있음 | `{% block content %}` 안만 수정 가능 |

## ⚠️ E파트 주의사항
- YouTube API 무료 할당량: 일 10,000 유닛. 검색 1회 = 100유닛 소모
- 과도한 API 호출 방지를 위해 결과 캐싱 구현 권장 (5분~1시간)
- DM 자동 발송 기능은 구현하지 않음 (복사 버튼만)
