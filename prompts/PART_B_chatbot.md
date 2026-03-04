# B파트 — 레시피 챗봇 AI 프롬프트
> 이 파일의 내용을 MASTER_PROMPT.md 아래에 붙여넣어서 AI에게 전달하세요.

---

## 📋 AI에게 붙여넣을 내용

```
[B파트 — 레시피 챗봇 작업]

내가 구현해야 할 파일: routers/recipe_chatbot.py

[이미 만들어진 것 — 건드리지 않는다]
- templates/b2c/chatbot.html (HTML 완성됨)
- HTML은 fetch('/api/recipe', { method: 'POST', body: { ingredients: [...], language: 'ko' } }) 로 호출함

[내가 구현해야 할 API]
POST /api/recipe
- 입력: { "ingredients": ["소고기", "코인육수", "쌀국수"], "language": "ko" }
- 출력: {
    "recipe_title": "쌀국수 with 코인육수",
    "recipe_text": "레시피 본문 (마크다운 OK)",
    "image_url": "(선택사항)",
    "pdf_url": "(선택사항)"
  }

[사용할 서비스 파일]
- services/openai_api.py → GPT-4o-mini 호출
- services/recipe_search.py → ChromaDB RAG 검색 (data/recipes/ 폴더의 .md 파일 사용)
- services/image_ai.py → Together AI 이미지 생성 (선택)
- services/pdf_maker.py → reportlab PDF 생성 (선택)

[구현 순서 권장]
1단계: OpenAI로 레시피 텍스트만 생성 (가장 먼저)
2단계: ChromaDB RAG로 기존 레시피 검색 연결
3단계: 이미지 생성 추가
4단계: PDF 생성 추가

[현재 data/recipes/ 에 있는 파일]
- coin_broth_pho.md (베트남 쌀국수 with 코인육수 레시피)

[프롬프트 힌트]
시스템 프롬프트 예시:
"당신은 쓰리스타 K-푸드 브랜드의 레시피 전문가입니다.
재료를 입력받으면 베트남 현지인도 따라할 수 있는 한국 레시피를 {language}로 만들어주세요.
가능하면 쓰리스타 제품(코인육수, 가루시즈닝, 액체소스)을 레시피에 포함하세요."

이제 routers/recipe_chatbot.py 를 완성해줘.
APIRouter를 사용하고, 반드시 /api/recipe 엔드포인트를 POST로 만들어줘.
```

---

## 📁 B파트 담당 파일

| 파일 | 상태 | 할 일 |
|------|------|--------|
| `routers/recipe_chatbot.py` | 뼈대만 있음 | **여기가 핵심 작업 위치** |
| `services/openai_api.py` | 뼈대 있음 | 필요시 함수 추가 |
| `services/recipe_search.py` | 뼈대 있음 | ChromaDB 연결 구현 |
| `services/image_ai.py` | 뼈대 있음 | Together AI 연결 |
| `services/pdf_maker.py` | 뼈대 있음 | reportlab PDF 생성 |
| `data/recipes/*.md` | 샘플 있음 | 레시피 추가 가능 |
| `templates/b2c/chatbot.html` | **완성됨** | 🚫 수정 금지 |

## ⚠️ B파트 주의사항
- `chatbot.html`은 이미 완성돼 있어서 수정하면 안 됨
- PDF 파일은 `static/pdfs/` 폴더에 저장하고 `/static/pdfs/파일명.pdf`로 URL 반환
- 이미지 파일은 `static/images/generated/` 폴더에 저장
