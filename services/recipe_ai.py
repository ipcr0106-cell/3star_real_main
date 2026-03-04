"""
★ recipe_ai.py — 챗봇 전용 GPT-4o-mini 호출 ★

B2C 챗봇 전용. openai_api.py(B2B 공유)와 별개.
call_gpt_mini: 경량 호출 (분류, 필터, 번역 등)
call_gpt: 메인 호출 (Sandwiching + Few-shot)
_format: GPT 응답 → 프론트엔드 정리
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MAIN_MODEL = os.getenv("MAIN_MODEL", "gpt-4.1-mini")          # 경량 호출용 (classify, rewrite, filter, hyde 등)
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "gpt-4.1")   # 메인 답변 생성용

_client = None
SYSTEM_PROMPT = ""
_translations_cache = None
_products_cache = None


def _load_translations() -> dict:
    """data/translations.json을 캐시하여 반환."""
    global _translations_cache
    if _translations_cache is None:
        translations_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "translations.json"
        )
        if os.path.exists(translations_path):
            with open(translations_path, "r", encoding="utf-8") as f:
                _translations_cache = json.load(f)
        else:
            _translations_cache = {}
    return _translations_cache


def _load_products() -> list:
    """products.json을 로드하여 제품 목록 반환."""
    global _products_cache
    if _products_cache is None:
        products_path = Path(__file__).parent.parent / "data" / "products.json"
        if products_path.exists():
            with open(products_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _products_cache = data if isinstance(data, list) else data.get("products", [])
        else:
            _products_cache = []
    return _products_cache


def _apply_translation(formatted: dict, language: str) -> dict:
    """language가 vi/en이면 translations.json에서 해당 언어 버전으로 교체."""
    if language == "ko" or formatted.get("type") != "recipe":
        return formatted

    recipe_id = formatted.get("recipe_id", "")
    if not recipe_id:
        return formatted

    translations = _load_translations()
    recipe_tr = translations.get(recipe_id)
    if not recipe_tr:
        return formatted

    lang_data = recipe_tr.get(language)
    if not lang_data:
        return formatted

    # 제목 교체
    if language == "vi" and recipe_tr.get("name_vn"):
        formatted["title"] = recipe_tr["name_vn"]
    elif language == "en" and recipe_tr.get("name_en"):
        formatted["title"] = recipe_tr["name_en"]

    # ★ 빈값 보호: 실제 내용이 있는 경우에만 교체
    tr_ingredients = lang_data.get("ingredients", [])
    if tr_ingredients and any(str(item).strip() for item in tr_ingredients):
        formatted["ingredients"] = tr_ingredients

    tr_steps = lang_data.get("steps", [])
    if tr_steps and any(str(item).strip() for item in tr_steps):
        formatted["steps"] = tr_steps

    tr_tips = lang_data.get("tips", [])
    if tr_tips and any(str(item).strip() for item in tr_tips):
        formatted["tips"] = tr_tips

    # ★ product 필드 번역 (products.json에서 다국어 제품명 가져오기)
    product_id = formatted.get("product_id", "")
    if product_id and formatted.get("product"):
        products_data = _load_products()
        for p in products_data:
            if p.get("id") == product_id:
                if language == "vi" and p.get("name_vn"):
                    formatted["product"] = p["name_vn"]
                elif language == "en" and p.get("name_en"):
                    formatted["product"] = p["name_en"]
                break

    return formatted


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    return _client


def _load_system_prompt():
    global SYSTEM_PROMPT
    if not SYSTEM_PROMPT:
        try:
            with open("data/system_prompt.txt", "r", encoding="utf-8") as f:
                SYSTEM_PROMPT = f.read()
        except FileNotFoundError:
            SYSTEM_PROMPT = "You are a helpful K-food chatbot assistant."
    return SYSTEM_PROMPT


# ─── A) call_gpt_mini: 경량 호출 ───
async def call_gpt_mini(
    prompt: str,
    max_tokens: int = 50,
    temperature: float = 0,
    response_format=None,
) -> str:
    """
    GPT-4o-mini 경량 호출. 분류/필터/번역 등에 사용.
    STEP 5~10에서 6곳에서 사용:
      classify_intent, query_rewrite, extract_filters,
      hyde, translate_to_korean, parse_ingredients
    """
    client = _get_client()
    kwargs = {
        "model": MAIN_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()


# ─── B) call_gpt: 메인 호출 (Sandwiching) ───
async def call_gpt(
    message: str,
    language: str = "vi",
    conversation_history: list | None = None,
    rag_context: str | None = None,
) -> dict:
    """
    GPT-4o-mini 메인 호출. JSON 응답.
    Sandwiching: system → history → [rag context] → user → [reminder]
    """
    client = _get_client()
    system_prompt = _load_system_prompt()

    # 시스템 프롬프트
    messages = [{"role": "system", "content": system_prompt}]

    # 대화 히스토리 (최근 6턴, 각 500자 제한)
    if conversation_history:
        recent = conversation_history[-6:]
        for turn in recent:
            role = turn.get("role", "user")
            content = str(turn.get("content", ""))[:500]
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

    # Sandwiching: RAG context → user → reminder
    if rag_context:
        messages.append({
            "role": "system",
            "content": f"참고 정보:\n{rag_context}",
        })
        messages.append({"role": "user", "content": message})
        messages.append({
            "role": "system",
            "content": (
                "=== REMINDER (반드시 준수) ===\n"
                "1. recipe_id: RAG context에 있는 ID를 그대로 복사. 없으면 \"\" (절대 만들지 말 것)\n"
                "2. title: RAG context에 있는 제목을 그대로 복사. 변형하지 말 것\n"
                "3. title_vn: RAG context에 있는 베트남어 제목을 그대로 복사\n"
                "4. ingredients: RAG context의 재료를 그대로 복사. 반드시 수량(g, ml, 큰술, 개 등)을 포함할 것. 재료를 축약하거나 누락하지 말 것. 전부 포함할 것.\n"
                "5. steps: RAG context의 조리법을 그대로 복사. 모든 단계를 빠짐없이 포함할 것. 절대로 빈 문자열(\"\")을 넣지 말 것.\n"
                "6. product: RAG context에 있는 product_id의 제품명 사용. 없으면 \"\"\n"
                "⚠️ RAG context에 없는 정보는 절대 생성하지 마세요. \"모르겠습니다\"가 환각보다 낫습니다.\n"
                "⚠️ 답변은 반드시 제공된 context 정보에 근거해야 합니다. context에 없는 가격, 성분, 영양정보를 만들지 마세요.\n"
                "==========================="
            ),
        })
    else:
        messages.append({"role": "user", "content": message})

    # 언어 지시
    lang_instruction = {
        "ko": "한국어로 답변하세요.",
        "en": "Answer in English.",
        "vi": "Trả lời bằng tiếng Việt.",
    }.get(language, "Trả lời bằng tiếng Việt.")

    messages.append({
        "role": "system",
        "content": f"LANGUAGE: {lang_instruction}",
    })

    response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=messages,
        max_tokens=2500,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"type": "chat", "reply": raw}


# ─── C) _format: GPT 응답 → 프론트엔드 정리 ───
def _format(result: dict) -> dict:
    """GPT 응답을 프론트엔드용으로 정리."""
    resp_type = result.get("type", "chat")

    if resp_type == "recipe":
        return {
            "type": "recipe",
            "title": result.get("title", ""),
            "title_vn": result.get("title_vn", ""),
            "product": result.get("product", ""),
            "product_id": result.get("product_id", ""),
            "recipe_id": result.get("recipe_id", ""),
            "ingredients": result.get("ingredients", []),
            "steps": result.get("steps", []),
            "tips": result.get("tips", []),
            "base_servings": result.get("base_servings", 2),
            "image_url": result.get("image_url", ""),
            "links": result.get("links", []),
        }
    else:
        return {
            "type": "chat",
            "reply": result.get("reply", ""),
            "links": result.get("links", []),
        }
