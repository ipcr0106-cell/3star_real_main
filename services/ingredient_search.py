"""재료 기반 레시피 역추천"""
import logging
from services.recipe_search import get_collection

logger = logging.getLogger(__name__)

_INGREDIENT_CACHE = None


def invalidate_cache():
    """STEP 14 CRUD에서 호출"""
    global _INGREDIENT_CACHE
    _INGREDIENT_CACHE = None
    logger.info("Ingredient cache invalidated")


def _build_cache() -> list[dict]:
    global _INGREDIENT_CACHE
    if _INGREDIENT_CACHE is not None:
        return _INGREDIENT_CACHE

    col = get_collection()
    results = col.get(
        where={"type": "recipe"},
        include=["metadatas"],
    )

    cache = []
    for i, meta in enumerate(results["metadatas"]):
        ingredients_raw = meta.get("ingredients_main", "")
        ingredients = [ing.strip() for ing in ingredients_raw.split(",") if ing.strip()]
        cache.append({
            "id": results["ids"][i],
            "name": meta.get("id", ""),
            "ingredients": ingredients,
            "category": meta.get("category", ""),
            "product_id": meta.get("product_id", ""),
        })

    _INGREDIENT_CACHE = cache
    logger.info(f"Ingredient cache built: {len(cache)} recipes")
    return cache


async def search_by_ingredients(user_ingredients: list[str], top_k: int = 5) -> list[dict]:
    """사용자 재료로 만들 수 있는 레시피 검색 (겹치는 재료 수 기준 정렬)"""
    cache = _build_cache()

    user_set = set(ing.strip().lower() for ing in user_ingredients)

    scored = []
    for recipe in cache:
        recipe_set = set(ing.lower() for ing in recipe["ingredients"])
        overlap = set()
        for u_ing in user_set:
            for r_ing in recipe_set:
                if u_ing in r_ing or r_ing in u_ing:
                    overlap.add(r_ing)
                    break
        if overlap:
            scored.append({
                **recipe,
                "match_count": len(overlap),
                "matched": list(overlap),
                "total_ingredients": len(recipe_set),
                "match_ratio": len(overlap) / len(recipe_set) if recipe_set else 0,
            })

    scored.sort(key=lambda x: (-x["match_count"], -x["match_ratio"]))
    return scored[:top_k]
