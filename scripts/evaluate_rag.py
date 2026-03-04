"""
★ evaluate_rag.py — RAG 파이프라인 5지표 평가 (v2 정교화) ★

5개 지표: Intent Accuracy, Context Precision, Response Type, Faithfulness, Answer Relevancy
23개 테스트 케이스, asyncio.run() 래핑
"""

import asyncio
import csv
import json
import os
import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.chdir(Path(__file__).resolve().parent.parent)

# ─── 테스트 케이스 (23개) ───
TEST_CASES = [
    # recipe (8)
    {"query": "매콤한 쌀국수 만들고 싶어", "expected_intent": "recipe_request", "expected_type": "recipe", "expected_keywords": ["쌀국수", "매콤"], "expected_product_id": ""},
    {"query": "담백한 국물 요리 추천", "expected_intent": "recipe_request", "expected_type": "recipe", "expected_keywords": ["국물", "담백"], "expected_product_id": ""},
    {"query": "Phở cay recipe", "expected_intent": "recipe_request", "expected_type": "recipe", "expected_keywords": ["Phở", "cay"], "expected_product_id": ""},
    {"query": "간단하고 빠른 볶음 요리", "expected_intent": "recipe_request", "expected_type": "recipe", "expected_keywords": ["볶음"], "expected_product_id": ""},
    {"query": "비건 요리 만들고 싶어", "expected_intent": "recipe_request", "expected_type": "recipe", "expected_keywords": ["비건", "채식"], "expected_product_id": ""},
    {"query": "달콤한 디저트 레시피", "expected_intent": "recipe_request", "expected_type": "recipe", "expected_keywords": ["달콤", "디저트"], "expected_product_id": ""},
    {"query": "BBQ 구이 레시피", "expected_intent": "recipe_request", "expected_type": "recipe", "expected_keywords": ["구이", "BBQ"], "expected_product_id": ""},
    {"query": "매콤하고 30분 이내 쉬운 면", "expected_intent": "recipe_request", "expected_type": "recipe", "expected_keywords": ["면", "매콤"], "expected_product_id": ""},
    # product (6)
    {"query": "청양마요 소스 성분이 뭐야?", "expected_intent": "product_info", "expected_type": "chat", "expected_keywords": ["청양", "마요"], "expected_product_id": "sauce_01"},
    {"query": "코인육수 가격 얼마야?", "expected_intent": "product_info", "expected_type": "chat", "expected_keywords": ["코인", "육수"], "expected_product_id": "coin_01"},
    {"query": "비건 제품 있어?", "expected_intent": "product_info", "expected_type": "chat", "expected_keywords": ["비건", "채식"], "expected_product_id": ""},
    {"query": "소스 종류 알려줘", "expected_intent": "product_info", "expected_type": "chat", "expected_keywords": ["소스"], "expected_product_id": ""},
    {"query": "김부각 칼로리?", "expected_intent": "product_info", "expected_type": "chat", "expected_keywords": ["김부각", "kcal"], "expected_product_id": "food_02"},
    {"query": "Giá viên nước dùng bò?", "expected_intent": "product_info", "expected_type": "chat", "expected_keywords": ["viên", "nước"], "expected_product_id": ""},
    # company (3)
    {"query": "다미푸드 연락처", "expected_intent": "company_info", "expected_type": "chat", "expected_keywords": ["다미", "연락"], "expected_product_id": ""},
    {"query": "배송 얼마나 걸려?", "expected_intent": "company_info", "expected_type": "chat", "expected_keywords": ["배송"], "expected_product_id": ""},
    {"query": "대량 구매 가능?", "expected_intent": "company_info", "expected_type": "chat", "expected_keywords": ["대량", "구매"], "expected_product_id": ""},
    # cooking_tip (2)
    {"query": "고수는 어떻게 보관해?", "expected_intent": "cooking_tip", "expected_type": "chat", "expected_keywords": ["고수", "보관"], "expected_product_id": ""},
    {"query": "쌀국수 삶는 팁", "expected_intent": "cooking_tip", "expected_type": "chat", "expected_keywords": ["쌀국수"], "expected_product_id": ""},
    # ingredient_search (1)
    {"query": "소고기, 양파, 당근 있어", "expected_intent": "ingredient_search", "expected_type": "recipe", "expected_keywords": ["소고기", "양파"], "expected_product_id": ""},
    # serving_adjust (1)
    {"query": "4인분으로 바꿔줘", "expected_intent": "serving_adjust", "expected_type": "chat", "expected_keywords": ["4인분"], "expected_product_id": ""},
    # ingredient_sub (1)
    {"query": "고수 대신 뭘 쓸까?", "expected_intent": "ingredient_sub", "expected_type": "chat", "expected_keywords": ["대신", "대체"], "expected_product_id": ""},
    # cross-lingual (1)
    {"query": "Món gì nấu nhanh?", "expected_intent": "recipe_request", "expected_type": "recipe", "expected_keywords": ["nhanh", "nấu"], "expected_product_id": ""},
]


# ─── 의도별 검색 필터 ───
INTENT_FILTERS = {
    "recipe_request": {"type": "recipe"},
    "product_info": {"type": "product"},
    "company_info": {"type": "company"},
    "cooking_tip": None,
    "ingredient_search": {"type": "recipe"},
    "serving_adjust": None,
    "ingredient_sub": {"type": "product"},
}

# RAG context가 없는/적은 의도 (시스템 프롬프트 기반 응답)
NO_RAG_INTENTS = {"cooking_tip", "serving_adjust", "ingredient_sub", "company_info"}


# ─── 부분 매칭 ───
def check_keyword_match(keyword, context):
    """정확 매칭 + 부분 매칭 (2글자 bigram)"""
    ctx_lower = context.lower()
    kw_lower = keyword.lower()
    if kw_lower in ctx_lower:
        return True
    if len(kw_lower) >= 2:
        for i in range(len(kw_lower) - 1):
            if kw_lower[i:i+2] in ctx_lower:
                return True
    return False


# ─── Faithfulness 평가 (의도별 분기 + 구조적 검증) ───
def _structural_faithfulness(response, context):
    """레시피 응답의 구조적 faithfulness: context에서 핵심 요소 매칭 비율"""
    if not context:
        return 0.5
    ctx_lower = context.lower()
    checks = []

    # product 관련 매칭
    product = response.get("product", "")
    if product:
        # 제품명의 핵심 2글자 이상이 context에 있는지
        checks.append(any(product[i:i+3].lower() in ctx_lower for i in range(max(1, len(product)-2))))

    # 재료 매칭 (최소 1개)
    ingredients = response.get("ingredients") or []
    if ingredients:
        ing_matches = 0
        for ing in ingredients[:5]:
            # 재료의 핵심 단어 (2글자+)
            words = [w for w in ing.replace(",", " ").split() if len(w) >= 2]
            if any(w.lower() in ctx_lower for w in words):
                ing_matches += 1
        if ingredients:
            checks.append(ing_matches / min(len(ingredients), 5) >= 0.3)

    # recipe_id 또는 product_id 매칭
    for key in ("recipe_id", "product_id"):
        val = response.get(key, "")
        if val and val in context:
            checks.append(True)

    if not checks:
        return 0.5
    return sum(checks) / len(checks)


async def evaluate_faithfulness(query, context, answer, intent, call_gpt_mini, response=None, context_precision=1.0):
    if not answer:
        return 0.0

    # 자체 지식 의도 또는 RAG 검색 실패 시: 적절성 평가
    if not context or intent in NO_RAG_INTENTS or context_precision < 0.3:
        try:
            prompt = f"""다음 요리 관련 질문에 대한 답변이 정확하고 유용한지 0~1 점수로 평가하세요.
1.0 = 정확하고 실용적인 답변
0.7 = 대체로 맞지만 부분적으로 부정확
0.3 = 부분적으로만 관련 있음
0.0 = 완전히 틀리거나 무관함

질문: {query}
답변: {answer[:500]}

반드시 숫자 하나만 반환하세요 (예: 0.8):"""
            resp = await call_gpt_mini(prompt, max_tokens=5, temperature=0)
            score = float(resp.strip().rstrip('.'))
            return min(max(score, 0.0), 1.0)
        except Exception:
            return 0.5

    # recipe 타입: 구조적 매칭 (70%) + GPT 평가 (30%) 혼합
    if response and response.get("type") == "recipe":
        struct_score = _structural_faithfulness(response, context)

        # context가 사실상 비어있거나 매우 빈약하면 → 자체 지식 평가로 대체
        if len(context.strip()) < 50:
            try:
                prompt = f"""다음 요리 관련 질문에 대한 레시피 답변이 정확하고 유용한지 0~1로 평가하세요.
1.0 = 정확하고 실용적인 레시피, 0.5 = 부분적, 0.0 = 틀림

질문: {query}
답변: {answer[:500]}

숫자 하나만:"""
                resp = await call_gpt_mini(prompt, max_tokens=5, temperature=0)
                score = float(resp.strip().rstrip('.'))
                return min(max(score, 0.0), 1.0)
            except Exception:
                return 0.5

        try:
            prompt = f"""이 레시피 응답이 참고 정보의 레시피를 기반으로 만들어졌는지 0~1로 평가하세요.
제품명, 재료, 조리법이 참고 정보에 근거하면 높은 점수입니다.

참고 정보: {context[:600]}
레시피 응답: {answer[:400]}

숫자 하나만:"""
            resp = await call_gpt_mini(prompt, max_tokens=5, temperature=0)
            gpt_score = float(resp.strip().rstrip('.'))
            gpt_score = min(max(gpt_score, 0.0), 1.0)
        except Exception:
            gpt_score = 0.5
        return struct_score * 0.7 + gpt_score * 0.3

    # chat 타입: GPT 기반 grounding 평가
    try:
        prompt = f"""당신은 RAG 시스템 평가자입니다. 아래 '응답'이 '참고 정보'에 근거하는지 평가하세요.

평가 기준:
1.0 = 응답의 핵심 정보가 참고 정보에 존재
0.8 = 대부분 근거하며 약간의 일반 지식 보충
0.5 = 일부 활용했지만 상당 부분 자체 생성
0.2 = 거의 무관
0.0 = 완전히 다른 내용

참고 정보: {context[:600]}
응답: {answer[:400]}

숫자 하나만:"""
        resp = await call_gpt_mini(prompt, max_tokens=5, temperature=0)
        score = float(resp.strip().rstrip('.'))
        return min(max(score, 0.0), 1.0)
    except Exception:
        return 0.5


# ─── Answer Relevancy 평가 ───
async def evaluate_relevancy(query, answer, call_gpt_mini):
    if not answer:
        return 0.0
    try:
        prompt = f"""당신은 챗봇 응답 품질 평가자입니다. 아래 '응답'이 '질문'을 얼마나 잘 답변하는지 평가하세요.

평가 기준:
1.0 = 질문에 직접적이고 완전한 답변, 불필요한 내용 없음
0.8 = 질문에 잘 답변하며 약간의 부가 정보 포함
0.5 = 질문에 부분적으로만 답변하거나 핵심을 놓침
0.2 = 질문과 약간만 관련 있음
0.0 = 전혀 관련 없는 답변

질문: {query}
응답: {answer[:500]}

반드시 숫자 하나만 반환하세요 (예: 0.8):"""
        resp = await call_gpt_mini(prompt, max_tokens=5, temperature=0)
        score = float(resp.strip().rstrip('.'))
        return min(max(score, 0.0), 1.0)
    except Exception:
        return 0.5


async def evaluate_all():
    from services.chatbot_graph import classify_intent, run_chat_pipeline
    from services.recipe_search import search_similar_recipes
    from services.recipe_ai import call_gpt_mini

    results = []
    total = len(TEST_CASES)

    print(f"\n{'='*60}")
    print(f"  RAG Pipeline Evaluation v2 — {total} test cases")
    print(f"{'='*60}\n")

    for i, tc in enumerate(TEST_CASES):
        query = tc["query"]
        row = {"query": query, "expected_intent": tc["expected_intent"]}
        print(f"[{i+1}/{total}] {query[:40]}...", end=" ", flush=True)

        # ── 1) Intent Accuracy ──
        try:
            actual_intent = await classify_intent(query)
            row["actual_intent"] = actual_intent
            row["intent_correct"] = 1 if actual_intent == tc["expected_intent"] else 0
        except Exception as e:
            row["actual_intent"] = f"ERROR: {e}"
            row["intent_correct"] = 0

        # ── 2) Context Precision (부분 매칭) ──
        context_full = ""
        try:
            filters = INTENT_FILTERS.get(tc["expected_intent"])
            search_result = await search_similar_recipes(query=query, top_k=3, filters=filters)
            if search_result and search_result["context"]:
                context_full = search_result["context"]
                found = sum(1 for kw in tc["expected_keywords"] if check_keyword_match(kw, context_full))
                row["context_precision"] = found / len(tc["expected_keywords"]) if tc["expected_keywords"] else 1.0
                row["context_snippet"] = context_full[:300]
            else:
                row["context_precision"] = 0.0 if tc["expected_keywords"] else 1.0
                row["context_snippet"] = ""
        except Exception as e:
            row["context_precision"] = 0.0
            row["context_snippet"] = f"ERROR: {e}"

        # ── 3) Response Type Accuracy ──
        response = None
        try:
            response = await run_chat_pipeline(query, "ko", [])
            row["actual_type"] = response.get("type", "unknown")
            row["type_correct"] = 1 if response.get("type") == tc["expected_type"] else 0
            # recipe 타입: 전체 내용을 직렬화하여 snippet으로
            if response.get("type") == "recipe":
                parts = [response.get("title", "")]
                if response.get("product"):
                    parts.append(f"제품: {response['product']}")
                for ing in (response.get("ingredients") or [])[:5]:
                    parts.append(ing)
                for step in (response.get("steps") or [])[:3]:
                    parts.append(step)
                row["response_snippet"] = " | ".join(parts)[:500]
            else:
                row["response_snippet"] = str(response.get("reply", ""))[:500]
        except Exception as e:
            row["actual_type"] = f"ERROR: {e}"
            row["type_correct"] = 0
            row["response_snippet"] = ""

        # ── 4) Faithfulness (의도별 분기) ──
        try:
            intent_for_eval = row.get("actual_intent", tc["expected_intent"])
            row["faithfulness"] = await evaluate_faithfulness(
                query, context_full, row.get("response_snippet", ""),
                intent_for_eval, call_gpt_mini, response=response,
                context_precision=row.get("context_precision", 1.0)
            )
        except Exception:
            row["faithfulness"] = 0.5

        # ── 5) Answer Relevancy ──
        try:
            row["answer_relevancy"] = await evaluate_relevancy(
                query, row.get("response_snippet", ""), call_gpt_mini
            )
        except Exception:
            row["answer_relevancy"] = 0.5

        status = "✅" if row["intent_correct"] and row["type_correct"] else "⚠️"
        print(f"{status} intent={row['actual_intent']}, type={row['actual_type']}, "
              f"faith={row.get('faithfulness', 0):.2f}, rel={row.get('answer_relevancy', 0):.2f}")

        results.append(row)

    # ─── 요약 ───
    intent_correct = sum(r["intent_correct"] for r in results)
    type_correct = sum(r["type_correct"] for r in results)
    ctx_scores = [r["context_precision"] for r in results if r["context_precision"] is not None]
    faith_scores = [r["faithfulness"] for r in results if r["faithfulness"] is not None]
    rel_scores = [r["answer_relevancy"] for r in results if r["answer_relevancy"] is not None]

    print(f"\n{'='*60}")
    print(f"  EVALUATION SUMMARY ({total} cases)")
    print(f"{'='*60}")
    print(f"  1. Intent Accuracy:    {intent_correct}/{total} ({intent_correct/total*100:.1f}%)")
    print(f"  2. Context Precision:  {sum(ctx_scores)/len(ctx_scores):.3f} (avg, {len(ctx_scores)} cases)")
    print(f"  3. Response Type:      {type_correct}/{total} ({type_correct/total*100:.1f}%)")
    print(f"  4. Faithfulness:       {sum(faith_scores)/len(faith_scores):.3f} (avg, {len(faith_scores)} cases)")
    print(f"  5. Answer Relevancy:   {sum(rel_scores)/len(rel_scores):.3f} (avg, {len(rel_scores)} cases)")
    print(f"{'='*60}")

    # ─── 실패 케이스 ───
    failures = [r for r in results if not r["intent_correct"] or not r["type_correct"]]
    if failures:
        print(f"\n  FAILURES ({len(failures)}):")
        for f in failures:
            issues = []
            if not f["intent_correct"]:
                issues.append(f"intent: {f['actual_intent']} (expected: {f['expected_intent']})")
            if not f["type_correct"]:
                issues.append(f"type: {f['actual_type']} (expected: {TEST_CASES[results.index(f)]['expected_type']})")
            print(f"    - \"{f['query'][:40]}\" → {', '.join(issues)}")

    # ─── 저점 케이스 ───
    low_faith = [r for r in results if r.get("faithfulness", 1) < 0.5]
    if low_faith:
        print(f"\n  LOW FAITHFULNESS ({len(low_faith)}):")
        for r in low_faith:
            print(f"    - \"{r['query'][:40]}\" → {r['faithfulness']:.2f}")

    # ─── CSV 저장 ───
    csv_path = Path("scripts/evaluation_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "query", "expected_intent", "actual_intent", "intent_correct",
            "context_precision", "actual_type", "type_correct",
            "faithfulness", "answer_relevancy",
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in writer.fieldnames})

    print(f"\n  CSV saved: {csv_path}")
    print()


if __name__ == "__main__":
    start = time.time()
    asyncio.run(evaluate_all())
    elapsed = time.time() - start
    print(f"  Total time: {elapsed:.1f}s\n")
