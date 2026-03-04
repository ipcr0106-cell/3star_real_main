# Part 1: 기능별 RAG 사용 여부 매핑

## 조사 대상 파일
- `routers/recipe_chatbot.py` — 3가지 모드 엔드포인트
- `services/chatbot_graph.py` — LangGraph 11노드 파이프라인 (chat 모드 전용)
- `services/recipe_search.py` — ChromaDB 벡터 검색
- `services/recipe_ai.py` — GPT 호출 + 번역 적용

## 임베딩 모델
- **text-embedding-3-large** (OpenAI)
- ChromaDB PersistentClient, 컬렉션: `threestar`

---

## 1. chat 모드 — 자유 대화 (LangGraph 파이프라인)

### 1-1. recipe_request (레시피 요청)
- **RAG 사용**: O
- **검색 방식**: semantic search + metadata filter
- **검색 함수**: `search_similar_recipes()`
- **top_k**: 5
- **필터**: 있음
  - `type=recipe` (필수)
  - `category` (GPT가 추출한 카테고리)
  - `taste_{맛}=true/false` (맛 필터 + 부정 조건)
  - `cook_time_minutes` (최대 조리 시간)
  - `difficulty` (난이도)
- **전처리 파이프라인**:
  1. `query_rewrite` — 대화 맥락에서 질문 재작성 (gpt-4.1-mini)
  2. `query_understanding` — 자연어 → 구조화 필터 추출 (gpt-4.1-mini, JSON)
  3. `hyde` — 가상 레시피 문서 생성 (비한국어 쿼리만, gpt-4.1-mini)
- **CRAG 적용**: O
  - sim ≥ 0.5: Correct → 전체 context 전달
  - 0.3 ≤ sim < 0.5: Ambiguous → 저관련도 청크 제거
  - sim < 0.3: Incorrect → 원본 메시지로 재검색 시도
- **Filter fallback**: 결과 < 2개면 `type=recipe`만으로 재검색
- **exclude_ids**: 대화 히스토리에서 이미 추천한 recipe_id 제외
- **GPT context 전달**: `참고 정보:\n{rag_context}` 시스템 메시지 + REMINDER 샌드위칭

### 1-2. product_info (제품 정보)
- **RAG 사용**: O
- **검색 방식**: semantic search
- **검색 함수**: `search_similar_recipes()`
- **top_k**: 8
- **필터**: `{"$or": [{"type": "product"}, {"type": "comparison"}]}`
- **전처리**: 없음 (search_direct 경로, query_rewrite/hyde 스킵)
- **CRAG 적용**: O (동일 로직)
- **GPT context 전달**: 동일 샌드위칭

### 1-3. company_info (회사 정보)
- **RAG 사용**: O
- **검색 방식**: semantic search
- **검색 함수**: `search_similar_recipes()`
- **top_k**: 3
- **필터**: `{"type": "company"}`
- **전처리**: 없음 (search_direct 경로)
- **CRAG 적용**: O
- **GPT context 전달**: 동일 샌드위칭

### 1-4. cooking_tip (요리 팁)
- **RAG 사용**: O
- **검색 방식**: semantic search
- **검색 함수**: `search_similar_recipes()`
- **top_k**: 3
- **필터**: `{"$or": [{"type": "cooking_tip"}, {"type": "recipe"}, {"type": "product"}]}`
- **전처리**: 없음 (search_direct 경로)
- **CRAG 적용**: O
- **GPT context 전달**: 동일 샌드위칭

### 1-5. ingredient_search (재료 기반 검색)
- **RAG 사용**: X (벡터 검색 아님)
- **검색 방식**: 키워드 매칭 (재료 문자열 포함 여부)
- **검색 함수**: `search_by_ingredients()` (`services/ingredient_search.py`)
- **top_k**: 5
- **필터**: ChromaDB `type=recipe` 메타데이터의 `ingredients_main` 필드에서 문자열 매칭
- **전처리**: GPT가 메시지에서 재료 목록 추출 (gpt-4.1-mini)
- **GPT context 전달**: 매칭 레시피 정보 (이름, 카테고리, 매칭 재료 등) 포맷팅 후 전달

### 1-6. serving_adjust (인분 조절)
- **RAG 사용**: X
- **검색 방식**: 없음 (대화 히스토리에서 이전 레시피 추출)
- **검색 함수**: 없음
- **GPT context 전달**: 이전 레시피 정보 + 비례 조절 지시문

### 1-7. ingredient_sub (재료 대체)
- **RAG 사용**: O
- **검색 방식**: semantic search (2회)
- **검색 함수**: `search_similar_recipes()` × 2
- **top_k**: 2 (제품) + 2 (레시피)
- **필터**: `{"type": "product"}` + `{"type": "recipe"}`
- **GPT context 전달**: 대체 가능 제품 + 관련 레시피 context

### 1-8. greeting (인사)
- **RAG 사용**: X
- **검색 방식**: 없음
- **검색 함수**: 없음
- **GPT context 전달**: 없음 (generate_direct 경로)

### 1-9. out_of_scope (범위 밖)
- **RAG 사용**: X
- **검색 방식**: 없음
- **검색 함수**: 없음
- **GPT context 전달**: 없음 (generate_direct 경로)

---

## 2. guided 모드 (가이드 추천)
- **RAG 사용**: O
- **검색 방식**: semantic search + metadata filter
- **검색 함수**: `search_similar_recipes()`
- **top_k**: 3
- **필터**: 있음
  - `type=recipe` (필수)
  - 카테고리 필터: `CATEGORY_FILTER` 매핑 사용
    - 국물탕 → `category=국물`
    - 면볶음면 → `category=면`
    - 구이볶음 → `category=구이 OR 볶음`
    - 쌈샐러드 → `category=샐러드`
    - 밥죽 → `category=밥`
    - 간식음료 → `category=음료 OR 디저트 OR 스낵`
  - 맛 필터: `taste_{맛}=true`
- **전처리**: 없음 (카테고리/맛은 프론트엔드 UI에서 선택)
- **CRAG 적용**: X (chatbot_graph 파이프라인 밖이므로)
- **GPT context 전달**: `search_result["context"]` → `참고 정보:\n{rag_context}` 시스템 메시지
- **번역**: `_apply_translation()` 적용 (vi/en용)

---

## 3. random 모드 (랜덤 추천)
- **RAG 사용**: △ (벡터 검색 아님, 랜덤 선택)
- **검색 방식**: 랜덤 (벡터 유사도 검색 없음)
- **검색 함수**: `get_random_recipe()`
- **top_k**: 1
- **필터**: `type=recipe` (전체 레시피 중 랜덤 1개)
- **전처리**: 없음
- **GPT context 전달**: 선택된 레시피 content[:800] → `rag_context`로 전달
- **번역**: `_apply_translation()` 적용

---

## 4. 비슷한 레시피 (프론트엔드 버튼)
- **RAG 사용**: 별도 API 없음
- **동작**: 프론트엔드에서 현재 레시피 제목을 `chat` 모드 메시지로 재전송
- **실질적 경로**: chat 모드 → recipe_request → 동일 RAG 파이프라인
- **검색 함수**: `search_similar_recipes()` (chat 모드 파이프라인 내)
- **exclude_ids**: 대화 히스토리에서 이전 recipe_id 제외하여 중복 방지

---

## 요약 테이블

| 기능 | RAG | 검색 방식 | 검색 함수 | top_k | 필터 | CRAG | HyDE |
|------|-----|-----------|-----------|-------|------|------|------|
| chat/recipe_request | O | semantic + filter | search_similar_recipes | 5 | type, category, taste, time, difficulty | O | O (비한국어만) |
| chat/product_info | O | semantic | search_similar_recipes | 8 | type=product\|comparison | O | X |
| chat/company_info | O | semantic | search_similar_recipes | 3 | type=company | O | X |
| chat/cooking_tip | O | semantic | search_similar_recipes | 3 | type=cooking_tip\|recipe\|product | O | X |
| chat/ingredient_search | X | keyword match | search_by_ingredients | 5 | ingredients_main | X | X |
| chat/serving_adjust | X | 없음 | 없음 | - | - | X | X |
| chat/ingredient_sub | O | semantic × 2 | search_similar_recipes | 2+2 | type=product, type=recipe | O | X |
| chat/greeting | X | 없음 | 없음 | - | - | X | X |
| chat/out_of_scope | X | 없음 | 없음 | - | - | X | X |
| guided | O | semantic + filter | search_similar_recipes | 3 | type, category, taste | X | X |
| random | △ | random | get_random_recipe | 1 | type=recipe | X | X |

---

생성일: 2026-03-03
