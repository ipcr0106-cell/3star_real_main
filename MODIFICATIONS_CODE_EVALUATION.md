# CHATBOT_MODIFICATIONS vs 현재 코드 대조 평가

> 대상: `3star_real_main` 프로젝트의 챗봇 관련 코드 전수 조사
> 작성일: 2026-03-04

---

## 평가 기준

각 수정사항에 대해 다음을 평가한다:
- **현재 코드 상태**: 실제 코드가 어떻게 되어있는지
- **MODIFICATIONS 제안**: 무엇을 어떻게 바꾸라는 것인지
- **제안의 타당성**: 현재 코드 구조상 이 수정이 맞는지, 부작용은 없는지
- **적용 판정**: ✅ 적용 권장 / ⚠️ 수정 후 적용 / ❌ 적용 불필요

---

## 수정 1: Guided 모드 검색 쿼리 수정

**파일**: `routers/recipe_chatbot.py` (line 144)

### 현재 코드
```python
search_result = await search_similar_recipes(
    query=req.taste or query, top_k=3, filters=filters
)
```

### MODIFICATIONS 제안
```python
search_result = await search_similar_recipes(
    query=query, top_k=3, filters=filters
)
```

### 평가

| 항목 | 판단 |
|------|------|
| **문제 진단** | 정확함. `req.taste`가 "매운"이면 검색 쿼리가 "매운" 한 단어가 됨 |
| **수정 방향** | 정확함. `query`는 "국물/탕 매운 맛"처럼 카테고리+맛이 결합된 문장 |
| **부작용** | 없음. `query`가 항상 `req.taste`를 포함하므로 정보 손실 없음 |
| **코드 확인** | `query_parts`에 카테고리명과 taste가 모두 추가됨 (line 131-139) |

### 판정: ✅ 적용 권장
- 1줄 수정으로 Guided 모드 검색 품질이 즉시 개선됨
- 위험도 제로

---

## 수정 2: classify_intent_node 에러 핸들링

**파일**: `services/chatbot_graph.py` (line 142-144)

### 현재 코드
```python
async def classify_intent_node(state: PipelineState) -> dict:
    intent = await classify_intent(state["message"])
    return {"intent": intent}
```

### MODIFICATIONS 제안
```python
async def classify_intent_node(state: PipelineState) -> dict:
    try:
        intent = await classify_intent(state["message"])
    except Exception as e:
        logger.warning(f"classify_intent failed: {e}, defaulting to recipe_request")
        intent = "recipe_request"
    return {"intent": intent}
```

### 평가

| 항목 | 판단 |
|------|------|
| **문제 진단** | 정확함. GPT API 호출 실패 시 전체 파이프라인이 중단됨 |
| **fallback 값** | `recipe_request`는 합리적. 가장 일반적인 의도이며 전체 RAG 경로를 타므로 안전 |
| **부작용** | 없음. 최악의 경우 레시피 추천이 반환되는 것뿐 |
| **기존 보호** | `generate_node`에는 이미 try/except가 있지만 (line 453-454), classify 단계에서 실패하면 도달하지 못함 |

### 판정: ✅ 적용 권장
- OpenAI API 장애, 네트워크 오류, Rate Limit 등 실제 발생 가능한 시나리오에 대한 필수 보호

---

## 수정 3: query_rewrite_node 에러 핸들링

**파일**: `services/chatbot_graph.py` (line 148-175)

### 현재 코드
```python
async def query_rewrite_node(state: PipelineState) -> dict:
    # ... GPT 호출 (try/except 없음)
    rewritten = await call_gpt_mini(prompt, max_tokens=100, temperature=0.2)
    return {"rewritten_query": rewritten.strip() or message}
```

### MODIFICATIONS 제안: 예외 시 원본 메시지 반환

### 평가

| 항목 | 판단 |
|------|------|
| **문제 진단** | 정확함. GPT 호출 실패 시 파이프라인 중단 |
| **fallback 값** | `message`(원본) 반환은 완벽한 fallback. 쿼리 재작성은 보조 기능이므로 원본으로도 검색 가능 |
| **부작용** | 없음 |
| **현재 보호** | `history`가 비어있으면 원본 반환하는 로직은 있음 (line 153-154), 그러나 GPT 호출 실패에 대한 보호는 없음 |

### 판정: ✅ 적용 권장

---

## 수정 4: hyde_node 에러 핸들링

**파일**: `services/chatbot_graph.py` (line 241-261)

### 현재 코드
```python
async def hyde_node(state: PipelineState) -> dict:
    # ... GPT 호출 (try/except 없음)
    doc = await call_gpt_mini(prompt, max_tokens=200, temperature=0.3)
    return {"hyde_doc": doc.strip()}
```

### MODIFICATIONS 제안: 예외 시 빈 문자열 반환

### 평가

| 항목 | 판단 |
|------|------|
| **문제 진단** | 정확함 |
| **fallback 값** | 빈 문자열은 완벽한 fallback. `search_node`에서 `hyde_doc`이 비면 `rewritten_query`를 사용함 (line 342) |
| **부작용** | 없음. HyDE 자체가 선택적 품질 향상 기능 |

### 판정: ✅ 적용 권장

---

## 수정 5: search_node 에러 핸들링

**파일**: `services/chatbot_graph.py` (line 276-403)

### 현재 코드
search_node는 약 130줄의 복잡한 함수. CRAG 3단계 + 필터 fallback + 재검색 로직을 포함하지만 전체를 감싸는 try/except가 없음.

### MODIFICATIONS 제안: 내부 로직을 `_search_node_inner`로 분리, 외부에서 try/except 래핑

### 평가

| 항목 | 판단 |
|------|------|
| **문제 진단** | 정확함. ChromaDB 접근 실패, 필터 구성 오류 등 다양한 실패 지점이 존재 |
| **fallback 값** | `{"rag_context": "", "max_similarity": 0.0, "search_result": None}`은 안전. generate_node가 RAG 없이도 GPT 응답을 생성할 수 있음 |
| **분리 방식** | 합리적이나, 단순히 전체를 try/except로 감싸는 것으로도 충분 |
| **부작용** | 없음 |

### 판정: ✅ 적용 권장
- 단, `_search_node_inner` 분리보다는 기존 함수에 try/except 래핑이 더 단순

---

## 수정 6: Guided/Random 이미지 에러 핸들링

**파일**: `routers/recipe_chatbot.py` (Random: line 98-110, Guided: line 162-171)

### 현재 코드 (두 곳 모두 동일 패턴)
```python
if formatted.get("type") == "recipe":
    rid = formatted.get("recipe_id", "")
    if rid:
        cached = get_cached_image(rid)
        if cached:
            formatted["image_url"] = cached
        else:
            formatted["image_url"] = await generate_recipe_image(rid, ...)
```

### MODIFICATIONS 제안: try/except로 감싸고 실패 시 `image_url = ""`

### 평가

| 항목 | 판단 |
|------|------|
| **문제 진단** | 정확함. DALL-E 3 API 실패 시 전체 응답이 깨짐 |
| **chat 모드에서는?** | `chatbot_graph.py`의 `generate_node`(line 467-475)에는 **이미** try/except가 있음 ✅ |
| **guided/random에서는?** | try/except **없음** ❌ |
| **부작용** | 없음. 이미지 없이도 레시피 응답은 유효 |

### 판정: ✅ 적용 권장
- chat 모드는 이미 보호됨. guided/random 모드만 추가하면 됨

---

## 수정 7: Query Understanding 키워드 기반 Fallback

**파일**: `services/chatbot_graph.py`

### 현재 코드
- `TASTE_ALIASES` 사전: ✅ **이미 존재** (line 23-34, 20+ 매핑)
- `query_understanding_node`: GPT 결과에 대해 TASTE_ALIASES로 정규화 ✅
- **그러나**: GPT 호출 실패 시 fallback이 없음 ❌

### MODIFICATIONS 제안
1. GPT 호출 **전**에 메시지에서 맛 키워드를 직접 추출 (fallback용)
2. GPT 실패 시 fallback 키워드 사용

### 평가

| 항목 | 판단 |
|------|------|
| **TASTE_ALIASES** | 이미 적용됨. GPT가 반환한 맛 값을 정규화하는 용도로 잘 사용 중 |
| **fallback 로직** | 미적용. GPT 실패 시 필터가 비어있게 됨 → 필터 없이 검색 → 부정확한 결과 |
| **효과** | 중간. GPT 실패는 드문 경우이나, 실패 시 최소한의 필터링이라도 유지하면 좋음 |

### 판정: ⚠️ 수정 후 적용 권장
- TASTE_ALIASES는 이미 적용됨 → 이 부분은 중복
- **GPT 실패 시 메시지에서 키워드 직접 추출하는 fallback만 추가**하면 됨
- query_understanding_node에 try/except도 함께 추가 필요

---

## 수정 8: CRAG 임계값 환경변수화 + 0.5→0.45

**파일**: `services/chatbot_graph.py` (line 367-373)

### 현재 코드
```python
if max_sim >= 0.5:     # 하드코딩
    ...
elif max_sim >= 0.3:   # 하드코딩
    ...
```

### MODIFICATIONS 제안
```python
CRAG_CORRECT_THRESHOLD = float(os.getenv("CRAG_CORRECT_THRESHOLD", "0.45"))
CRAG_AMBIGUOUS_THRESHOLD = float(os.getenv("CRAG_AMBIGUOUS_THRESHOLD", "0.3"))
CRAG_RETRY_THRESHOLD = float(os.getenv("CRAG_RETRY_THRESHOLD", "0.25"))
```

### 평가

| 항목 | 판단 |
|------|------|
| **0.45 근거** | MODIFICATIONS의 실측 데이터가 설득력 있음: 평균 유사도 0.4914, 0.5 기준에서 55%만 Correct, 0.45에서 80% Correct |
| **환경변수화** | 합리적. 재배포 없이 A/B 테스트 가능 |
| **리스크** | 0.45로 내리면 관련 없는 결과(sim 0.45~0.50)도 Correct로 통과할 가능성. 그러나 MODIFICATIONS의 실측에 따르면 이 구간에 정답이 밀집 |
| **현재 코드에 `import os`** | chatbot_graph.py에 `import os`가 **없음**. 추가 필요 |
| **부작용** | 0.45~0.50 구간의 결과가 필터링 없이 통과. 현재 recipe_request Context Precision이 0.649인 점을 고려하면 추가 하락 위험 |

### 판정: ⚠️ 신중하게 적용 권장
- 환경변수화는 무조건 적용하되, **기본값은 현재 0.5를 유지**하고 운영 중 로그 모니터링 후 조정하는 것이 안전
- 0.45로 즉시 변경하기보다 0.48부터 단계적으로 테스트 권장
- `import os` 추가 필요

---

## 수정 9: 프론트엔드 컨텍스트 윈도우 10→6턴

**파일**: `static/js/chatbot-float.js`

### 현재 코드
3곳에서 `cwConversationHistory.slice(-10)` 사용

### 백엔드 상태 (recipe_ai.py)
```python
recent = history[-6:]  # 이미 6턴으로 제한
```

### 평가

| 항목 | 판단 |
|------|------|
| **불일치** | 프론트엔드는 10턴 전송하지만 백엔드는 6턴만 사용 → 4턴분의 데이터가 불필요하게 전송됨 |
| **성능 영향** | 미미함. JSON 페이로드 크기 차이가 작음 |
| **기능 영향** | 없음. 백엔드가 이미 6턴으로 자르고 있으므로 결과는 동일 |
| **일관성** | FE/BE 불일치는 유지보수에 혼란을 줄 수 있음 |

### 판정: ⚠️ 적용 권장 (우선순위 낮음)
- 기능적으로 차이 없음. 일관성 유지 차원에서 적용하되 급하지 않음

---

## 수정 10: HyDE 한국어 스킵 제거 + 다국어 프롬프트

**파일**: `services/chatbot_graph.py` (line 241-261)

### 현재 코드
```python
# 한국어 비율 30% 이상이면 HyDE 스킵 (DB가 한국어이므로)
korean_chars = sum(1 for c in query if '\uac00' <= c <= '\ud7a3')
if len(query) > 0 and korean_chars / len(query) > 0.3:
    logger.info(f"HyDE skipped: Korean ratio {korean_chars/len(query):.0%}")
    return {"hyde_doc": ""}
```

### 현재 프롬프트 (한국어만)
```python
prompt = f"""다음 질문에 대한 가상의 한국-베트남 퓨전 레시피를 한국어로 간략히 작성하세요.
제목, 재료 3~5개, 조리법 2~3단계만 포함하세요.
질문: {query}
가상 레시피:"""
```

### MODIFICATIONS 제안
1. 한국어 스킵 조건 **완전 제거**
2. 3언어(한/베/영) 가상 문서 생성 프롬프트로 교체

### 현재 DB 문서 구조 확인
```
Vietnamese: Bún bò Huế           ← 문서 앞부분 (임베딩 가중치 높음)
English: Hue-Style Spicy Beef... ← 두 번째
# 후에식 매운 소고기 국수 (...)   ← 한국어는 세 번째부터
```

### 평가

| 항목 | 판단 |
|------|------|
| **"DB가 한국어" 전제** | **틀림**. `init_vectordb.py` line 74-81에서 문서 앞에 `Vietnamese:` + `English:`을 붙이고 있음. 즉 DB 문서는 **베트남어/영어 선행** |
| **한국어 스킵의 영향** | 한국어 쿼리가 들어왔을 때 HyDE가 꺼지면, 짧은 한국어 질문("매콤한 거 추천")이 베트남어/영어 선행 문서와 바로 매칭됨 → 유사도 낮음 |
| **다국어 프롬프트** | 합리적. DB 문서와 같은 형식(Vietnamese → English → 한국어)으로 가상 문서를 생성하면 임베딩 매칭이 개선됨 |
| **스킵 완전 제거** | 주의 필요. HyDE는 추가 GPT 호출 = 비용 + 지연시간 증가. 모든 쿼리에 HyDE를 적용하면 응답 시간이 늘어남 |

### 판정: ⚠️ 수정 후 적용 권장
- **한국어 스킵 제거**: 적용 권장. MODIFICATIONS의 분석이 정확함
- **다국어 프롬프트**: 적용 권장. DB 문서 형식과 일치시키는 것이 논리적
- **단, 비용/지연 모니터링 필요**: 모든 쿼리에 HyDE 적용 시 GPT 호출 1회 추가됨

---

## 수정 11: init_vectordb.py 한국어 검색 키워드 지원

**파일**: `services/init_vectordb.py` (line 74-81)

### 현재 코드
```python
name_vn = fm.get("name_vn", "")
name_en = fm.get("name_en", "")
prefix = ""
if name_vn:
    prefix += f"Vietnamese: {name_vn}\n"
if name_en:
    prefix += f"English: {name_en}\n"
```

### MODIFICATIONS 제안
```python
prefix = ""
if search_keywords:
    prefix += f"검색키워드: {search_keywords}\n"
if name_ko:
    prefix += f"한국어: {name_ko}\n"
if name_vn:
    prefix += f"Vietnamese: {name_vn}\n"
if name_en:
    prefix += f"English: {name_en}\n"
```

### 평가

| 항목 | 판단 |
|------|------|
| **현재 문제** | 임베딩 텍스트가 `Vietnamese:` → `English:` → 본문 순서. 한국어 키워드가 문서 상단에 없어 한국어 쿼리와의 유사도가 낮음 |
| **제안 효과** | 한국어 검색 키워드를 문서 **최상단**에 배치하면 한국어 쿼리 유사도가 크게 개선됨 |
| **전제 조건** | 레시피 파일에 `search_keywords`, `name_ko` 필드가 **있어야** 동작 → 현재 없음 |
| **name vs name_ko** | 현재 레시피의 `name` 필드가 이미 한국어 이름 (예: "후에식 매운 소고기 국수"). `name_ko`를 별도로 추가할 필요 없이 `name`을 사용해도 됨 |

### 판정: ⚠️ 수정 후 적용 권장
- `name_ko` 대신 기존 `name` 필드를 `한국어:` 접두사로 추가하면 **레시피 파일 수정 없이** 즉시 효과를 볼 수 있음
- `search_keywords`는 별도 작업이 필요하므로 단계적 적용 권장:
  - **1단계**: `name` 필드를 `한국어:` 접두사로 추가 (코드 1줄)
  - **2단계**: 레시피 파일에 `search_keywords` 필드 추가 (81개 파일)
  - **3단계**: ChromaDB 재구축

---

## 수정 12: 레시피 81개 파일에 search_keywords, name_ko 추가

**파일**: `data/recipes/*.md` (81개)

### 현재 상태
```yaml
id: recipe_bun_bo_hue_coin01_002
name: 후에식 매운 소고기 국수
name_vn: Bún bò Huế
name_en: Hue-Style Spicy Beef Noodle Soup
# ... (search_keywords, name_ko 필드 없음)
```

### MODIFICATIONS 제안
```yaml
name_ko: 후에식 매운 소고기 국수
search_keywords: "매운 쌀국수, 분보후에, 매콤한 국수, 소고기 국수, ..."
```

### 평가

| 항목 | 판단 |
|------|------|
| **name_ko** | `name` 필드와 동일한 값. **불필요한 중복**. init_vectordb.py에서 `fm.get("name")` 사용하면 됨 |
| **search_keywords** | 유의미한 개선. 한국어 동의어/구어체 표현을 추가하면 검색 정확도 향상 |
| **작업량** | 81개 파일에 수작업은 비현실적 → scripts 디렉토리에 자동화 스크립트 필요 |
| **MODIFICATIONS의 스크립트** | `scripts/add_search_keywords.py`, `scripts/enrich_search_keywords.py`를 언급하지만 실행된 적 없음 |
| **유사도 개선 데이터** | MODIFICATIONS의 실측: "소고기 쌀국수" 0.421 → 0.616 (+46%). 매우 유의미한 개선 |

### 판정: ⚠️ 단계적 적용 권장
- **name_ko 추가**: 불필요. 기존 `name` 필드를 init_vectordb.py에서 사용하면 동일 효과
- **search_keywords 추가**: 효과 크지만 작업량이 큼. 자동화 스크립트로 처리해야 함
- 우선 init_vectordb.py만 수정하여 `name` 필드를 prefix에 추가하는 것이 즉시 적용 가능한 최선

---

## 종합 평가 요약

### 적용 우선순위

| 순위 | 수정 | 파일 | 난이도 | 효과 | 판정 |
|------|------|------|--------|------|------|
| **1** | Guided 모드 쿼리 수정 | recipe_chatbot.py | 1줄 | 높음 | ✅ 즉시 적용 |
| **2** | 에러 핸들링 4개 노드 | chatbot_graph.py | 각 3~5줄 | 높음 | ✅ 즉시 적용 |
| **3** | Guided/Random 이미지 에러 핸들링 | recipe_chatbot.py | 각 4줄 | 중간 | ✅ 즉시 적용 |
| **4** | HyDE 한국어 스킵 제거 + 다국어 프롬프트 | chatbot_graph.py | 15줄 | 높음 | ⚠️ 적용 (비용 모니터링) |
| **5** | init_vectordb `name` prefix 추가 | init_vectordb.py | 3줄 | 높음 | ⚠️ 적용 (ChromaDB 재구축 필요) |
| **6** | CRAG 임계값 환경변수화 | chatbot_graph.py | 5줄 | 중간 | ⚠️ 적용 (기본값 0.5 유지 권장) |
| **7** | query_understanding fallback | chatbot_graph.py | 10줄 | 낮음 | ⚠️ 선택적 |
| **8** | FE 컨텍스트 윈도우 10→6 | chatbot-float.js | 3줄 | 낮음 | ⚠️ 낮은 우선순위 |
| **9** | 레시피 search_keywords 추가 | recipes/*.md 81개 | 대규모 | 매우 높음 | ⚠️ 자동화 스크립트 필요 |

### MODIFICATIONS에서 이미 적용된 것

| 항목 | 상태 | 비고 |
|------|------|------|
| TASTE_ALIASES (20+ 매핑) | ✅ 적용됨 | chatbot_graph.py line 23-34 |
| generate_node 이미지 에러 핸들링 | ✅ 적용됨 | chatbot_graph.py line 467-475 (chat 모드만) |
| generate_node 전체 에러 핸들링 | ✅ 적용됨 | chatbot_graph.py line 453-454 |
| 백엔드 6턴 제한 | ✅ 적용됨 | recipe_ai.py의 `history[-6:]` |

### MODIFICATIONS의 분석 오류/주의사항

| 항목 | 내용 |
|------|------|
| **name_ko 필드** | 기존 `name` 필드가 이미 한국어 → 별도 필드 불필요 |
| **문서 수 103 vs 108** | init_vectordb.py 헤더는 103이라고 하지만 cooking_tips 5개를 포함하면 108. 그러나 이는 코드 **주석의 오류**이지 기능 문제는 아님 |
| **CRAG 0.45 즉시 적용** | Context Precision이 이미 0.649로 낮은 상황에서 임계값을 낮추면 더 하락할 수 있음. 단계적 조정 권장 |

### 현재 코드의 숨은 강점 (MODIFICATIONS에서 미언급)

| 항목 | 위치 | 설명 |
|------|------|------|
| generate_node 빈 레시피 fallback | chatbot_graph.py line 460-469 | 빈 title/ingredients/steps 감지 시 chat 타입으로 자동 전환 |
| Intent 기반 type 강제 교정 | chatbot_graph.py line 447-454 | GPT가 잘못된 type을 반환해도 intent에 맞게 교정 |
| 필터 fallback 재검색 | chatbot_graph.py line 352-358 | recipe_request에서 결과 부족 시 type=recipe만으로 재검색 |
| CRAG 4단계 동작 | chatbot_graph.py line 378-395 | 재검색 실패 시에도 recipe_request면 기존 결과 전달 |
| 번역 시스템 | recipe_ai.py | `_apply_translation()`으로 vi/en 자동 번역 |
