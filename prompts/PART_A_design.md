# A파트 — B2C 자사몰 디자인 AI 프롬프트
> 이 파일의 내용을 MASTER_PROMPT.md 아래에 붙여넣어서 AI에게 전달하세요.

---

## 📋 AI에게 붙여넣을 내용

```
[A파트 — B2C 자사몰 디자인 작업]

내가 수정할 수 있는 파일:
- templates/b2c/index.html    (홈 페이지)
- templates/b2c/company.html  (브랜드 소개)
- templates/b2c/product.html  (제품 페이지)
- templates/b2c/contact.html  (문의 페이지)
- static/css/style.css        (B2C 전용 CSS)
- static/js/main.js           (B2C 전용 JS, cart.js 제외)

[절대 건드리면 안 되는 파일]
- templates/base_b2c.html     (공통 레이아웃 — 수정 금지)
- static/js/cart.js           (장바구니 로직 — 수정 금지)
- templates/b2c/chatbot.html  (챗봇 — 수정 금지)

[HTML 구조 규칙 — 반드시 지켜야 함]
모든 b2c HTML 파일은 반드시 이 형식이어야 한다:

{% extends "base_b2c.html" %}
{% set active_tab = "여기에 탭명" %}   ← home / company / product / contact 중 하나

{% block title %}페이지 제목{% endblock %}

{% block content %}
  <!-- 여기에만 HTML 내용 작성 -->
{% endblock %}

{% block extra_css %}
  <!-- 이 페이지에만 필요한 CSS (선택사항) -->
{% endblock %}

{% block extra_js %}
  <!-- 이 페이지에만 필요한 JS (선택사항) -->
{% endblock %}

[product.html 특별 규칙]
- 제품 데이터는 Jinja2 변수 {{ categories }} 로 자동 주입됨
- 하드코딩된 제품 카드를 만들지 말 것
- 반드시 {% for cat_key, cat in categories.items() %} 루프를 유지할 것

[장바구니 사용법 — cart.js 함수 그대로 사용]
- addToCart('상품id')   → 장바구니에 추가
- openCartModal()       → 장바구니 모달 열기
- proceedToCheckout()   → 구매 버튼 (UI만, 결제 미구현)

[브랜드 톤앤매너]
- 브랜드명: Three Star ★ (쓰리스타)
- 대상: 베트남 20-35세 MZ세대
- 언어: 영어 기본, 한국어/베트남어 병기
- 분위기: 프리미엄하면서도 친근한 K-푸드 브랜드

이제 [원하는 페이지명].html 과 style.css 를 완성해줘.
디자인 레퍼런스: [여기에 레퍼런스 URL이나 설명 추가]
```

---

## 📁 A파트 담당 파일

| 파일 | 상태 | 할 일 |
|------|------|--------|
| `templates/b2c/index.html` | 뼈대 있음 | 디자인 완성 |
| `templates/b2c/company.html` | 뼈대 있음 | 브랜드 스토리 + 디자인 |
| `templates/b2c/product.html` | 뼈대 있음 | 제품 카드 디자인 (Jinja2 루프 유지) |
| `templates/b2c/contact.html` | 뼈대 있음 | 지도 embed + 폼 디자인 |
| `static/css/style.css` | 기본 뼈대 | 전체 B2C 스타일 완성 |
| `static/js/main.js` | 기본 있음 | 추가 인터랙션 |
| `static/images/products/` | 비어있음 | 제품 이미지 추가 |
| `static/images/brand/` | 비어있음 | 로고, 캐릭터 이미지 추가 |

## ⚠️ A파트 주의사항
- `cart.js`는 이미 장바구니 모달 HTML이 `base_b2c.html`에 포함돼 있음
- 모달 CSS 클래스는 `cart-modal-box`, `cart-items-list`, `cart-modal-footer` (수정 가능하되 클래스명 유지)
- 외부 폰트는 Google Fonts만 사용 (유료 폰트 금지)
- 이미지 없을 때 대비해 `onerror` 처리 유지




