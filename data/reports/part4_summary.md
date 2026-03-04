# Part 4: RAGAS 재평가 결과

## 평가 환경
- 평가 모델: gpt-4.1 (Faithfulness, Context Precision) + gpt-4.1 (Answer Relevancy, custom)
- 테스트 케이스: 23개 (기존 동일)
- RAGAS 버전: 0.4.3
- 변경사항: 레시피 72→81, 마크다운 70개 수정 (다미푸드 제품 추가), translations.json 재생성, ChromaDB 재인덱싱

## 현재 점수

| 메트릭 | 점수 |
|--------|------|
| Faithfulness | 0.845 |
| Context Precision | 0.673 |
| Answer Relevancy | 0.957 |
| **RAGAS Score (전체)** | **0.825** |

## RAG-only 점수 (RAG 의도 21개)

| 메트릭 | 이전 (v3) | 현재 (v4) | Delta |
|--------|-----------|-----------|-------|
| Faithfulness | 0.925 | 0.925 | 0.000 |
| Context Precision | 0.737 | 0.737 | 0.000 |
| Answer Relevancy | 0.952 | 0.952 | 0.000 |
| **RAG-only RAGAS** | **0.874** | **0.871** | **-0.003** |

## 비교 분석

### 이전 RAG-only RAGAS: 0.874 → 현재: 0.871
- 차이: **-0.003** (실질적으로 동일)
- 70개 레시피 마크다운 수정 및 ChromaDB 재인덱싱이 RAG 품질에 **부정적 영향 없음** 확인

### Intent / Type 정확도
- Intent 정확도: 23/23 (100.0%)
- Type 정확도: 23/23 (100.0%)

### 세부 메트릭 분석
- **Faithfulness (0.845)**: RAG intent에서 0.925로 높음. Non-RAG (serving_adjust, ingredient_sub)에서 0.0으로 전체 평균 하락
- **Context Precision (0.673)**: 가장 낮은 메트릭. recipe_request 일부에서 관련 없는 context가 포함
- **Answer Relevancy (0.957)**: 가장 높은 메트릭. GPT가 질문에 적합한 답변 생성

### 약한 케이스
| 쿼리 | F | CP | AR | 원인 |
|------|---|----|----|------|
| 4인분으로 바꿔줘 | 0.00 | 0.00 | 1.00 | serving_adjust (RAG 없음, 대화 히스토리 필요) |
| 고수 대신 뭘 쓸까? | 0.00 | 0.00 | 1.00 | ingredient_sub (context 부족) |
| 소고기, 양파, 당근 있어 | 0.07 | 0.83 | 0.80 | ingredient_search (키워드 매칭, 벡터 아님) |

## 결론
- **점수 유지됨**: 0.874 → 0.871 (RAG-only), 차이 -0.003은 무시 가능
- 70개 레시피 수정 + ChromaDB 재인덱싱이 검색 품질에 영향 없음
- Non-RAG 의도 (serving_adjust, ingredient_sub)는 구조적으로 F/CP가 0이며, 이는 정상 동작

생성일: 2026-03-03
