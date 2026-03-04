"""AI 음식 이미지 생성 + 로컬 캐싱"""
import json
import logging
import os
import re
from pathlib import Path

import httpx
import openai

logger = logging.getLogger(__name__)

IMAGES_DIR = Path("static/images/recipes")
CACHE_FILE = Path("data/image_cache.json")
TRANSLATIONS_FILE = Path("data/translations.json")
RECIPES_DIR = Path("data/recipes")

IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# ─── 프롬프트 빌더 ───

PRESENTATION_STYLE = {
    "bowl": "Served in a deep ceramic bowl, seen from 45-degree angle",
    "plate": "Plated on a round ceramic dish, seen from above",
    "glass": "In a tall clear glass, seen from eye level",
}

CATEGORY_TO_STYLE = {
    "국물": "bowl",
    "면": "bowl",
    "구이": "plate",
    "볶음": "plate",
    "밥": "plate",
    "스낵": "plate",
    "샐러드": "plate",
    "음료": "glass",
    "디저트": "plate",
}

PRODUCT_FILTER = [
    "dami", "da-mi", "damifood", "coin broth", "broth cube", "broth coin",
    "k-grain", "k-bbq", "k-rosé", "k-rose", "gim-bugak", "gimbugak",
    "cheongyang mayo", "plum sauce", "ssamjang", "mango gochujang",
    "bulgogi coconut", "bulgogi seasoning", "dakgalbi seasoning",
    "kimchi-tamarind", "gamjatang seasoning", "abalone porridge seasoning",
    "wing sauce", "coconut chip", "energy powder",
    "seasoning", "coin", "sauce bottle",
]

GENERIC_FILTER = [
    "water", "salt", "pepper", "sugar", "oil", "sesame oil",
    "fish sauce", "soy sauce", "cooking oil", "vegetable oil",
    "cornstarch", "flour", "egg", "ice",
]

_translations_cache = None


def _load_translations() -> dict:
    global _translations_cache
    if _translations_cache is None:
        if TRANSLATIONS_FILE.exists():
            _translations_cache = json.loads(
                TRANSLATIONS_FILE.read_text(encoding="utf-8")
            )
        else:
            _translations_cache = {}
    return _translations_cache


def _get_category(recipe_id: str) -> str:
    """레시피 마크다운에서 카테고리 추출."""
    md_path = RECIPES_DIR / f"{recipe_id}.md"
    if not md_path.exists():
        return ""
    try:
        content = md_path.read_text(encoding="utf-8")
        match = re.search(r"^category:\s*(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else ""
    except Exception:
        return ""


def _clean_ingredient(ing: str) -> str:
    """수량, 괄호, 불필요한 수식어 제거."""
    # 수량 제거: "200g", "1/2 cup", "3 tablespoons" 등
    cleaned = re.sub(
        r"\d+[/.\d]*\s*(g|ml|kg|L|cups?|tablespoons?|teaspoons?|pieces?|"
        r"cloves?|stalks?|slices?|sheets?|bunch|handful)?\b",
        "", ing, flags=re.I,
    )
    # 괄호 제거: "(bánh phở)", "(optional)"
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)
    # 후행 수식어 제거: "to taste", "as needed", "optional", "thinly sliced" 등
    cleaned = re.sub(
        r"\b(to taste|as needed|optional|thinly sliced|finely chopped|"
        r"finely minced|julienned|diced|minced|sliced|chopped)\b",
        "", cleaned, flags=re.I,
    )
    # 포장/단위 수식어 제거: "pack of", "block of", "head of", "handful of", "leaves of"
    cleaned = re.sub(
        r"\b(pack|block|head|handful|leaves?|bunch|sprig|stalk|clove)\s*(of\b)?",
        "", cleaned, flags=re.I,
    )
    # 복합구문 제거: "suitable amount of ...", "such as ..."
    cleaned = re.sub(r"\bsuitable\s+amount\s+of\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bsuch\s+as\b", "", cleaned, flags=re.I)
    # 잔여 "of " 제거 (수량 제거 후 남는 "of")
    cleaned = re.sub(r"^\s*of\s+", "", cleaned.strip(), flags=re.I)
    # 관사/수식어 제거
    cleaned = re.sub(r"^(a |an |some |about |fresh )", "", cleaned.strip(), flags=re.I)
    cleaned = cleaned.strip(" -,.")
    return cleaned


def _extract_visual_ingredients(recipe_id: str) -> str:
    """translations.json에서 영문 재료 추출 → 시각적 핵심 재료 3~5개."""
    tr = _load_translations()
    recipe = tr.get(recipe_id, {})
    en_ingredients = recipe.get("en", {}).get("ingredients", [])

    visual = []
    for ing in en_ingredients:
        ing_lower = ing.lower()
        if any(k in ing_lower for k in PRODUCT_FILTER):
            continue
        if any(k in ing_lower for k in GENERIC_FILTER):
            continue
        cleaned = _clean_ingredient(ing)
        if cleaned and len(cleaned) > 1:
            visual.append(cleaned)

    return ", ".join(visual[:5]) if visual else ""


def build_prompt(recipe_id: str, name_en: str = "") -> str:
    """레시피 ID로 개선된 DALL-E 프롬프트 생성."""
    # 영문명
    if not name_en:
        tr = _load_translations()
        name_en = tr.get(recipe_id, {}).get("name_en", recipe_id)

    # 시각 재료
    visual_ing = _extract_visual_ingredients(recipe_id)
    ing_part = f", with {visual_ing}" if visual_ing else ""

    # 카테고리 → 스타일
    category = _get_category(recipe_id)
    style_key = CATEGORY_TO_STYLE.get(category, "plate")
    presentation = PRESENTATION_STYLE[style_key]

    prompt = (
        f"Professional food photo of {name_en}{ing_part}.\n"
        f"{presentation}.\n"
        f"Light wooden table, warm natural side lighting, vibrant colors, sharp focus."
    )
    return prompt


# ─── 캐시 관리 ───

def _load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict):
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ─── 이미지 생성 ───

async def generate_recipe_image(
    recipe_id: str, recipe_name: str, recipe_name_vn: str = ""
) -> str:
    """레시피 이미지 생성/캐시 반환. 로컬 URL 반환."""
    cache = _load_cache()

    # 캐시 히트
    if recipe_id in cache:
        local_path = cache[recipe_id]
        if Path(local_path).exists():
            logger.info(f"Image cache hit: {recipe_id}")
            return f"/{local_path}"

    # 프롬프트 생성
    prompt = build_prompt(recipe_id, recipe_name)

    # DALL-E 3 생성
    try:
        client = openai.AsyncOpenAI()

        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url

        # httpx로 다운로드
        local_filename = f"{recipe_id}.png"
        local_path = IMAGES_DIR / local_filename

        async with httpx.AsyncClient(timeout=30) as http_client:
            img_response = await http_client.get(image_url)
            img_response.raise_for_status()
            local_path.write_bytes(img_response.content)

        # 캐시 저장
        relative_path = f"static/images/recipes/{local_filename}"
        cache[recipe_id] = relative_path
        _save_cache(cache)

        logger.info(f"Image generated and cached: {recipe_id}")
        return f"/{relative_path}"

    except Exception as e:
        logger.error(f"Image generation failed for {recipe_id}: {e}")
        return ""


def get_cached_image(recipe_id: str) -> str:
    """캐시된 이미지 경로 반환. 없으면 빈 문자열."""
    cache = _load_cache()
    if recipe_id in cache and Path(cache[recipe_id]).exists():
        return f"/{cache[recipe_id]}"
    return ""
