"""
★ init_vectordb.py — ChromaDB 초기화 (103개 문서 벡터화) ★

실행: python3 -m services.init_vectordb
- 81 레시피 + 16 제품 상세 + 1 회사 정보 + 5 비교 문서 = 103개 문서
- OpenAI text-embedding-3-large 사용
- data/chromadb/ 에 영구 저장
"""

import glob
import os
import re

import chromadb
import yaml
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = "data/chromadb"
COLLECTION_NAME = "threestar"
TASTE_LIST = ["매운", "고소", "담백", "달콤", "새콤", "짭짤", "바삭", "감칠맛", "얼큰"]

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def get_embedding_function():
    api_key = os.getenv("OPENAI_API_KEY", "")
    return OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-large",
    )


def parse_md(filepath):
    """frontmatter(dict)와 본문(프런트매터 제거)을 반환."""
    text = open(filepath, "r", encoding="utf-8").read()
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    body = FRONTMATTER_RE.sub('', text)
    return fm, body


def load_recipes():
    """data/recipes/*.md → (ids, documents, metadatas)"""
    ids, docs, metas = [], [], []
    for filepath in sorted(glob.glob("data/recipes/*.md")):
        fm, text = parse_md(filepath)
        if not fm:
            continue
        doc_id = fm.get("id", os.path.basename(filepath).replace(".md", ""))

        metadata = {
            "id": doc_id,
            "type": "recipe",
            "category": fm.get("category", ""),
            "difficulty": fm.get("difficulty", ""),
            "taste": fm.get("taste", ""),
            "cook_time": fm.get("cook_time", ""),
            "cook_time_minutes": int(fm.get("cook_time_minutes", 30)),
            "ingredients_main": fm.get("ingredients_main", ""),
            "base_servings": int(fm.get("base_servings", 2)),
            "product_id": fm.get("product_id", ""),
        }
        # taste 불리언: Python bool → 문자열 "true"/"false"
        for taste in TASTE_LIST:
            key = f"taste_{taste}"
            val = fm.get(key, False)
            metadata[key] = "true" if val else "false"

        # 다국어 이름을 임베딩 텍스트 앞에 추가 (검색 개선)
        name_ko = fm.get("name", "")
        name_vn = fm.get("name_vn", "")
        name_en = fm.get("name_en", "")
        prefix = ""
        if name_ko:
            prefix += f"Korean: {name_ko}\n"
        if name_vn:
            prefix += f"Vietnamese: {name_vn}\n"
        if name_en:
            prefix += f"English: {name_en}\n"
        search_keywords = fm.get("search_keywords", "")
        if search_keywords:
            prefix += f"Keywords: {search_keywords}\n"

        ids.append(doc_id)
        docs.append(prefix + text)
        metas.append(metadata)

    return ids, docs, metas


def load_products():
    """data/product_details/*.md → (ids, documents, metadatas)"""
    ids, docs, metas = [], [], []
    for filepath in sorted(glob.glob("data/product_details/*.md")):
        fm, text = parse_md(filepath)
        product_id = os.path.basename(filepath).replace(".md", "")

        metadata = {
            "id": product_id,
            "type": "product",
            "product_id": product_id,
            "product_category": fm.get("category", ""),
            "brand": "DAMI",
            "price": fm.get("price", ""),
        }

        ids.append(product_id)
        docs.append(text)
        metas.append(metadata)

    return ids, docs, metas


def load_company():
    """data/company_info.md → (ids, documents, metadatas)"""
    filepath = "data/company_info.md"
    if not os.path.exists(filepath):
        return [], [], []
    text = open(filepath, "r", encoding="utf-8").read()
    return (
        ["company_info"],
        [text],
        [{"id": "company_info", "type": "company"}],
    )


def load_comparisons():
    """data/product_comparisons/*.md → (ids, documents, metadatas)"""
    ids, docs, metas = [], [], []
    comp_dir = "data/product_comparisons"
    if not os.path.exists(comp_dir):
        return ids, docs, metas
    for filepath in sorted(glob.glob(f"{comp_dir}/*.md")):
        text = open(filepath, "r", encoding="utf-8").read()
        doc_id = "comparison_" + os.path.basename(filepath).replace(".md", "")

        metadata = {
            "id": doc_id,
            "type": "comparison",
        }

        ids.append(doc_id)
        docs.append(text)
        metas.append(metadata)

    return ids, docs, metas


def load_cooking_tips():
    """data/cooking_tips/*.md → (ids, documents, metadatas)"""
    ids, docs, metas = [], [], []
    tip_dir = "data/cooking_tips"
    if not os.path.exists(tip_dir):
        print("  data/cooking_tips/ 폴더 없음 — 건너뜀")
        return ids, docs, metas
    for filepath in sorted(glob.glob(f"{tip_dir}/*.md")):
        fm, text = parse_md(filepath)
        doc_id = fm.get("id", os.path.basename(filepath).replace(".md", ""))
        metadata = {
            "id": doc_id,
            "type": "cooking_tip",
        }
        ids.append(doc_id)
        docs.append(text)
        metas.append(metadata)
    return ids, docs, metas


def main():
    print("=== ChromaDB 초기화 시작 ===")

    # 클라이언트 생성
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = get_embedding_function()

    # 기존 컬렉션 삭제 후 재생성
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"기존 컬렉션 '{COLLECTION_NAME}' 삭제")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    # 레시피 로드
    r_ids, r_docs, r_metas = load_recipes()
    print(f"레시피: {len(r_ids)}개")

    # 제품 로드
    p_ids, p_docs, p_metas = load_products()
    print(f"제품: {len(p_ids)}개")

    # 회사 정보 로드
    c_ids, c_docs, c_metas = load_company()
    print(f"회사: {len(c_ids)}개")

    # 비교 문서 로드
    comp_ids, comp_docs, comp_metas = load_comparisons()
    print(f"비교 문서: {len(comp_ids)}개")

    # 요리 팁 로드
    tip_ids, tip_docs, tip_metas = load_cooking_tips()
    print(f"요리 팁: {len(tip_ids)}개")

    # 모두 합치기
    all_ids = r_ids + p_ids + c_ids + comp_ids + tip_ids
    all_docs = r_docs + p_docs + c_docs + comp_docs + tip_docs
    all_metas = r_metas + p_metas + c_metas + comp_metas + tip_metas

    print(f"\n총 {len(all_ids)}개 문서 임베딩 시작...")

    # 배치 처리 (ChromaDB 제한: 한 번에 최대 ~5000개)
    batch_size = 50
    for i in range(0, len(all_ids), batch_size):
        end = min(i + batch_size, len(all_ids))
        collection.add(
            ids=all_ids[i:end],
            documents=all_docs[i:end],
            metadatas=all_metas[i:end],
        )
        print(f"  배치 {i//batch_size + 1}: {i+1}~{end} 완료")

    print(f"\n=== 완료: {collection.count()}개 문서 저장됨 ===")


if __name__ == "__main__":
    main()
