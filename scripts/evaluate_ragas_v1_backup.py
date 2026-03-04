"""RAGAS 품질 평가 스크립트 (STEP 16)
====================================
역할: Faithfulness, ContextPrecision, AnswerRelevancy를
      RAGAS 프레임워크(arXiv:2309.15217)로 측정.

기능 통합 테스트(Intent/Type)는 scripts/evaluate_rag.py에서 수행합니다.

실행: python3 scripts/evaluate_ragas.py
"""

import asyncio
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
from ragas.embeddings.base import embedding_factory
from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
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


def _extract_reply(response: dict) -> str:
    """응답에서 텍스트 reply 추출"""
    if response.get("type") == "recipe":
        parts = []
        if response.get("title"):
            parts.append(f"제목: {response['title']}")
        if response.get("title_vn"):
            parts.append(f"베트남어: {response['title_vn']}")
        if response.get("ingredients"):
            parts.append(f"재료: {response['ingredients']}")
        if response.get("steps"):
            parts.append(f"조리법: {response['steps']}")
        if response.get("product"):
            parts.append(f"추천 제품: {response['product']}")
        if response.get("reply"):
            parts.append(response["reply"])
        return "\n".join(parts) if parts else json.dumps(response, ensure_ascii=False)
    else:
        return response.get("reply", "") or json.dumps(response, ensure_ascii=False)


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

            reply_text = _extract_reply(response)
            rag_context = debug.get("rag_context", "")

            # RAG context를 문서 단위로 분리
            contexts = []
            if rag_context:
                parts = rag_context.split("\n[")
                for part in parts:
                    cleaned = part.strip()
                    if cleaned:
                        if not cleaned.startswith("["):
                            cleaned = "[" + cleaned
                        contexts.append(cleaned)

            if not contexts:
                contexts = ["(컨텍스트 없음)"]

            samples.append({
                "query": query,
                "response": reply_text,
                "contexts": contexts,
                "intent": debug.get("intent", ""),
                "actual_type": response.get("type", ""),
                "expected_intent": tc["expected_intent"],
                "expected_type": tc["expected_type"],
            })
            print(f"✅ ({len(contexts)} contexts, {len(reply_text)} chars)")

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


async def run_ragas_evaluation(samples: list[dict]) -> list[dict]:
    """RAGAS 프레임워크로 품질 평가 — per-sample ascore() 사용"""
    print(f"\n{'='*60}")
    print(f"  Phase 2: RAGAS 평가 실행")
    print(f"{'='*60}\n")

    # LLM & Embeddings 설정 (모두 AsyncOpenAI 사용)
    async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    evaluator_llm = llm_factory("gpt-4.1-mini", client=async_client)
    evaluator_llm.model_args["max_tokens"] = 4096  # 긴 레시피 응답의 statement 생성에 필요
    evaluator_embeddings = embedding_factory(
        "openai", model="text-embedding-3-small", client=async_client
    )

    # 메트릭 인스턴스
    faith_metric = Faithfulness(llm=evaluator_llm)
    ar_metric = AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings)
    cp_metric = ContextPrecisionWithoutReference(llm=evaluator_llm)

    total = len(samples)
    scored = []

    for i, s in enumerate(samples):
        query = s["query"]
        print(f"  [{i+1}/{total}] {query[:35]}...", end=" ", flush=True)

        try:
            # Faithfulness: (user_input, response, retrieved_contexts)
            faith_result = await faith_metric.ascore(
                user_input=s["query"],
                response=s["response"],
                retrieved_contexts=s["contexts"],
            )
            faith_val = float(faith_result)
        except Exception as e:
            print(f"[Faith ERR: {e}]", end=" ")
            faith_val = 0.0

        try:
            # ContextPrecision: (user_input, response, retrieved_contexts)
            cp_result = await cp_metric.ascore(
                user_input=s["query"],
                response=s["response"],
                retrieved_contexts=s["contexts"],
            )
            cp_val = float(cp_result)
        except Exception as e:
            print(f"[CP ERR: {e}]", end=" ")
            cp_val = 0.0

        try:
            # AnswerRelevancy: (user_input, response) — no contexts needed
            ar_result = await ar_metric.ascore(
                user_input=s["query"],
                response=s["response"],
            )
            ar_val = float(ar_result)
        except Exception as e:
            print(f"[AR ERR: {e}]", end=" ")
            ar_val = 0.0

        scored.append({
            "faithfulness": round(faith_val, 3),
            "context_precision": round(cp_val, 3),
            "answer_relevancy": round(ar_val, 3),
        })
        print(f"F={faith_val:.2f} CP={cp_val:.2f} AR={ar_val:.2f}")

    return scored


def print_results(samples: list[dict], scores: list[dict], baseline_path: str = "baseline_results.json"):
    """결과 출력 및 Before/After 비교"""
    total = len(samples)

    print(f"\n{'='*60}")
    print(f"  RAGAS 품질 평가 결과")
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
    intent_pass = sum(1 for s in samples if s["intent"] == s["expected_intent"])
    type_pass = sum(1 for s in samples if s["actual_type"] == s["expected_type"])

    print(f"\n  {'AVERAGE':<35} {avg_faith:>7.3f} {avg_cp:>7.3f} {avg_ar:>7.3f}")
    print(f"\n  Intent 정확도: {intent_pass}/{total} ({intent_pass/total:.1%})")
    print(f"  Type 정확도:   {type_pass}/{total} ({type_pass/total:.1%})")

    # ─── Before/After 비교표 ───
    baseline = {}
    if Path(baseline_path).exists():
        baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))

    if baseline:
        bl = baseline.get("summary", {})
        print(f"\n{'='*60}")
        print(f"  Before (Baseline) vs After (Final) 비교")
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
        "test_type": "ragas_quality_evaluation",
        "ragas_version": "0.4.3",
        "evaluator_model": "gpt-4.1-mini",
        "total_cases": total,
        "summary": {
            "intent_accuracy": f"{intent_pass}/{total} ({intent_pass/total:.1%})",
            "intent_accuracy_pct": round(intent_pass/total*100, 1),
            "response_type_accuracy": f"{type_pass}/{total} ({type_pass/total:.1%})",
            "response_type_accuracy_pct": round(type_pass/total*100, 1),
            "faithfulness": round(avg_faith, 3),
            "context_precision": round(avg_cp, 3),
            "answer_relevancy": round(avg_ar, 3),
        },
        "per_case": per_case,
    }

    json_path = Path("scripts/ragas_evaluation_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON saved: {json_path}")

    # CSV 저장
    csv_path = Path("scripts/ragas_evaluation_results.csv")
    import csv
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=per_case[0].keys())
        writer.writeheader()
        writer.writerows(per_case)
    print(f"  CSV saved: {csv_path}")

    return results_summary


async def main():
    # Phase 1: 파이프라인 실행으로 샘플 수집
    samples = await collect_samples()

    # Phase 2: RAGAS 평가 (per-sample)
    scores = await run_ragas_evaluation(samples)

    # Phase 3: 결과 출력 및 비교
    print_results(samples, scores)


if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    elapsed = time.time() - start
    print(f"\n  Total time: {elapsed:.1f}s\n")
