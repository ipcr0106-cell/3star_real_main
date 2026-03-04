"""
★ recipe_search.py — 벡터 검색 서비스 ★

[사용법]
from services.recipe_search import get_collection, search_similar_recipes, get_random_recipe
"""

import os
import random
import re

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

FRONTMATTER_RE = re.compile(r'^---\s*\n.*?\n---\s*\n', re.DOTALL)
CHROMA_PATH = "data/chromadb"
COLLECTION_NAME = "threestar"

_collection = None


def get_collection():
    """ChromaDB 컬렉션 싱글턴 반환."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        api_key = os.getenv("OPENAI_API_KEY", "")
        ef = OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-large",
        )
        _collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=ef,
        )
    return _collection


async def search_similar_recipes(
    query: str, top_k: int = 3, filters: dict | None = None,
    exclude_ids: list[str] | None = None,
) -> dict | None:
    """
    벡터 유사도 검색.

    Args:
        query: 검색 쿼리
        top_k: 반환할 결과 수
        filters: ChromaDB where 절 (예: {"type": "recipe"})

    Returns:
        {"context": 포맷된 문자열, "max_similarity": float, "result_count": int}
        또는 결과 없으면 None
    """
    collection = get_collection()

    kwargs = {
        "query_texts": [query],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if filters:
        kwargs["where"] = filters

    # exclude_ids가 있으면 더 많이 검색해서 필터링
    if exclude_ids:
        kwargs["n_results"] = top_k + len(exclude_ids)

    results = collection.query(**kwargs)

    ids = results["ids"][0]
    documents = results["documents"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    # exclude_ids 필터링
    if exclude_ids:
        filtered = [
            (i, d, dist, m) for i, d, dist, m
            in zip(ids, documents, distances, metadatas)
            if i not in exclude_ids
        ]
        if filtered:
            ids, documents, distances, metadatas = zip(*filtered)
            ids = list(ids)[:top_k]
            documents = list(documents)[:top_k]
            distances = list(distances)[:top_k]
            metadatas = list(metadatas)[:top_k]
        else:
            ids, documents, distances, metadatas = [], [], [], []

    if not ids:
        return None

    context_parts = []
    max_similarity = 0.0

    for doc_id, doc, dist, meta in zip(ids, documents, distances, metadatas):
        similarity = 1 - dist
        max_similarity = max(max_similarity, similarity)
        body = FRONTMATTER_RE.sub('', doc)
        truncated = body[:1200]
        context_parts.append(f"[{meta.get('type', 'unknown')}:{doc_id} sim={similarity:.2f}]\n{truncated}")

    context = "\n---\n".join(context_parts)

    return {
        "context": context,
        "max_similarity": max_similarity,
        "result_count": len(ids),
    }


async def get_random_recipe() -> dict | None:
    """type=recipe에서 랜덤 1개 반환."""
    collection = get_collection()

    results = collection.get(
        where={"type": "recipe"},
        include=["documents", "metadatas"],
    )

    if not results["ids"]:
        return None

    idx = random.randint(0, len(results["ids"]) - 1)

    return {
        "id": results["ids"][idx],
        "content": results["documents"][idx],
        "metadata": results["metadatas"][idx],
    }
