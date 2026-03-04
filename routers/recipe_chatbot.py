"""
★ B파트 — 레시피 챗봇 라우터 (recipe_chatbot.py) ★

POST /chat — 3가지 모드: chat, guided, random
- chat: LangGraph 파이프라인 (chatbot_graph.py)
- guided/random: 기존 방식 유지
"""

import copy

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.recipe_ai import call_gpt, _format, _apply_translation
from services.recipe_search import search_similar_recipes, get_random_recipe
from services.chatbot_graph import INJECTION_PATTERNS, _check_injection
from services.output_guardrail import check_output
from services.analytics import log_event
from services.image_generator import generate_recipe_image, get_cached_image

router = APIRouter()


BLOCKED_RESPONSE = {
    "type": "chat",
    "reply": "저는 다미푸드의 K-푸드 챗봇입니다. 레시피 추천이나 제품 관련 질문을 도와드릴 수 있어요! 무엇이 궁금하신가요?",
    "links": [],
    "_raw": None,
}

# ─── 카테고리/맛 매핑 ───
CATEGORY_FILTER = {
    "국물탕": {"category": "국물"},
    "면볶음면": {"category": "면"},
    "구이볶음": {"$or": [{"category": "구이"}, {"category": "볶음"}]},
    "쌈샐러드": {"category": "샐러드"},
    "밥죽": {"category": "밥"},
    "간식음료": {"$or": [{"category": "음료"}, {"category": "디저트"}, {"category": "스낵"}]},
}

CATEGORY_PROMPT_NAME = {
    "국물탕": "국물/탕",
    "면볶음면": "면/볶음면",
    "구이볶음": "구이/볶음",
    "쌈샐러드": "쌈/샐러드",
    "밥죽": "밥/죽",
    "간식음료": "간식/음료",
}

TASTE_QUERY = ["매운", "고소", "담백", "달콤", "새콤", "짭짤", "바삭", "감칠맛", "얼큰"]


# ─── 요청 모델 ───
class ChatRequest(BaseModel):
    message: str = ""
    language: str = "vi"
    mode: str = "chat"  # chat / guided / random
    category: str | None = None
    taste: str | None = None
    conversation_history: list = Field(default_factory=list)


# ─── POST /chat ───
@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """
    3가지 모드:
    - chat: LangGraph 파이프라인 (guardrail → 의도분류 → 검색 → 생성)
    - guided: 카테고리/맛 기반 가이드 추천
    - random: 랜덤 레시피 1개
    """

    # ── MODE: random ──
    if req.mode == "random":
        if req.message and _check_injection(req.message):
            return BLOCKED_RESPONSE
        recipe = await get_random_recipe()
        if not recipe:
            return {
                "type": "chat",
                "reply": "레시피를 찾을 수 없습니다. 잠시 후 다시 시도해 주세요.",
                "links": [],
                "_raw": None,
            }
        rag_context = f"[recipe:{recipe['id']}]\n{recipe['content'][:800]}"
        prompt = f"이 레시피를 소개해 주세요: {recipe['metadata'].get('id', '')}"
        result = await call_gpt(
            message=prompt,
            language=req.language,
            conversation_history=req.conversation_history,
            rag_context=rag_context,
        )
        result = await check_output(result)
        raw_copy = copy.deepcopy(result)
        formatted = _format(result)
        formatted["_raw"] = raw_copy
        formatted = _apply_translation(formatted, req.language)
        # 이미지 생성/캐시
        if formatted.get("type") == "recipe":
            rid = formatted.get("recipe_id", "")
            if rid:
                cached = get_cached_image(rid)
                if cached:
                    formatted["image_url"] = cached
                else:
                    formatted["image_url"] = await generate_recipe_image(
                        rid, formatted.get("title", ""),
                    )
        log_event("recipe_search", {
            "mode": "random",
            "recipe_id": formatted.get("recipe_id", ""),
            "recipe_name": formatted.get("title", ""),
            "language": req.language,
        })
        return formatted

    # ── MODE: guided ──
    if req.mode == "guided":
        if req.message and _check_injection(req.message):
            return BLOCKED_RESPONSE

        # 카테고리 필터 구성
        cat_filter = CATEGORY_FILTER.get(req.category, {})
        base_filter = {"type": "recipe"}
        if cat_filter:
            filters = {"$and": [base_filter, cat_filter]}
        else:
            filters = base_filter

        # taste 필터 추가
        query_parts = []
        if req.category:
            query_parts.append(CATEGORY_PROMPT_NAME.get(req.category, req.category))
        if req.taste:
            taste_key = f"taste_{req.taste}"
            if "$and" in filters:
                filters["$and"].append({taste_key: "true"})
            else:
                filters = {"$and": [filters, {taste_key: "true"}]}
            query_parts.append(f"{req.taste} 맛")

        query = " ".join(query_parts) if query_parts else "추천 레시피"

        search_result = await search_similar_recipes(
            query=req.taste or query, top_k=3, filters=filters
        )
        rag_context = search_result["context"] if search_result else None

        prompt = f"'{query}' 조건에 맞는 레시피를 추천해 주세요."
        result = await call_gpt(
            message=prompt,
            language=req.language,
            conversation_history=req.conversation_history,
            rag_context=rag_context,
        )
        result = await check_output(result)
        raw_copy = copy.deepcopy(result)
        formatted = _format(result)
        formatted["_raw"] = raw_copy
        formatted = _apply_translation(formatted, req.language)
        # 이미지 생성/캐시
        if formatted.get("type") == "recipe":
            rid = formatted.get("recipe_id", "")
            if rid:
                cached = get_cached_image(rid)
                if cached:
                    formatted["image_url"] = cached
                else:
                    formatted["image_url"] = await generate_recipe_image(
                        rid, formatted.get("title", ""),
                    )
        log_event("recipe_search", {
            "mode": "guided",
            "recipe_id": formatted.get("recipe_id", ""),
            "recipe_name": formatted.get("title", ""),
            "category": req.category or "",
            "taste": req.taste or "",
            "language": req.language,
        })
        return formatted

    # ── MODE: chat (LangGraph 파이프라인) ──
    from services.chatbot_graph import run_chat_pipeline
    result = await run_chat_pipeline(req.message, req.language, req.conversation_history)
    if result.get("type") == "recipe":
        log_event("recipe_search", {
            "mode": "chat",
            "recipe_id": result.get("recipe_id", ""),
            "recipe_name": result.get("title", ""),
            "language": req.language,
        })
    return result
