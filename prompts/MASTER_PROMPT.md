# ★ 쓰리스타 프로젝트 — AI 마스터 프롬프트
> Claude, Gemini, ChatGPT, Cursor 등 **모든 AI 도구에 코딩을 시킬 때** 대화 맨 앞에 이 내용을 붙이세요.  
> 이것만 제대로 넣으면 AI가 "이 프로젝트를 이미 아는 개발자"처럼 동작합니다.

---

## 📋 AI에게 붙여넣을 프롬프트 (복사해서 사용)

```
[프로젝트 컨텍스트]
나는 "Three Star(쓰리스타)"라는 베트남 K-푸드 브랜드의 웹 플랫폼을 개발 중이야.
이 프로젝트의 기술 스택과 규칙을 먼저 알려줄게. 코드를 짜기 전에 반드시 이 규칙을 지켜줘.

[기술 스택]
- 백엔드: Python 3.11 + FastAPI + Jinja2 템플릿
- 프론트: 순수 HTML/CSS/JS (React 없음, 프레임워크 없음)
- AI 연동: OpenAI GPT-4o-mini (os.getenv("OPENAI_API_KEY"))
- 패키지: requirements.txt 참고

[폴더 구조 핵심]
- routers/파일명.py → 각 기능의 API 엔드포인트 (반드시 /api/ 접두사)
- services/파일명.py → 외부 API 호출 함수들
- templates/b2c/ → 고객용 HTML (base_b2c.html 상속)
- templates/b2b/ → 직원 포탈 HTML (base_b2b.html 상속)
- static/css/style.css → B2C 스타일
- static/css/portal.css → B2B 포탈 스타일

[절대 지켜야 할 규칙]
1. main.py는 건드리지 않는다
2. base_b2c.html / base_b2b.html은 건드리지 않는다
3. 모든 API 엔드포인트는 /api/ 로 시작한다
4. API 키는 반드시 os.getenv()로만 호출한다
5. 라우터는 반드시 APIRouter() 를 사용하고, return 값은 딕셔너리
6. HTML은 반드시 base 템플릿을 extends 하고, {% block content %} 안에만 내용 작성
7. CSS 클래스명은 반드시 파트 prefix를 붙인다 (예: .c-news-card, .d-keyword-tag)

[내가 지금 요청할 파트]
→ 아래에 구체적인 작업 내용을 적어주세요
```

---

## ✅ 사용법

1. 위 박스 전체를 복사
2. AI 대화창에 붙여넣기
3. 맨 마지막 줄 `[내가 지금 요청할 파트]` 아래에 구체적인 요청 추가
4. 각 파트별 프롬프트는 `prompts/PART_*.md` 파일 참고

---

## ⚠️ AI별 주의사항

| AI 도구 | 주의할 점 |
|---------|-----------|
| **Claude** | 마스터 프롬프트 + 파트 프롬프트를 한 번에 붙여넣기 |
| **ChatGPT/GPT-4** | 대화가 길어지면 앞 내용을 잊음 → 새 대화마다 마스터 프롬프트 재첨부 |
| **Gemini** | 코드가 길면 잘림 → 함수 단위로 나눠서 요청 |
| **Cursor** | `.cursorrules` 파일에 마스터 프롬프트 내용을 넣어두면 자동 적용 |
| **GitHub Copilot** | 파트별 프롬프트를 해당 파일 최상단에 주석으로 붙여넣기 |

---

## 🔄 코드 품질 유지 전략

AI가 생성한 코드를 받을 때 반드시 확인해야 할 체크리스트:

```
받은 코드를 붙여넣기 전 체크:
□ APIRouter()를 사용했는가?
□ 엔드포인트가 /api/로 시작하는가?
□ API 키를 os.getenv()로 호출하는가?
□ return 값이 딕셔너리인가?
□ HTML이 {% extends %} 로 시작하는가?
□ {% block content %} 안에만 내용이 있는가?
□ CSS 클래스명에 파트 prefix가 있는가?
□ main.py를 수정하라는 내용이 있는가? (있으면 PM에게 전달해주세요)
```
