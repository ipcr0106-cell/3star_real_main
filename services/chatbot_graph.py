"""
★ chatbot_graph.py — LangGraph 챗봇 파이프라인 ★

11개 노드, 9의도 분기:
input_guardrail → classify_intent → (의도별 분기) → generate → output_guardrail → END

의도: recipe_request, product_info, company_info, cooking_tip,
      ingredient_search, serving_adjust, ingredient_sub, greeting, out_of_scope
"""

import copy
import json
import logging
import os
import re
from typing import TypedDict

logger = logging.getLogger(__name__)

from langgraph.graph import StateGraph, END

CRAG_CORRECT_THRESHOLD = float(os.getenv("CRAG_CORRECT_THRESHOLD", "0.5"))
CRAG_AMBIGUOUS_THRESHOLD = float(os.getenv("CRAG_AMBIGUOUS_THRESHOLD", "0.3"))
CRAG_INCORRECT_RETRY_THRESHOLD = float(os.getenv("CRAG_INCORRECT_RETRY_THRESHOLD", "0.25"))

VALID_TASTES = {"매운", "고소", "담백", "달콤", "새콤", "짭짤", "바삭", "감칠맛", "얼큰"}

TASTE_ALIASES = {
    "매콤": "매운", "맵다": "매운", "칼칼": "매운", "칼칼한": "매운",
    "매콤한": "매운", "매운맛": "매운", "스파이시": "매운",
    "고소하다": "고소", "고소한": "고소",
    "달다": "달콤", "달달": "달콤", "달달한": "달콤", "달콤한": "달콤",
    "상큼": "새콤", "시큼": "새콤", "새콤달콤": "새콤", "상큼한": "새콤",
    "짭짤한": "짭짤", "짠": "짭짤",
    "바삭한": "바삭", "바삭바삭": "바삭", "크리스피": "바삭",
    "얼큰한": "얼큰",
    "감칠맛나는": "감칠맛", "우마미": "감칠맛",
    "담백한": "담백", "깔끔": "담백", "깔끔한": "담백",
}

CATEGORY_KEYWORDS = {
    "면": ["국수", "쌀국수", "분짜", "분보", "분", "면", "라면", "미꽝", "후띠에우", "팟타이", "phở", "bún", "mì"],
    "국물": ["국", "탕", "찌개", "전골", "수프", "라우", "까인", "lẩu", "canh"],
    "볶음": ["볶음", "볶다", "xào"],
    "구이": ["구이", "굽다", "바비큐", "BBQ", "nướng"],
    "밥": ["밥", "볶음밥", "비빔밥", "cơm", "xôi"],
    "샐러드": ["샐러드", "겉절이", "gỏi"],
    "음료": ["음료", "주스", "스무디", "라떼", "sinh tố"],
    "디저트": ["디저트", "과자", "케이크", "아이스크림"],
    "스낵": ["스낵", "간식", "튀김", "팝콘"],
}


# ─── PipelineState ───
class PipelineState(TypedDict):
    message: str
    language: str
    conversation_history: list
    intent: str
    rag_context: str
    search_result: dict | None
    result: dict
    error: str | None
    max_similarity: float
    rewritten_query: str
    filters: dict
    hyde_doc: str


# ─── Input Guardrail: 프롬프트 인젝션 패턴 ───
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?)", re.I),
    re.compile(r"(pretend|act)\s+(you\s+are|as\s+if|to\s+be)", re.I),
    re.compile(r"(system\s*prompt|내부\s*지시|시스템\s*프롬프트)", re.I),
    re.compile(r"(disregard|forget|override)\s+(everything|all|instructions?)", re.I),
    re.compile(r"(DAN|jailbreak|do\s+anything\s+now)", re.I),
    re.compile(r"(repeat|show|reveal|print)\s+(the\s+)?(system|instructions?|prompt)", re.I),
]

BLOCKED_REPLY = "저는 다미푸드의 K-푸드 챗봇입니다. 레시피 추천이나 제품 관련 질문을 도와드릴 수 있어요! 무엇이 궁금하신가요?"


def _check_injection(text: str) -> bool:
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


# ─── 노드 1: input_guardrail ───
async def input_guardrail_node(state: PipelineState) -> dict:
    msg = state["message"].strip()
    if not msg:
        return {"error": "안녕하세요! 다미푸드 챗봇입니다. 레시피 추천이나 제품 관련 질문을 해주세요!"}
    if _check_injection(msg):
        return {"error": BLOCKED_REPLY}
    return {"message": msg}


# ─── 노드 2: classify_intent (7의도) ───
INTENT_PROMPT = """사용자 메시지의 의도를 분류하세요.

## 의도 목록 및 예시
1. recipe_request: 레시피/요리법을 원할 때
   예: "매콤한 쌀국수", "BBQ 레시피", "Phở cay recipe", "간단한 볶음 요리"
   예: "비건 요리 만들고 싶어", "달콤한 디저트 레시피"
2. product_info: 제품 정보(가격/성분/영양/종류)를 물을 때
   예: "코인육수 가격", "김부각 칼로리", "소스 종류 알려줘", "비건 제품 있어?"
3. company_info: 회사/배송/주문/구매/연락처 관련
   예: "배송 얼마나 걸려?", "다미푸드 연락처", "대량 구매 가능?", "주문 방법"
4. cooking_tip: 요리 팁/보관법 (특정 레시피 요청이 아님)
   예: "고수 보관법", "쌀국수 삶는 팁", "양파 안 매운 법"
5. ingredient_search: "~있어", "~있는데 뭐 만들지" 패턴
   예: "소고기, 양파 있어", "냉장고에 닭고기랑 버섯"
6. serving_adjust: 인분 변경 요청 (이전 대화의 레시피 기준)
   예: "4인분으로", "2인분으로 줄여줘"
7. ingredient_sub: 재료 대체 요청
   예: "고수 대신 뭘 쓸까?", "느억맘 없으면?"
8. greeting: 인사, 감사, 작별 표현
   예: "안녕하세요", "고마워", "Hello", "Xin chào", "감사합니다", "잘 가"
9. out_of_scope: K-food/레시피/제품/회사와 무관한 질문
   예: "날씨 어때?", "주식 추천해줘", "게임 추천", "What time is it?"

## 오분류 방지 가이드 (중요!)
- "~만들고 싶어", "~레시피", "~요리" → recipe_request (product_info 아님)
- "~가격", "~성분", "~칼로리", "~종류" → product_info (recipe_request 아님)
- "연락처", "전화번호", "배송", "주문", "구매 가능", "대량" → company_info
- "~보관", "~팁", "~방법" (특정 요리 없이) → cooking_tip
- 재료만 나열하고 "있어/있는데" → ingredient_search (recipe_request 아님)
- "~인분으로" → serving_adjust
- "~대신", "~대체", "~없으면" → ingredient_sub
- "안녕", "하이", "Hello", "Xin chào", "고마워", "감사합니다" → greeting (recipe_request 아님!)
- 음식/레시피/제품/회사와 전혀 관련 없는 질문 → out_of_scope

메시지: {query}

의도 (위 9개 중 하나만 반환, 다른 텍스트 없이):"""


async def classify_intent(message: str) -> str:
    """독립 호출 가능 — STEP 11 평가에서 사용"""
    from services.recipe_ai import call_gpt_mini
    prompt = INTENT_PROMPT.format(query=message)
    result = await call_gpt_mini(prompt, max_tokens=20, temperature=0.1)
    # gpt-4.1-mini may return "의도: product_info" — strip any prefix
    cleaned = result.strip().lower().replace(" ", "_")
    valid = [
        "recipe_request", "product_info", "company_info", "cooking_tip",
        "ingredient_search", "serving_adjust", "ingredient_sub",
        "greeting", "out_of_scope",
    ]
    # Extract the valid intent from anywhere in the response
    for v in valid:
        if v in cleaned:
            return v
    return "out_of_scope"


async def classify_intent_node(state: PipelineState) -> dict:
    try:
        intent = await classify_intent(state["message"])
    except Exception as e:
        logger.warning(f"classify_intent failed: {e}, defaulting to recipe_request")
        intent = "recipe_request"
    return {"intent": intent}


# ─── 노드 3: query_rewrite ───
async def query_rewrite_node(state: PipelineState) -> dict:
    """대화 맥락에서 짧은 follow-up 질문을 완전한 질문으로 재작성."""
    history = state.get("conversation_history") or []
    message = state["message"]

    if not history:
        return {"rewritten_query": message}

    from services.recipe_ai import call_gpt_mini

    recent = history[-4:]
    history_text = "\n".join(
        f"{t.get('role', 'user')}: {str(t.get('content', ''))[:200]}"
        for t in recent
    )

    prompt = f"""이전 대화를 참고하여 다음 질문을 완전한 문장으로 재작성하세요.
대명사나 생략된 맥락을 복원하여 독립적으로 이해 가능한 질문으로 만드세요.
재작성된 질문만 출력하세요.

이전 대화:
{history_text}

현재 질문: {message}
재작성:"""

    try:
        rewritten = await call_gpt_mini(prompt, max_tokens=100, temperature=0.2)
        return {"rewritten_query": rewritten.strip() or message}
    except Exception as e:
        logger.warning(f"query_rewrite failed: {e}, using original message")
        return {"rewritten_query": message}


# ─── 노드 4: query_understanding ───
async def query_understanding_node(state: PipelineState) -> dict:
    """자연어 → 구조화 필터 추출."""
    from services.recipe_ai import call_gpt_mini

    query = state.get("rewritten_query") or state["message"]

    prompt = f"""다음 요리 관련 질문에서 필터 조건을 JSON으로 추출하세요.

추출 필드:
- category: "면"|"국물"|"볶음"|"구이"|"밥"|"샐러드"|"음료"|"디저트"|"스낵"|null
- taste: ["매운","고소","담백","달콤","새콤","짭짤","바삭","감칠맛","얼큰"] 중 해당하는 것들 (리스트)
- difficulty: "쉬움"|"보통"|"어려움"|null
- exclude_taste: 부정 조건의 맛 리스트 ("달지 않은" → ["달콤"])
- exclude_category: 제외할 카테고리 리스트 또는 null
- max_cook_time: 숫자(분) 또는 null ("30분 이내" → 30)

질문: {query}
JSON:"""

    raw = await call_gpt_mini(
        prompt,
        max_tokens=150,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}

    # category 키워드 교차검증: GPT 결과를 키워드로 검증/보정
    query_lower = query.lower()
    keyword_category = None
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            keyword_category = cat
            break

    if not parsed.get("category"):
        # GPT가 category 추출 실패 시 키워드 폴백
        if keyword_category:
            parsed["category"] = keyword_category
            logger.info(f"Keyword fallback → category: {keyword_category}")
    elif keyword_category and parsed["category"] != keyword_category:
        # GPT가 추출한 category와 키워드 매칭 결과가 다르면 키워드 우선
        logger.info(f"Keyword override: GPT={parsed['category']} → keyword={keyword_category}")
        parsed["category"] = keyword_category

    # taste와 exclude_taste가 리스트인지 보장
    if not isinstance(parsed.get("taste"), list):
        parsed["taste"] = [parsed["taste"]] if parsed.get("taste") else []
    if not isinstance(parsed.get("exclude_taste"), list):
        parsed["exclude_taste"] = [parsed["exclude_taste"]] if parsed.get("exclude_taste") else []

    # taste 화이트리스트 검증 + 동의어 매핑
    normalized = []
    for t in parsed.get("taste", []):
        t = t.strip()
        if t in VALID_TASTES:
            normalized.append(t)
        elif t in TASTE_ALIASES:
            normalized.append(TASTE_ALIASES[t])
        else:
            logger.warning(f"Unknown taste filter ignored: {t}")
    parsed["taste"] = list(set(normalized))

    # taste 키워드 폴백: GPT가 빈 리스트 반환 시 TASTE_ALIASES로 보충
    if not parsed["taste"]:
        query_lower = query.lower()
        for alias, canonical in TASTE_ALIASES.items():
            if alias in query_lower:
                parsed["taste"] = [canonical]
                logger.info(f"Keyword fallback → taste: {canonical}")
                break

    # exclude_taste도 동일 처리
    normalized_ex = []
    for t in parsed.get("exclude_taste", []):
        t = t.strip()
        if t in VALID_TASTES:
            normalized_ex.append(t)
        elif t in TASTE_ALIASES:
            normalized_ex.append(TASTE_ALIASES[t])
    parsed["exclude_taste"] = list(set(normalized_ex))

    return {"filters": parsed}


# ─── 노드 5: hyde (Hypothetical Document Embedding) ───
async def hyde_node(state: PipelineState) -> dict:
    """가상 레시피 문서 생성 → 더 나은 임베딩 매칭."""
    from services.recipe_ai import call_gpt_mini

    query = state.get("rewritten_query") or state["message"]

    prompt = f"""Generate a hypothetical recipe document for the following query.
Include Vietnamese name, English name, Korean title, main ingredients (3-5), and brief cooking steps (2-3).
Format:
Vietnamese: [Vietnamese dish name]
English: [English dish name]
[Korean recipe title]
재료: ...
조리법: ...

Query: {query}
Document:"""

    try:
        doc = await call_gpt_mini(prompt, max_tokens=200, temperature=0.3)
        return {"hyde_doc": doc.strip()}
    except Exception as e:
        logger.warning(f"hyde_node failed: {e}, skipping HyDE")
        return {"hyde_doc": ""}


# ─── CRAG: 저관련도 청크 제거 ───
def _refine_context(context: str, threshold: float = 0.3) -> str:
    """저관련도 청크 제거"""
    chunks = context.split("\n---\n")
    refined = []
    for chunk in chunks:
        match = re.search(r'sim=([\d.]+)', chunk)
        if match and float(match.group(1)) >= threshold:
            refined.append(chunk.strip())
    return "\n---\n".join(refined) if refined else context


# ─── 노드 6: search (CRAG 포함) ───
async def search_node(state: PipelineState) -> dict:
    try:
        return await _search_node_inner(state)
    except Exception as e:
        logger.error(f"search_node failed: {e}")
        return {"rag_context": "", "max_similarity": 0.0, "search_result": None}


async def _search_node_inner(state: PipelineState) -> dict:
    from services.recipe_search import search_similar_recipes

    intent = state["intent"]
    filters = state.get("filters") or {}

    # 의도별 where 조건 구성
    if intent == "recipe_request":
        where_conditions = [{"type": "recipe"}]

        if filters.get("category"):
            where_conditions.append({"category": filters["category"]})

        for t in (filters.get("taste") or []):
            where_conditions.append({f"taste_{t}": "true"})

        for t in (filters.get("exclude_taste") or []):
            where_conditions.append({f"taste_{t}": "false"})

        if filters.get("max_cook_time"):
            where_conditions.append({"cook_time_minutes": {"$lte": filters["max_cook_time"]}})

        if filters.get("difficulty"):
            where_conditions.append({"difficulty": filters["difficulty"]})

    elif intent == "product_info":
        where_conditions = [{"$or": [{"type": "product"}, {"type": "comparison"}]}]
    elif intent == "company_info":
        where_conditions = [{"type": "company"}]
    elif intent == "cooking_tip":
        where_conditions = [{"$or": [{"type": "cooking_tip"}, {"type": "recipe"}, {"type": "product"}]}]
    else:
        where_conditions = []

    # where 조합
    if len(where_conditions) >= 2:
        where = {"$and": where_conditions}
    elif len(where_conditions) == 1:
        where = where_conditions[0]
    else:
        where = None

    # 검색 쿼리: hyde_doc 우선 → rewritten_query → message
    search_query = state.get("hyde_doc") or state.get("rewritten_query") or state["message"]

    # intent별 top_k 조정
    if intent == "product_info":
        top_k = 8
    elif intent == "company_info":
        top_k = 3
    elif intent == "cooking_tip":
        top_k = 3
    else:
        top_k = 5

    # "다른 레시피" 요청 시에만 이전 추천 recipe_id 제외
    ANOTHER_KEYWORDS = [
        "다른", "다르", "또 ", "새로운", "말고", "제외",
        "another", "other", "different", "instead",
        "khác", "món khác", "cái khác",
    ]
    original_msg = (state.get("message") or "").lower()
    wants_different = any(kw in original_msg for kw in ANOTHER_KEYWORDS)

    exclude_ids = []
    if wants_different:
        for turn in (state.get("conversation_history") or []):
            content = str(turn.get("content", ""))
            for rid_match in re.finditer(r'"recipe_id"\s*:\s*"([^"]+)"', content):
                exclude_ids.append(rid_match.group(1))

    result = await search_similar_recipes(
        query=search_query, top_k=top_k, filters=where,
        exclude_ids=exclude_ids if exclude_ids else None,
    )

    # recipe_request 필터 fallback: 결과가 부족하면 단계적 필터 완화
    if intent == "recipe_request" and (not result or result.get("result_count", 0) < 2):
        count = result.get("result_count", 0) if result else 0
        # Step 1: taste 필터만 제거, category 유지
        if filters.get("category"):
            logger.info(f"Filter fallback step1: 결과 {count}개, taste 제거 → category={filters['category']}만")
            cat_only_where = {"$and": [{"type": "recipe"}, {"category": filters["category"]}]}
            result = await search_similar_recipes(
                query=search_query, top_k=5, filters=cat_only_where,
                exclude_ids=exclude_ids if exclude_ids else None,
            )
        # Step 2: 여전히 부족하면 모든 필터 제거
        if not result or result.get("result_count", 0) < 2:
            logger.info(f"Filter fallback step2: category도 제거 → type=recipe만")
            fallback_where = {"type": "recipe"}
            result = await search_similar_recipes(
                query=search_query, top_k=5, filters=fallback_where,
                exclude_ids=exclude_ids if exclude_ids else None,
            )

    if not result:
        return {"rag_context": "", "max_similarity": 0.0, "search_result": None}

    max_sim = result["max_similarity"]

    # CRAG 3단계 판별
    if max_sim >= CRAG_CORRECT_THRESHOLD:
        context = result["context"]
        logger.info(f"CRAG: Correct (sim={max_sim:.3f})")
    elif max_sim >= CRAG_AMBIGUOUS_THRESHOLD:
        context = _refine_context(result["context"], threshold=CRAG_AMBIGUOUS_THRESHOLD)
        logger.info(f"CRAG: Ambiguous (sim={max_sim:.3f}), refined")
    else:
        # ★ CRAG Incorrect: 원본 메시지로 재검색 시도 (hyde/rewrite 우회)
        original_message = state["message"]
        retried = False
        if intent == "recipe_request" and original_message and original_message != search_query:
            logger.info(f"CRAG: Incorrect (sim={max_sim:.3f}), retrying with original message")
            retry_result = await search_similar_recipes(
                query=original_message, top_k=5, filters=where
            )
            if retry_result and retry_result["max_similarity"] >= CRAG_INCORRECT_RETRY_THRESHOLD:
                context = retry_result["context"]
                max_sim = retry_result["max_similarity"]
                result = retry_result
                retried = True
                logger.info(f"CRAG: Retry succeeded (sim={max_sim:.3f})")

        if not retried:
            # 원본 재검색도 실패했지만, recipe_request면 기존 결과라도 전달
            if intent == "recipe_request" and result.get("result_count", 0) > 0:
                context = result["context"]
                logger.info(f"CRAG: Low-sim recipe fallback (sim={max_sim:.3f}), passing results anyway")
            else:
                context = ""
                logger.info(f"CRAG: Incorrect (sim={max_sim:.3f}), no results")

    return {
        "rag_context": context,
        "max_similarity": max_sim,
        "search_result": result,
    }


# ─── Intent → Response Type 강제 매핑 ───
INTENT_TYPE_MAP = {
    "recipe_request": "recipe",
    "ingredient_search": "recipe",
    "product_info": "chat",
    "company_info": "chat",
    "cooking_tip": "chat",
    "serving_adjust": "chat",
    "ingredient_sub": "chat",
    "greeting": "chat",
    "out_of_scope": "chat",
}


# ─── 노드 7: generate ───
async def generate_node(state: PipelineState) -> dict:
    from services.recipe_ai import call_gpt, _format, _apply_translation

    try:
        rag_context = state.get("rag_context") or None
        raw = await call_gpt(
            message=state["message"],
            language=state["language"],
            conversation_history=state["conversation_history"],
            rag_context=rag_context,
        )
        raw_copy = copy.deepcopy(raw)
        formatted = _format(raw)
        formatted["_raw"] = raw_copy

        # Intent 기반 type 강제 교정
        intent = state.get("intent", "")
        expected_type = INTENT_TYPE_MAP.get(intent, "chat")
        # serving_adjust는 GPT가 recipe 구조를 반환할 수 있으므로 GPT 응답을 존중
        if intent == "serving_adjust" and formatted.get("type") == "recipe":
            pass  # GPT가 recipe를 반환했으면 그대로 유지
        elif (formatted.get("type") == "recipe"
              and formatted.get("title")
              and formatted.get("ingredients")
              and formatted.get("steps")
              and formatted.get("recipe_id")):
            # GPT가 유효한 recipe_id 포함 완전한 레시피를 반환 → type 존중
            logger.info(f"Type override skipped: complete recipe with id={formatted.get('recipe_id')} for intent '{intent}'")
        elif formatted.get("type") != expected_type:
            logger.warning(f"Type mismatch: GPT returned '{formatted.get('type')}', forcing '{expected_type}' for intent '{intent}'")
            formatted["type"] = expected_type

        # 빈 recipe 응답 fallback
        if formatted.get("type") == "recipe":
            title = formatted.get("title", "")
            ingredients = formatted.get("ingredients", [])
            steps = formatted.get("steps", [])
            if not title or not ingredients or not steps:
                logger.warning(f"Empty recipe detected: title='{title}', ingredients={len(ingredients)}, steps={len(steps)}")
                fallback_reply = raw.get("reply", "") or raw.get("title", "") or "레시피를 찾지 못했습니다. 다른 키워드로 검색해 보세요."
                formatted = {
                    "type": "chat",
                    "reply": fallback_reply,
                    "links": formatted.get("links", []),
                    "_raw": raw_copy,
                }

        # 번역 적용 (language가 vi/en이면 translations.json에서 교체)
        formatted = _apply_translation(formatted, state["language"])

        # recipe 타입: AI 이미지 생성/캐시
        if formatted.get("type") == "recipe":
            recipe_id = formatted.get("recipe_id", "")
            if recipe_id:
                try:
                    from services.image_generator import generate_recipe_image, get_cached_image
                    cached = get_cached_image(recipe_id)
                    if cached:
                        formatted["image_url"] = cached
                    else:
                        image_url = await generate_recipe_image(
                            recipe_id,
                            formatted.get("title", ""),
                            formatted.get("title_vn", ""),
                        )
                        formatted["image_url"] = image_url
                except Exception as img_err:
                    logger.warning(f"Image generation failed for {recipe_id}: {img_err}")
                    formatted["image_url"] = ""

        return {"result": formatted}
    except Exception as e:
        return {"result": {"type": "chat", "reply": f"응답 생성 중 오류: {e}", "links": []}}


# ─── 노드 8: output_guardrail ───
async def output_guardrail_node(state: PipelineState) -> dict:
    from services.output_guardrail import check_output
    try:
        checked = await check_output(state.get("result", {}))
        return {"result": checked}
    except Exception as e:
        logger.warning(f"Output guardrail failed: {e}")
        return {}


# ─── 노드 9: ingredient_search ───
async def ingredient_search_node(state: PipelineState) -> dict:
    """재료 기반 역추천: 메시지에서 재료 추출 → 매칭 레시피 검색."""
    from services.recipe_ai import call_gpt_mini
    from services.ingredient_search import search_by_ingredients

    # GPT로 재료 추출
    prompt = f"""다음 메시지에서 요리 재료만 쉼표로 나열하세요. 재료가 아닌 것은 제외하세요.
메시지: {state["message"]}
재료:"""
    raw = await call_gpt_mini(prompt, max_tokens=100, temperature=0.2)
    ingredients = [ing.strip() for ing in raw.split(",") if ing.strip()]

    if not ingredients:
        return {"rag_context": ""}

    results = await search_by_ingredients(ingredients, top_k=5)

    if not results:
        return {"rag_context": ""}

    # rag_context 포맷 구성
    context_parts = []
    for r in results:
        context_parts.append(
            f"[recipe:{r['id']} match={r['match_count']}/{r['total_ingredients']}]\n"
            f"이름: {r['name']}\n"
            f"카테고리: {r['category']}\n"
            f"제품: {r['product_id']}\n"
            f"매칭 재료: {', '.join(r['matched'])}\n"
            f"전체 재료: {', '.join(r['ingredients'])}"
        )

    context = "\n---\n".join(context_parts)
    return {"rag_context": context}


# ─── 노드 10: serving_adjust ───
async def serving_adjust_node(state: PipelineState) -> dict:
    """인분 조절: 대화 히스토리에서 레시피 찾아 인분 변경."""
    import re, json as _json

    history = state.get("conversation_history") or []

    # 마지막 레시피 응답 찾기
    last_recipe = None
    base_servings = 2  # 기본값
    for turn in reversed(history):
        content = str(turn.get("content", ""))
        if "ingredients" in content or "재료" in content or "recipe" in content.lower():
            last_recipe = content[:800]
            # base_servings 추출 시도
            try:
                parsed = _json.loads(content)
                base_servings = parsed.get("base_servings", 2)
            except Exception:
                bs_match = re.search(r'"base_servings"\s*:\s*(\d+)', content)
                if bs_match:
                    base_servings = int(bs_match.group(1))
            break

    context = ""
    if last_recipe:
        # 언어 정보 추가
        lang = state.get("language", "ko")
        lang_instruction = {
            "ko": "한국어로 응답하세요.",
            "vi": "Trả lời bằng tiếng Việt.",
            "en": "Answer in English."
        }.get(lang, "한국어로 응답하세요.")

        context = (
            f"[이전 레시피 정보 (기준 {base_servings}인분)]\n"
            f"{last_recipe}\n\n"
            f"⚠️ 위 레시피는 {base_servings}인분 기준입니다. "
            f"사용자가 요청한 인분 수에 맞게 모든 재료의 양을 비례 조절하세요. "
            f"예: {base_servings}인분→4인분이면 모든 재료를 {4/base_servings:.1f}배로 곱하세요.\n"
            f"⚠️ {lang_instruction}"
        )

    return {"rag_context": context}


# ─── 노드 11: ingredient_sub ───
async def ingredient_sub_node(state: PipelineState) -> dict:
    """재료 대체 추천: 다미푸드 제품으로 대체 가능한 옵션 제시."""
    from services.recipe_search import search_similar_recipes

    context_parts = []

    # 제품 검색: 대체 가능한 다미푸드 제품
    product_result = await search_similar_recipes(
        query=state["message"], top_k=2, filters={"type": "product"}
    )
    if product_result:
        context_parts.append(f"[대체 가능 제품 정보]\n{product_result['context']}")

    # 레시피 검색: 해당 재료를 사용하는 레시피 참고
    recipe_result = await search_similar_recipes(
        query=state["message"], top_k=2, filters={"type": "recipe"}
    )
    if recipe_result:
        context_parts.append(f"[관련 레시피]\n{recipe_result['context']}")

    return {"rag_context": "\n---\n".join(context_parts)}


# ─── 그래프 빌드 (7의도 분기) ───
def build_chat_graph():
    graph = StateGraph(PipelineState)

    # 11개 노드 등록
    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("query_rewrite", query_rewrite_node)
    graph.add_node("query_understanding", query_understanding_node)
    graph.add_node("hyde", hyde_node)
    graph.add_node("search", search_node)
    graph.add_node("generate", generate_node)
    graph.add_node("output_guardrail", output_guardrail_node)
    graph.add_node("ingredient_search", ingredient_search_node)
    graph.add_node("serving_adjust", serving_adjust_node)
    graph.add_node("ingredient_sub", ingredient_sub_node)

    graph.set_entry_point("input_guardrail")

    # input_guardrail 분기
    graph.add_conditional_edges(
        "input_guardrail",
        lambda s: "blocked" if s.get("error") else "ok",
        {"blocked": END, "ok": "classify_intent"},
    )

    # classify_intent 분기 (7의도)
    def route_intent(state):
        intent = state.get("intent", "recipe_request")
        if intent == "recipe_request":
            return "recipe"
        elif intent in ("product_info", "company_info"):
            return "search_direct"
        elif intent == "cooking_tip":
            return "search_direct"
        elif intent == "ingredient_search":
            return "ingredient"
        elif intent == "serving_adjust":
            return "serving"
        elif intent == "ingredient_sub":
            return "sub"
        elif intent in ("greeting", "out_of_scope"):
            return "generate_direct"
        return "recipe"

    graph.add_conditional_edges("classify_intent", route_intent, {
        "recipe": "query_rewrite",
        "search_direct": "search",
        "generate_direct": "generate",
        "ingredient": "ingredient_search",
        "serving": "serving_adjust",
        "sub": "ingredient_sub",
    })

    # recipe 경로: query_rewrite → query_understanding → hyde → search
    graph.add_edge("query_rewrite", "query_understanding")
    graph.add_edge("query_understanding", "hyde")
    graph.add_edge("hyde", "search")

    # 공통: search → generate → output_guardrail → END
    graph.add_edge("search", "generate")
    graph.add_edge("generate", "output_guardrail")
    graph.add_edge("output_guardrail", END)

    # 신규 의도 → generate
    graph.add_edge("ingredient_search", "generate")
    graph.add_edge("serving_adjust", "generate")
    graph.add_edge("ingredient_sub", "generate")

    return graph.compile()


# ─── 실행 함수 ───
async def run_chat_pipeline(message: str, language: str, conversation_history: list, return_debug: bool = False) -> dict:
    graph = build_chat_graph()
    state = {
        "message": message,
        "language": language,
        "conversation_history": conversation_history or [],
        "intent": "",
        "rag_context": "",
        "search_result": None,
        "result": {},
        "error": None,
        "max_similarity": 0.0,
        "rewritten_query": "",
        "filters": {},
        "hyde_doc": "",
    }
    final = await graph.ainvoke(state)
    if final.get("error"):
        return {"type": "chat", "reply": final["error"], "links": [], "_raw": None}
    result = final.get("result", {"type": "chat", "reply": "응답 생성 실패"})
    if return_debug:
        result["_debug"] = {
            "rag_context": final.get("rag_context", ""),
            "intent": final.get("intent", ""),
            "max_similarity": final.get("max_similarity", 0),
            "filters": final.get("filters", {}),
            "rewritten_query": final.get("rewritten_query", ""),
            "hyde_doc": final.get("hyde_doc", ""),
        }
    return result
