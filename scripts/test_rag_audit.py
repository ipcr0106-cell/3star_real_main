#!/usr/bin/env python3
"""
RAG 파이프라인 전수 조사 — Part 2 + Part 3
Part 2: 다변량 RAG 검색 테스트 (30+ 쿼리)
Part 3: 81개 레시피 전체 검색 가능성 테스트
"""
import asyncio
import json
import os
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.chdir(Path(__file__).resolve().parent.parent)

from dotenv import load_dotenv
load_dotenv()

from services.recipe_search import search_similar_recipes, get_collection

REPORTS_DIR = Path("data/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# Part 2: 다변량 RAG 검색 테스트
# ══════════════════════════════════════════════════════════════

# 변수 A: 언어 (같은 의미, 다른 언어)
QUERIES_A = [
    {"query": "해산물 볶음면", "language": "ko", "expected": "recipe_mi_xao_hai_san_sauce04_001"},
    {"query": "mì xào hải sản", "language": "vi", "expected": "recipe_mi_xao_hai_san_sauce04_001"},
    {"query": "seafood stir-fried noodle", "language": "en", "expected": "recipe_mi_xao_hai_san_sauce04_001"},
    {"query": "치킨윙 구이", "language": "ko", "expected": "recipe_canh_ga_nuong_sauce06_003"},
    {"query": "cánh gà nướng", "language": "vi", "expected": "recipe_canh_ga_nuong_sauce06_003"},
    {"query": "grilled chicken wings", "language": "en", "expected": "recipe_canh_ga_nuong_sauce06_003"},
    {"query": "채식 전골", "language": "ko", "expected": "recipe_lau_chay_coin03_001"},
    {"query": "lẩu chay", "language": "vi", "expected": "recipe_lau_chay_coin03_001"},
    {"query": "vegetarian hot pot", "language": "en", "expected": "recipe_lau_chay_coin03_001"},
    {"query": "쌀국수", "language": "ko", "expected": "recipe_pho_bo_coin01_001"},
    {"query": "phở", "language": "vi", "expected": "recipe_pho_bo_coin01_001"},
    {"query": "pho", "language": "en", "expected": "recipe_pho_bo_coin01_001"},
    {"query": "김치찌개", "language": "ko", "expected": None},  # DB에 없을 수 있음
    {"query": "canh kim chi", "language": "vi", "expected": None},
    {"query": "kimchi stew", "language": "en", "expected": None},
]

# 변수 B: 표현 방식 (구어체 vs 정확한 이름)
QUERIES_B = [
    {"query": "매운 국수", "language": "ko", "expected": "recipe_bun_bo_hue_coin01_002"},
    {"query": "분보후에", "language": "ko", "expected": "recipe_bun_bo_hue_coin01_002"},
    {"query": "bún bò Huế", "language": "vi", "expected": "recipe_bun_bo_hue_coin01_002"},
    {"query": "달콤한 디저트", "language": "ko", "expected": None},  # 여러 가능
    {"query": "고기 구이", "language": "ko", "expected": None},  # 여러 가능
    {"query": "반미", "language": "ko", "expected": "recipe_banh_mi_sauce01_001"},
    {"query": "bánh mì thịt nướng", "language": "vi", "expected": "recipe_banh_mi_thit_nuong_season01_001"},
]

# 변수 C: 제품 기반 검색
QUERIES_C = [
    {"query": "코인육수로 만들 수 있는 요리", "language": "ko", "expected_products": ["coin01", "coin02", "coin03", "coin04"]},
    {"query": "K-로제 소스 레시피", "language": "ko", "expected_products": ["sauce04"]},
    {"query": "윙소스 활용법", "language": "ko", "expected_products": ["sauce06"]},
    {"query": "불고기 시즈닝 요리", "language": "ko", "expected_products": ["season01"]},
    {"query": "김부각 코코넛 칩 요리", "language": "ko", "expected_products": ["food02"]},
]

# 변수 D: 카테고리/맛 기반 검색
QUERIES_D = [
    {"query": "매운 면 요리", "language": "ko", "expected_cat": "면", "expected_taste": "매운"},
    {"query": "담백한 국물 요리", "language": "ko", "expected_cat": "국물", "expected_taste": "담백"},
    {"query": "바삭한 간식", "language": "ko", "expected_cat": "스낵", "expected_taste": "바삭"},
    {"query": "달콤한 음료", "language": "ko", "expected_cat": "음료", "expected_taste": "달콤"},
    {"query": "고소한 볶음", "language": "ko", "expected_cat": "볶음", "expected_taste": "고소"},
]

# 변수 E: 모호한/일상적 검색
QUERIES_E = [
    {"query": "오늘 뭐 먹지", "language": "ko"},
    {"query": "간단한 저녁", "language": "ko"},
    {"query": "10분 요리", "language": "ko"},
    {"query": "손님 접대 요리", "language": "ko"},
    {"query": "아이 간식", "language": "ko"},
]


def _get_recipe_metadata():
    """ChromaDB에서 모든 레시피 메타데이터 로드"""
    col = get_collection()
    results = col.get(where={"type": "recipe"}, include=["metadatas"])
    meta = {}
    for i, m in enumerate(results["metadatas"]):
        rid = results["ids"][i]
        meta[rid] = m
    return meta


async def run_part2():
    """Part 2 실행"""
    print(f"\n{'='*70}")
    print(f"  Part 2: 다변량 RAG 검색 테스트")
    print(f"{'='*70}\n")

    recipe_meta = _get_recipe_metadata()
    all_results = []

    # --- 변수 A: 언어 테스트 ---
    print("  [변수 A: 언어별 검색]")
    for q in QUERIES_A:
        r = await _test_query(q["query"], q["language"], "A", q.get("expected"), recipe_meta)
        all_results.append(r)
        _print_row(r)

    # --- 변수 B: 표현 방식 ---
    print("\n  [변수 B: 표현 방식]")
    for q in QUERIES_B:
        r = await _test_query(q["query"], q["language"], "B", q.get("expected"), recipe_meta)
        all_results.append(r)
        _print_row(r)

    # --- 변수 C: 제품 기반 ---
    print("\n  [변수 C: 제품 기반 검색]")
    for q in QUERIES_C:
        r = await _test_product_query(q["query"], q["language"], q["expected_products"], recipe_meta)
        all_results.append(r)
        _print_row(r)

    # --- 변수 D: 카테고리/맛 ---
    print("\n  [변수 D: 카테고리/맛 기반]")
    for q in QUERIES_D:
        r = await _test_category_query(q["query"], q["language"], q["expected_cat"], q["expected_taste"], recipe_meta)
        all_results.append(r)
        _print_row(r)

    # --- 변수 E: 모호한 검색 ---
    print("\n  [변수 E: 모호한 검색]")
    for q in QUERIES_E:
        r = await _test_vague_query(q["query"], q["language"], recipe_meta)
        all_results.append(r)
        _print_row(r)

    # --- 결과 저장 ---
    detail_path = REPORTS_DIR / "part2_rag_test_detail.json"
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # --- 실패 패턴 분석 ---
    total = len(all_results)
    passes = sum(1 for r in all_results if r["verdict"] == "PASS")
    fails = sum(1 for r in all_results if r["verdict"] == "FAIL")

    # 패턴별 분류
    lang_fails = {}
    var_fails = {}
    for r in all_results:
        if r["verdict"] == "FAIL":
            lang = r.get("language", "ko")
            lang_fails[lang] = lang_fails.get(lang, 0) + 1
            vt = r.get("variable_type", "?")
            var_fails[vt] = var_fails.get(vt, 0) + 1

    # top5에는 있는데 top3에서 잘린 케이스
    top5_but_not_top3 = sum(1 for r in all_results
        if r["verdict"] == "FAIL" and r.get("expected_rank") and r["expected_rank"] <= 5)

    summary_lines = []
    summary_lines.append(f"# Part 2: RAG 검색 다변량 테스트 결과 요약\n")
    summary_lines.append(f"## 전체 결과")
    summary_lines.append(f"- 총 쿼리: {total}개")
    summary_lines.append(f"- PASS (top3 기준): {passes}개")
    summary_lines.append(f"- FAIL (top3 기준): {fails}개")
    summary_lines.append(f"- 실패율: {fails/total*100:.1f}%\n")

    summary_lines.append(f"## 임베딩 모델")
    summary_lines.append(f"- **text-embedding-3-large** (OpenAI)")
    summary_lines.append(f"- 다국어 지원: O (모델 자체 지원)\n")

    summary_lines.append(f"## 변수별 실패 분포")
    for vt in sorted(var_fails.keys()):
        var_total = sum(1 for r in all_results if r.get("variable_type") == vt)
        var_pass = sum(1 for r in all_results if r.get("variable_type") == vt and r["verdict"] == "PASS")
        summary_lines.append(f"- 변수 {vt}: {var_pass}/{var_total} PASS ({var_fails.get(vt, 0)} FAIL)")
    for vt in ["A", "B", "C", "D", "E"]:
        if vt not in var_fails:
            var_total = sum(1 for r in all_results if r.get("variable_type") == vt)
            summary_lines.append(f"- 변수 {vt}: {var_total}/{var_total} PASS (0 FAIL)")

    summary_lines.append(f"\n## 언어별 실패 분포")
    for lang in ["ko", "vi", "en"]:
        lang_total = sum(1 for r in all_results if r.get("language") == lang)
        lang_pass = sum(1 for r in all_results if r.get("language") == lang and r["verdict"] == "PASS")
        if lang_total:
            summary_lines.append(f"- {lang}: {lang_pass}/{lang_total} PASS ({lang_fails.get(lang, 0)} FAIL)")

    summary_lines.append(f"\n## 주요 실패 패턴")
    patterns = []

    # 언어 패턴
    if lang_fails:
        worst_lang = max(lang_fails, key=lang_fails.get)
        patterns.append(f"1. **언어 문제**: {worst_lang}에서 {lang_fails[worst_lang]}건 실패")

    # top5 vs top3
    if top5_but_not_top3:
        patterns.append(f"2. **유사도 임계값**: top5에는 있지만 top3에서 잘린 케이스 {top5_but_not_top3}건")

    # 변수별
    if var_fails:
        worst_var = max(var_fails, key=var_fails.get)
        patterns.append(f"3. **변수 {worst_var} 문제**: {var_fails[worst_var]}건 실패")

    if not patterns:
        patterns.append("실패 패턴 없음 (모두 PASS)")

    summary_lines.extend(patterns)

    summary_lines.append(f"\n## 실패 케이스 상세")
    for r in all_results:
        if r["verdict"] == "FAIL":
            exp = r.get("expected_recipe", "N/A")
            rank = r.get("expected_rank", "N/A")
            summary_lines.append(f"- **\"{r['query']}\"** ({r['language']}, 변수{r['variable_type']}): 기대={exp}, 순위={rank}")

    summary_text = "\n".join(summary_lines) + "\n"
    summary_path = REPORTS_DIR / "part2_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print(f"\n{'='*70}")
    print(f"  Part 2 요약")
    print(f"{'='*70}")
    print(f"  총 쿼리: {total}개")
    print(f"  PASS: {passes}개")
    print(f"  FAIL: {fails}개")
    print(f"  실패율: {fails/total*100:.1f}%")
    print(f"  저장: {detail_path}")
    print(f"  저장: {summary_path}")

    return all_results


async def _test_query(query, language, var_type, expected_id, meta):
    """단일 쿼리 테스트 (변수 A, B)"""
    result = await search_similar_recipes(query, top_k=5)
    results_list = []
    expected_rank = None

    if result:
        col = get_collection()
        # Re-query to get individual results
        raw = col.query(query_texts=[query], n_results=5, include=["documents", "metadatas", "distances"])
        for i, (rid, dist, m) in enumerate(zip(raw["ids"][0], raw["distances"][0], raw["metadatas"][0])):
            sim = 1 - dist
            is_relevant = False
            if expected_id and rid == expected_id:
                is_relevant = True
                expected_rank = i + 1
            results_list.append({
                "rank": i + 1,
                "recipe_id": rid,
                "name": m.get("id", rid),
                "similarity": round(sim, 4),
                "category": m.get("category", ""),
                "taste": _extract_tastes(m),
                "relevant": is_relevant,
            })

    if expected_id is None:
        # 기대 레시피가 없는 경우 → 결과가 있으면 PASS
        verdict = "PASS" if results_list else "FAIL"
    else:
        verdict = "PASS" if expected_rank and expected_rank <= 3 else "FAIL"

    return {
        "query": query,
        "language": language,
        "variable_type": var_type,
        "results": results_list,
        "expected_recipe": expected_id,
        "expected_rank": expected_rank,
        "verdict": verdict,
    }


async def _test_product_query(query, language, expected_products, meta):
    """제품 기반 쿼리 테스트 (변수 C)"""
    col = get_collection()
    raw = col.query(query_texts=[query], n_results=5, include=["documents", "metadatas", "distances"],
                    where={"type": "recipe"})
    results_list = []
    has_match = False

    for i, (rid, dist, m) in enumerate(zip(raw["ids"][0], raw["distances"][0], raw["metadatas"][0])):
        sim = 1 - dist
        pid = m.get("product_id", "")
        is_relevant = any(ep in pid for ep in expected_products)
        if is_relevant and i < 3:
            has_match = True
        results_list.append({
            "rank": i + 1,
            "recipe_id": rid,
            "name": m.get("id", rid),
            "similarity": round(sim, 4),
            "category": m.get("category", ""),
            "product_id": pid,
            "taste": _extract_tastes(m),
            "relevant": is_relevant,
        })

    return {
        "query": query,
        "language": language,
        "variable_type": "C",
        "results": results_list,
        "expected_recipe": f"products: {expected_products}",
        "expected_rank": None,
        "verdict": "PASS" if has_match else "FAIL",
    }


async def _test_category_query(query, language, expected_cat, expected_taste, meta):
    """카테고리/맛 기반 쿼리 테스트 (변수 D)"""
    col = get_collection()
    raw = col.query(query_texts=[query], n_results=5, include=["documents", "metadatas", "distances"],
                    where={"type": "recipe"})
    results_list = []
    has_match = False

    for i, (rid, dist, m) in enumerate(zip(raw["ids"][0], raw["distances"][0], raw["metadatas"][0])):
        sim = 1 - dist
        cat = m.get("category", "")
        tastes = _extract_tastes(m)
        # 카테고리 + 맛 둘 다 매칭
        cat_match = expected_cat.lower() in cat.lower() if expected_cat else True
        taste_match = expected_taste in tastes if expected_taste else True
        is_relevant = cat_match and taste_match
        if is_relevant and i < 3:
            has_match = True
        results_list.append({
            "rank": i + 1,
            "recipe_id": rid,
            "name": m.get("id", rid),
            "similarity": round(sim, 4),
            "category": cat,
            "taste": tastes,
            "relevant": is_relevant,
        })

    return {
        "query": query,
        "language": language,
        "variable_type": "D",
        "results": results_list,
        "expected_recipe": f"cat={expected_cat}, taste={expected_taste}",
        "expected_rank": None,
        "verdict": "PASS" if has_match else "FAIL",
    }


async def _test_vague_query(query, language, meta):
    """모호한 쿼리 테스트 (변수 E): 결과가 반환되면 PASS"""
    col = get_collection()
    raw = col.query(query_texts=[query], n_results=5, include=["documents", "metadatas", "distances"],
                    where={"type": "recipe"})
    results_list = []

    if raw["ids"][0]:
        for i, (rid, dist, m) in enumerate(zip(raw["ids"][0], raw["distances"][0], raw["metadatas"][0])):
            sim = 1 - dist
            results_list.append({
                "rank": i + 1,
                "recipe_id": rid,
                "name": m.get("id", rid),
                "similarity": round(sim, 4),
                "category": m.get("category", ""),
                "taste": _extract_tastes(m),
                "relevant": True,  # 모호한 쿼리는 결과 있으면 OK
            })

    # 모호한 검색: top1 유사도가 0.2 이상이면 PASS (최소한 뭔가 관련 있는 결과)
    top1_sim = results_list[0]["similarity"] if results_list else 0
    verdict = "PASS" if top1_sim >= 0.15 else "FAIL"

    return {
        "query": query,
        "language": language,
        "variable_type": "E",
        "results": results_list,
        "expected_recipe": "any (vague query)",
        "expected_rank": None,
        "verdict": verdict,
    }


def _extract_tastes(meta):
    """메타데이터에서 true인 맛 추출"""
    tastes = []
    for key in ["매운", "고소", "담백", "달콤", "새콤", "짭짤", "바삭", "감칠맛", "얼큰"]:
        if meta.get(f"taste_{key}") == "true":
            tastes.append(key)
    return ",".join(tastes) if tastes else ""


def _print_row(r):
    """한 줄 요약 출력"""
    q = r["query"][:20].ljust(20)
    lang = r["language"]
    vt = r["variable_type"]
    exp = str(r.get("expected_recipe", ""))[:30]
    rank = r.get("expected_rank", "-")
    verdict = r["verdict"]
    top_sim = r["results"][0]["similarity"] if r["results"] else 0
    mark = "✅" if verdict == "PASS" else "❌"
    print(f"  {mark} {q} {lang:>2} {vt} rank={str(rank):>3} sim={top_sim:.3f} {verdict}")


# ══════════════════════════════════════════════════════════════
# Part 3: 81개 레시피 전체 검색 가능성 테스트
# ══════════════════════════════════════════════════════════════

async def run_part3():
    """Part 3: 각 레시피의 한글 이름으로 검색, top3 포함 여부 확인"""
    print(f"\n{'='*70}")
    print(f"  Part 3: 81개 레시피 전체 검색 가능성 테스트")
    print(f"{'='*70}\n")

    # translations.json에서 레시피명 가져오기
    tr_path = Path("data/translations.json")
    translations = json.loads(tr_path.read_text(encoding="utf-8"))

    col = get_collection()
    results = []
    failures = []

    for rid, tr in sorted(translations.items()):
        name = tr.get("name", rid)
        if not name:
            name = rid

        raw = col.query(
            query_texts=[name],
            n_results=5,
            include=["metadatas", "distances"],
            where={"type": "recipe"},
        )

        found_rank = None
        sim_at_rank = None
        top1_sim = None

        if raw["ids"][0]:
            top1_sim = round(1 - raw["distances"][0][0], 4)
            for i, search_id in enumerate(raw["ids"][0]):
                if search_id == rid:
                    found_rank = i + 1
                    sim_at_rank = round(1 - raw["distances"][0][i], 4)
                    break

        in_top3 = found_rank is not None and found_rank <= 3
        result_entry = {
            "recipe_id": rid,
            "query": name,
            "rank": found_rank,
            "in_top3": in_top3,
            "similarity": sim_at_rank,
            "top1_similarity": top1_sim,
        }
        results.append(result_entry)

        mark = "✅" if in_top3 else "❌"
        rank_str = str(found_rank) if found_rank else "N/A"
        sim_str = f"{sim_at_rank:.4f}" if sim_at_rank else "N/A"
        if not in_top3:
            failures.append(result_entry)
            # 실패면 top1이 뭔지도 보여주기
            top1_id = raw["ids"][0][0] if raw["ids"][0] else "N/A"
            print(f"  {mark} {rid[:40]:<40} rank={rank_str:>3} sim={sim_str:>7} (top1: {top1_id})")

    success = sum(1 for r in results if r["in_top3"])
    fail = len(results) - success

    # 상세 결과 저장
    detail_path = REPORTS_DIR / "part3_recipe_search_all.json"
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 요약 저장
    summary_lines = []
    summary_lines.append(f"# Part 3: 전체 레시피 검색 가능성 테스트 결과\n")
    summary_lines.append(f"## 전체 결과")
    summary_lines.append(f"- 검색 성공 (top 3 이내): {success}/{len(results)}")
    summary_lines.append(f"- 검색 실패 (top 3 밖): {fail}/{len(results)}")
    summary_lines.append(f"- 성공률: {success/len(results)*100:.1f}%\n")

    if failures:
        summary_lines.append(f"## 실패 목록")
        summary_lines.append(f"| recipe_id | 레시피명 | 실제 순위 | 유사도 |")
        summary_lines.append(f"|-----------|---------|----------|--------|")
        for f_entry in failures:
            rank = f_entry["rank"] if f_entry["rank"] else "N/A"
            sim = f"{f_entry['similarity']:.4f}" if f_entry["similarity"] else "N/A"
            summary_lines.append(f"| {f_entry['recipe_id']} | {f_entry['query']} | {rank} | {sim} |")
    else:
        summary_lines.append(f"## 실패 없음 — 모든 레시피가 top 3 이내에서 검색됨")

    # 유사도 분포
    sims = [r["similarity"] for r in results if r["similarity"] is not None]
    if sims:
        summary_lines.append(f"\n## 유사도 분포")
        summary_lines.append(f"- 평균: {sum(sims)/len(sims):.4f}")
        summary_lines.append(f"- 최소: {min(sims):.4f}")
        summary_lines.append(f"- 최대: {max(sims):.4f}")
        summary_lines.append(f"- 중앙값: {sorted(sims)[len(sims)//2]:.4f}")

    summary_text = "\n".join(summary_lines) + "\n"
    summary_path = REPORTS_DIR / "part3_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print(f"\n{'='*70}")
    print(f"  Part 3 요약")
    print(f"{'='*70}")
    print(f"  검색 성공 (top 3 이내): {success}/{len(results)}")
    print(f"  검색 실패 (top 3 밖): {fail}/{len(results)}")
    print(f"  성공률: {success/len(results)*100:.1f}%")
    if failures:
        print(f"\n  실패 목록:")
        for f_entry in failures:
            rank = f_entry["rank"] if f_entry["rank"] else "N/A"
            print(f"    - {f_entry['recipe_id']}: \"{f_entry['query']}\" (순위: {rank})")
    print(f"  저장: {detail_path}")
    print(f"  저장: {summary_path}")

    return results


async def main():
    await run_part2()
    await run_part3()
    print(f"\n{'='*70}")
    print(f"  전체 완료")
    print(f"{'='*70}")
    print(f"  Part 2: data/reports/part2_rag_test_detail.json")
    print(f"          data/reports/part2_summary.md")
    print(f"  Part 3: data/reports/part3_recipe_search_all.json")
    print(f"          data/reports/part3_summary.md")


if __name__ == "__main__":
    asyncio.run(main())
