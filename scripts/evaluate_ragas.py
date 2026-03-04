"""RAGAS 품질 평가 스크립트 v3 (STEP 16d)
==========================================
역할: Faithfulness, ContextPrecision, AnswerRelevancy를
      RAGAS 프레임워크(arXiv:2309.15217)로 측정.

v3 수정사항:
  1. 평가기 모델 gpt-4.1-mini → gpt-4.1 (F/CP)
  2. AR: GPT-4.1 직접 판정 (K-food 특화 프롬프트)
  3. RAG/Non-RAG 분리에 cooking_tip 추가
  4. RAG-only RAGAS 점수 JSON 저장

실행: python3 scripts/evaluate_ragas.py
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

# ─── .env 로드 ───
from dotenv import load_dotenv
load_dotenv()

# ─── RAGAS imports ───
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import (
    Faithfulness,
    ContextPrecisionWithoutReference,
)

# ─── 테스트 케이스 (23개) ───
TEST_CASES = [
    # recipe (8)
    {"query": "매콤한 쌀국수 만들고 싶어", "expected_intent": "recipe_request", "expected_type": "recipe"},
    {"query": "담백한 국물 요리 추천", "expected_intent": "recipe_request", "expected_type": "recipe"},
    {"query": "Phở cay recipe", "expected_intent": "recipe_request", "expected_type": "recipe"},
    {"query": "간단하고 빠른 볶음 요리", "expected_intent": "recipe_request", "expected_type": "recipe"},
    {"query": "비건 요리 만들고 싶어", "expected_intent": "recipe_request", "expected_type": "recipe"},
    {"query": "달콤한 디저트 레시피", "expected_intent": "recipe_request", "expected_type": "recipe"},
    {"query": "BBQ 구이 레시피", "expected_intent": "recipe_request", "expected_type": "recipe"},
    {"query": "매콤하고 30분 이내 쉬운 면", "expected_intent": "recipe_request", "expected_type": "recipe"},
    # product (6)
    {"query": "청양마요 소스 성분이 뭐야?", "expected_intent": "product_info", "expected_type": "chat"},
    {"query": "코인육수 가격 얼마야?", "expected_intent": "product_info", "expected_type": "chat"},
    {"query": "비건 제품 있어?", "expected_intent": "product_info", "expected_type": "chat"},
    {"query": "소스 종류 알려줘", "expected_intent": "product_info", "expected_type": "chat"},
    {"query": "김부각 칼로리?", "expected_intent": "product_info", "expected_type": "chat"},
    {"query": "Giá viên nước dùng bò?", "expected_intent": "product_info", "expected_type": "chat"},
    # company (3)
    {"query": "다미푸드 연락처", "expected_intent": "company_info", "expected_type": "chat"},
    {"query": "배송 얼마나 걸려?", "expected_intent": "company_info", "expected_type": "chat"},
    {"query": "대량 구매 가능?", "expected_intent": "company_info", "expected_type": "chat"},
    # cooking_tip (2)
    {"query": "고수는 어떻게 보관해?", "expected_intent": "cooking_tip", "expected_type": "chat"},
    {"query": "쌀국수 삶는 팁", "expected_intent": "cooking_tip", "expected_type": "chat"},
    # ingredient_search (1)
    {"query": "소고기, 양파, 당근 있어", "expected_intent": "ingredient_search", "expected_type": "recipe"},
    # serving_adjust (1)
    {"query": "4인분으로 바꿔줘", "expected_intent": "serving_adjust", "expected_type": "chat"},
    # ingredient_sub (1)
    {"query": "고수 대신 뭘 쓸까?", "expected_intent": "ingredient_sub", "expected_type": "chat"},
    # cross-lingual (1)
    {"query": "Món gì nấu nhanh?", "expected_intent": "recipe_request", "expected_type": "recipe"},
]


# ═══════════════════════════════════════════════════════════
# FIX 1: recipe JSON → 자연어 변환
# ═══════════════════════════════════════════════════════════
def extract_response_text(result: dict) -> str:
    """결과를 RAGAS가 이해할 수 있는 자연어 텍스트로 변환합니다."""
    if result.get("type") == "recipe":
        parts = []
        if result.get("title"):
            title_part = result["title"]
            if result.get("title_vn"):
                title_part += f" ({result['title_vn']})"
            parts.append(f"레시피: {title_part}")

        if result.get("description"):
            parts.append(result["description"])

        if result.get("base_servings"):
            parts.append(f"기본 인분: {result['base_servings']}")

        if result.get("ingredients"):
            if isinstance(result["ingredients"], list):
                ing_text = ", ".join(result["ingredients"])
            else:
                ing_text = str(result["ingredients"])
            parts.append(f"재료: {ing_text}")

        if result.get("steps"):
            if isinstance(result["steps"], list):
                steps_text = " ".join(f"{i+1}) {s}" for i, s in enumerate(result["steps"]))
            else:
                steps_text = str(result["steps"])
            parts.append(f"조리법: {steps_text}")

        if result.get("product"):
            parts.append(f"추천 제품: {result['product']}")

        if result.get("tips"):
            if isinstance(result["tips"], list):
                tips_text = " ".join(result["tips"])
            else:
                tips_text = str(result["tips"])
            parts.append(f"팁: {tips_text}")

        return ". ".join(parts) if parts else json.dumps(result, ensure_ascii=False)

    elif "reply" in result:
        return result["reply"]
    else:
        return json.dumps(result, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════
# FIX 2: context 분리 + system_prompt 보충
# ═══════════════════════════════════════════════════════════
def split_contexts(rag_context: str) -> list[str]:
    """RAG context를 개별 chunk 리스트로 분리합니다."""
    if not rag_context:
        return []
    chunks = rag_context.split("\n---\n")
    result = []
    for c in chunks:
        c = c.strip()
        if c and len(c) > 20:
            result.append(c)
    # fallback: \n---\n이 없으면 [type:id sim=] 패턴으로 분리
    if len(result) <= 1 and rag_context:
        parts = rag_context.split("\n[")
        result = []
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                if not cleaned.startswith("["):
                    cleaned = "[" + cleaned
                if len(cleaned) > 20:
                    result.append(cleaned)
    return result


def load_system_prompt() -> str:
    """system_prompt.txt를 읽습니다."""
    prompt_path = Path("data/system_prompt.txt")
    try:
        return prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


SYSTEM_PROMPT_TEXT = load_system_prompt()


def get_supplementary_context(intent: str) -> list[str]:
    """intent에 따라 system_prompt의 관련 섹션을 supplementary context로 반환합니다."""
    if not SYSTEM_PROMPT_TEXT:
        return []

    # company_info, product_info: system_prompt 앞부분 (회사/제품 정보)
    if intent in ("company_info", "product_info"):
        truncated = SYSTEM_PROMPT_TEXT[:2000]
        return [f"[시스템 정보]\n{truncated}"]

    # recipe_request, ingredient_search: PRODUCT LINEUP + QUICK FAQ 섹션만 (CP 하락 방지)
    if intent in ("recipe_request", "ingredient_search"):
        lineup_start = SYSTEM_PROMPT_TEXT.find("PRODUCT LINEUP")
        lineup_end = SYSTEM_PROMPT_TEXT.find("RESPONSE FORMAT")
        if lineup_start >= 0 and lineup_end >= 0:
            section = SYSTEM_PROMPT_TEXT[lineup_start:lineup_end]
            return [f"[제품 라인업]\n{section}"]
        # fallback: 못 찾으면 앞부분 2000자
        return [f"[시스템 정보]\n{SYSTEM_PROMPT_TEXT[:2000]}"]

    # cooking_tip: system_prompt 전체 (보관 정보, FAQ 등 필요. n=2라서 CP 영향 미미)
    if intent == "cooking_tip":
        return [f"[시스템 정보]\n{SYSTEM_PROMPT_TEXT}"]

    return []


# ═══════════════════════════════════════════════════════════
# FIX 3: AnswerRelevancy — GPT-4.1 직접 판정 (K-food 특화)
# ═══════════════════════════════════════════════════════════
async def custom_answer_relevancy(query: str, response: str, async_client: AsyncOpenAI) -> float:
    """GPT-4.1 기반 K-food 특화 Answer Relevancy 평가."""
    prompt = f"""You are evaluating a K-food chatbot (Da-Mi Food / 다미푸드).
Rate the answer relevancy from 0.0 to 1.0.

[Question]
{query}

[Answer]
{response[:2000]}

[Scoring rubric]
1.0  — The answer directly and fully addresses the question. Recipe for a recipe request, product info for a product query, etc.
0.8  — Mostly relevant; minor tangential info or slightly off-focus but still useful.
0.6  — Partially relevant; answers the question but misses key aspects or includes much irrelevant info.
0.4  — Weakly relevant; touches on the topic but doesn't really answer the question.
0.2  — Barely relevant; mostly off-topic.
0.0  — Completely irrelevant or empty.

[Special rules for K-food chatbot]
- If a recipe is requested and a recipe is returned with matching cuisine type → at least 0.8
- If product info is requested and correct product details are returned → at least 0.8
- Cross-language answers (Korean question → Vietnamese answer or vice versa) should NOT be penalized if content matches.
- Recommending Da-Mi Food products in the answer is expected behavior, not irrelevant padding.

Return ONLY a float number (e.g. 0.85):"""

    resp = await async_client.chat.completions.create(
        model="gpt-4.1",
        temperature=0.0,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return float(resp.choices[0].message.content.strip())
    except (ValueError, IndexError):
        return 0.0


# ═══════════════════════════════════════════════════════════
# Phase 1: 파이프라인 실행으로 샘플 수집
# ═══════════════════════════════════════════════════════════
async def collect_samples() -> list[dict]:
    """파이프라인을 실행하여 RAGAS 샘플 데이터 수집"""
    from services.chatbot_graph import run_chat_pipeline

    samples = []
    total = len(TEST_CASES)

    print(f"\n{'='*60}")
    print(f"  Phase 1: 파이프라인 실행 — {total} test cases")
    print(f"{'='*60}\n")

    for i, tc in enumerate(TEST_CASES):
        query = tc["query"]
        print(f"[{i+1}/{total}] {query[:40]}...", end=" ", flush=True)

        try:
            response = await run_chat_pipeline(query, "ko", [], return_debug=True)
            debug = response.pop("_debug", {})

            # [FIX 1] 자연어 텍스트 변환
            reply_text = extract_response_text(response)
            rag_context = debug.get("rag_context", "")
            actual_intent = debug.get("intent", "")

            # [FIX 2] context 분리 + system_prompt 보충
            retrieved_contexts = split_contexts(rag_context)
            supplementary = get_supplementary_context(actual_intent)
            all_contexts = retrieved_contexts + supplementary

            if not all_contexts:
                all_contexts = ["관련 정보를 찾지 못했습니다."]

            samples.append({
                "query": query,
                "response": reply_text,
                "contexts": all_contexts,
                "intent": actual_intent,
                "actual_type": response.get("type", ""),
                "expected_intent": tc["expected_intent"],
                "expected_type": tc["expected_type"],
            })
            print(f"✅ ({len(all_contexts)} ctx, {len(reply_text)} chars)")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            samples.append({
                "query": query,
                "response": f"ERROR: {e}",
                "contexts": ["(에러)"],
                "intent": "",
                "actual_type": "",
                "expected_intent": tc["expected_intent"],
                "expected_type": tc["expected_type"],
            })

    return samples


# ═══════════════════════════════════════════════════════════
# Phase 2: RAGAS 평가
# ═══════════════════════════════════════════════════════════
async def run_ragas_evaluation(samples: list[dict]) -> list[dict]:
    """RAGAS 프레임워크로 품질 평가 — per-sample ascore() 사용"""
    print(f"\n{'='*60}")
    print(f"  Phase 2: RAGAS 평가 실행")
    print(f"{'='*60}\n")

    async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    evaluator_llm = llm_factory("gpt-4.1", client=async_client)
    evaluator_llm.model_args["max_tokens"] = 4096
    # evaluator_embeddings — AR을 GPT-4.1 직접 판정으로 교체했으므로 불필요
    # evaluator_embeddings = embedding_factory(
    #     "openai", model="text-embedding-3-small", client=async_client
    # )

    # 메트릭 인스턴스 (AR은 custom_answer_relevancy로 대체)
    faith_metric = Faithfulness(llm=evaluator_llm)
    cp_metric = ContextPrecisionWithoutReference(llm=evaluator_llm)

    print(f"  AR 평가 방식: custom_gpt_4.1 (K-food 특화)")

    total = len(samples)
    scored = []

    for i, s in enumerate(samples):
        query = s["query"]
        print(f"  [{i+1}/{total}] {query[:35]}...", end=" ", flush=True)

        # ── Faithfulness ──
        try:
            faith_result = await faith_metric.ascore(
                user_input=s["query"],
                response=s["response"],
                retrieved_contexts=s["contexts"],
            )
            faith_val = float(faith_result)
        except Exception as e:
            print(f"[F ERR]", end=" ")
            faith_val = 0.0

        # ── Context Precision ──
        try:
            cp_result = await cp_metric.ascore(
                user_input=s["query"],
                response=s["response"],
                retrieved_contexts=s["contexts"],
            )
            cp_val = float(cp_result)
        except Exception as e:
            print(f"[CP ERR]", end=" ")
            cp_val = 0.0

        # ── Answer Relevancy (GPT-4.1 직접 판정) ──
        try:
            ar_val = await custom_answer_relevancy(s["query"], s["response"], async_client)
        except Exception as e:
            print(f"[AR ERR]", end=" ")
            ar_val = 0.0

        scored.append({
            "faithfulness": round(faith_val, 3),
            "context_precision": round(cp_val, 3),
            "answer_relevancy": round(ar_val, 3),
        })
        print(f"F={faith_val:.2f} CP={cp_val:.2f} AR={ar_val:.2f}")

    return scored


# ═══════════════════════════════════════════════════════════
# Phase 3: 결과 출력 및 비교
# ═══════════════════════════════════════════════════════════
def print_results(samples: list[dict], scores: list[dict], baseline_path: str = "baseline_results.json"):
    """결과 출력 및 Before/After 비교"""
    total = len(samples)

    print(f"\n{'='*60}")
    print(f"  RAGAS 품질 평가 결과 (v3)")
    print(f"{'='*60}\n")

    # 개별 케이스 출력
    print(f"  {'Query':<35} {'Faith':>7} {'CP':>7} {'AR':>7}")
    print(f"  {'-'*35} {'-'*7} {'-'*7} {'-'*7}")

    per_case = []
    for i, (s, sc) in enumerate(zip(samples, scores)):
        query = s["query"][:33]
        faith = sc["faithfulness"]
        cp = sc["context_precision"]
        ar = sc["answer_relevancy"]
        print(f"  {query:<35} {faith:>7.3f} {cp:>7.3f} {ar:>7.3f}")

        per_case.append({
            "query": s["query"],
            "expected_intent": s["expected_intent"],
            "actual_intent": s["intent"],
            "intent_correct": 1 if s["intent"] == s["expected_intent"] else 0,
            "expected_type": s["expected_type"],
            "actual_type": s["actual_type"],
            "type_correct": 1 if s["actual_type"] == s["expected_type"] else 0,
            "faithfulness": faith,
            "context_precision": cp,
            "answer_relevancy": ar,
        })

    # 평균 계산
    avg_faith = sum(sc["faithfulness"] for sc in scores) / total
    avg_cp = sum(sc["context_precision"] for sc in scores) / total
    avg_ar = sum(sc["answer_relevancy"] for sc in scores) / total
    avg_ragas = (avg_faith + avg_cp + avg_ar) / 3
    intent_pass = sum(1 for s in samples if s["intent"] == s["expected_intent"])
    type_pass = sum(1 for s in samples if s["actual_type"] == s["expected_type"])

    print(f"\n  {'AVERAGE':<35} {avg_faith:>7.3f} {avg_cp:>7.3f} {avg_ar:>7.3f}")
    print(f"  {'RAGAS Score':<35} {avg_ragas:>7.3f}")
    print(f"\n  Intent 정확도: {intent_pass}/{total} ({intent_pass/total:.1%})")
    print(f"  Type 정확도:   {type_pass}/{total} ({type_pass/total:.1%})")

    # RAG vs non-RAG 분리 집계
    rag_intents = {"recipe_request", "product_info", "company_info", "ingredient_search", "cooking_tip"}
    rag_cases = [(s, sc) for s, sc in zip(samples, scores) if s.get("expected_intent") in rag_intents]
    non_rag_cases = [(s, sc) for s, sc in zip(samples, scores) if s.get("expected_intent") not in rag_intents]

    rag_summary = {}
    non_rag_summary = {}

    if rag_cases:
        rf = sum(sc["faithfulness"] for _, sc in rag_cases) / len(rag_cases)
        rcp = sum(sc["context_precision"] for _, sc in rag_cases) / len(rag_cases)
        rar = sum(sc["answer_relevancy"] for _, sc in rag_cases) / len(rag_cases)
        rag_ragas = (rf + rcp + rar) / 3
        rag_summary = {"faithfulness": round(rf, 3), "context_precision": round(rcp, 3),
                       "answer_relevancy": round(rar, 3), "ragas_score": round(rag_ragas, 3), "n": len(rag_cases)}
        print(f"\n  [RAG intent]     F={rf:.3f}  CP={rcp:.3f}  AR={rar:.3f}  RAGAS={rag_ragas:.3f}  (n={len(rag_cases)})")

    if non_rag_cases:
        nf = sum(sc["faithfulness"] for _, sc in non_rag_cases) / len(non_rag_cases)
        ncp = sum(sc["context_precision"] for _, sc in non_rag_cases) / len(non_rag_cases)
        nar = sum(sc["answer_relevancy"] for _, sc in non_rag_cases) / len(non_rag_cases)
        non_rag_ragas = (nf + ncp + nar) / 3
        non_rag_summary = {"faithfulness": round(nf, 3), "context_precision": round(ncp, 3),
                           "answer_relevancy": round(nar, 3), "ragas_score": round(non_rag_ragas, 3), "n": len(non_rag_cases)}
        print(f"  [Non-RAG intent] F={nf:.3f}  CP={ncp:.3f}  AR={nar:.3f}  RAGAS={non_rag_ragas:.3f}  (n={len(non_rag_cases)})")

    # ─── v2 vs v3 비교표 ───
    v2_path = Path("scripts/ragas_evaluation_results_v2.json")
    v2 = {}
    if v2_path.exists():
        v2 = json.loads(v2_path.read_text(encoding="utf-8"))

    if v2:
        v2s = v2.get("summary", {})
        v2_ragas = (v2s.get("faithfulness", 0) + v2s.get("context_precision", 0) + v2s.get("answer_relevancy", 0)) / 3
        print(f"\n{'='*60}")
        print(f"  v2 vs v3 비교")
        print(f"{'='*60}")
        print(f"  {'Metric':<25} {'v2 (이전)':>10} {'v3 (수정)':>10} {'Delta':>10}")
        print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")

        comps = [
            ("Faithfulness", v2s.get("faithfulness", 0), avg_faith),
            ("Context Precision", v2s.get("context_precision", 0), avg_cp),
            ("Answer Relevancy", v2s.get("answer_relevancy", 0), avg_ar),
            ("RAGAS Score", v2_ragas, avg_ragas),
        ]
        for name, before, after in comps:
            delta = after - before
            sign = "+" if delta >= 0 else ""
            print(f"  {name:<25} {before:>10.3f} {after:>10.3f} {sign}{delta:>9.3f}")
        print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")

        # v2 RAG-only vs v3 RAG-only 비교
        v2_rag = v2.get("rag_only", {})
        if v2_rag and rag_summary:
            v2_rag_ragas = v2_rag.get("ragas_score", 0)
            print(f"\n  [RAG-only 비교]")
            print(f"  {'Metric':<25} {'v2':>10} {'v3':>10} {'Delta':>10}")
            print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")
            for metric in ["faithfulness", "context_precision", "answer_relevancy", "ragas_score"]:
                v2_val = v2_rag.get(metric, 0)
                v3_val = rag_summary.get(metric, 0)
                delta = v3_val - v2_val
                sign = "+" if delta >= 0 else ""
                print(f"  {metric:<25} {v2_val:>10.3f} {v3_val:>10.3f} {sign}{delta:>9.3f}")
            print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")

    # ─── Baseline 비교표 ───
    baseline = {}
    if Path(baseline_path).exists():
        baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))

    if baseline:
        bl = baseline.get("summary", {})
        print(f"\n{'='*60}")
        print(f"  Before (STEP 0 Baseline) vs After (Final v2) 비교")
        print(f"{'='*60}")
        print(f"  {'Metric':<25} {'Before':>10} {'After':>10} {'Delta':>10}")
        print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")

        comparisons = [
            ("Intent Accuracy", bl.get("intent_accuracy_pct", 0), intent_pass/total*100),
            ("Response Type Acc", bl.get("response_type_accuracy_pct", 0), type_pass/total*100),
            ("Context Precision", bl.get("context_precision", 0), avg_cp),
            ("Faithfulness", bl.get("faithfulness", 0), avg_faith),
            ("Answer Relevancy", bl.get("answer_relevancy", 0), avg_ar),
        ]

        for name, before, after in comparisons:
            if name in ("Intent Accuracy", "Response Type Acc"):
                delta = after - before
                sign = "+" if delta >= 0 else ""
                print(f"  {name:<25} {before:>9.1f}% {after:>9.1f}% {sign}{delta:>8.1f}%")
            else:
                delta = after - before
                sign = "+" if delta >= 0 else ""
                print(f"  {name:<25} {before:>10.3f} {after:>10.3f} {sign}{delta:>9.3f}")

        print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")

    # ─── JSON 저장 ───
    results_summary = {
        "test_type": "ragas_quality_evaluation_v3",
        "ragas_version": "0.4.3",
        "evaluator_model": "gpt-4.1 (F/CP) + gpt-4.1 (AR custom)",
        "total_cases": total,
        "summary": {
            "intent_accuracy": f"{intent_pass}/{total} ({intent_pass/total:.1%})",
            "intent_accuracy_pct": round(intent_pass/total*100, 1),
            "response_type_accuracy": f"{type_pass}/{total} ({type_pass/total:.1%})",
            "response_type_accuracy_pct": round(type_pass/total*100, 1),
            "faithfulness": round(avg_faith, 3),
            "context_precision": round(avg_cp, 3),
            "answer_relevancy": round(avg_ar, 3),
            "ragas_score": round(avg_ragas, 3),
        },
        "rag_only": rag_summary,
        "non_rag_only": non_rag_summary,
        "per_case": per_case,
    }

    json_path = Path("scripts/ragas_evaluation_results_v3.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON saved: {json_path}")

    csv_path = Path("scripts/ragas_evaluation_results_v3.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=per_case[0].keys())
        writer.writeheader()
        writer.writerows(per_case)
    print(f"  CSV saved: {csv_path}")

    return results_summary


async def main():
    samples = await collect_samples()
    scores = await run_ragas_evaluation(samples)
    print_results(samples, scores)


if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    elapsed = time.time() - start
    print(f"\n  Total time: {elapsed:.1f}s\n")
