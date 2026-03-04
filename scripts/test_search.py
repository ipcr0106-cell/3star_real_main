"""
★ ChromaDB 검색 테스트 스크립트 ★
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.recipe_search import get_collection


def test_total_count(col):
    total = col.count()
    status = "PASS" if total == 89 else "FAIL"
    print(f"[{status}] 1. Total documents: {total} (기대: 89)")


def test_recipe_search(col):
    results = col.query(
        query_texts=["매콤한 쌀국수"],
        where={"type": "recipe"},
        n_results=3,
        include=["metadatas", "distances"],
    )
    count = len(results["ids"][0])
    print(f"\n2. '매콤한 쌀국수' (recipe, top_k=3): {count}건")
    for i, (doc_id, dist) in enumerate(zip(results["ids"][0], results["distances"][0])):
        sim = 1 - dist
        print(f"   {i+1}. {doc_id} (sim={sim:.3f})")


def test_product_search(col):
    results = col.query(
        query_texts=["코인육수 가격"],
        where={"type": "product"},
        n_results=2,
        include=["metadatas", "distances"],
    )
    count = len(results["ids"][0])
    print(f"\n3. '코인육수 가격' (product, top_k=2): {count}건")
    for i, (doc_id, dist) in enumerate(zip(results["ids"][0], results["distances"][0])):
        sim = 1 - dist
        meta = results["metadatas"][0][i]
        print(f"   {i+1}. {doc_id} price={meta.get('price','')} (sim={sim:.3f})")


def test_company_search(col):
    results = col.query(
        query_texts=["배송 연락처"],
        where={"type": "company"},
        n_results=1,
        include=["metadatas", "distances"],
    )
    count = len(results["ids"][0])
    print(f"\n4. '배송 연락처' (company, top_k=1): {count}건")
    for i, (doc_id, dist) in enumerate(zip(results["ids"][0], results["distances"][0])):
        sim = 1 - dist
        print(f"   {i+1}. {doc_id} (sim={sim:.3f})")


def test_vegan_search(col):
    results = col.query(
        query_texts=["채식 요리"],
        where={"type": "recipe"},
        n_results=3,
        include=["metadatas", "distances"],
    )
    count = len(results["ids"][0])
    print(f"\n5. '채식 요리' (recipe, top_k=3): {count}건")
    for i, (doc_id, dist) in enumerate(zip(results["ids"][0], results["distances"][0])):
        sim = 1 - dist
        print(f"   {i+1}. {doc_id} (sim={sim:.3f})")


def test_type_counts(col):
    print("\n6. 타입별 문서 수:")
    for t in ["recipe", "product", "company"]:
        count = len(col.get(where={"type": t})["ids"])
        expected = {"recipe": 72, "product": 16, "company": 1}[t]
        status = "PASS" if count == expected else "FAIL"
        print(f"   [{status}] {t}: {count} (기대: {expected})")


def test_taste_filter(col):
    results = col.query(
        query_texts=["매운 요리"],
        where={"taste_매운": "true"},
        n_results=3,
        include=["metadatas", "distances"],
    )
    count = len(results["ids"][0])
    status = "PASS" if count > 0 else "FAIL"
    print(f"\n7. taste_매운='true' 필터 테스트:")
    print(f"   [{status}] 결과: {count}건 (0건이면 FAIL)")
    for i, (doc_id, dist) in enumerate(zip(results["ids"][0], results["distances"][0])):
        sim = 1 - dist
        meta = results["metadatas"][0][i]
        print(f"   {i+1}. {doc_id} taste={meta.get('taste','')} taste_매운={meta.get('taste_매운','')} (sim={sim:.3f})")


def test_metadata_types(col):
    sample = col.get(where={"type": "recipe"}, limit=1, include=["metadatas"])
    meta = sample["metadatas"][0]
    taste_val = meta.get("taste_매운", None)
    ctm_val = meta.get("cook_time_minutes", None)
    print(f"\n8. 메타데이터 타입 검증:")
    status1 = "PASS" if isinstance(taste_val, str) else "FAIL"
    print(f"   [{status1}] taste_매운: type={type(taste_val).__name__}, value={taste_val}")
    status2 = "PASS" if isinstance(ctm_val, int) else "FAIL"
    print(f"   [{status2}] cook_time_minutes: type={type(ctm_val).__name__}, value={ctm_val}")


def main():
    print("=" * 50)
    print("ChromaDB 검색 테스트")
    print("=" * 50)

    col = get_collection()

    test_total_count(col)
    test_recipe_search(col)
    test_product_search(col)
    test_company_search(col)
    test_vegan_search(col)
    test_type_counts(col)
    test_taste_filter(col)
    test_metadata_types(col)

    print("\n" + "=" * 50)
    print("테스트 완료")
    print("=" * 50)


if __name__ == "__main__":
    main()
