"""Output Guardrail — GPT 응답 검증"""
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# 유효 제품 ID 로드
_VALID_PRODUCTS = None


def _get_valid_products() -> dict:
    global _VALID_PRODUCTS
    if _VALID_PRODUCTS is None:
        data = json.loads(Path("data/products.json").read_text(encoding="utf-8"))
        _VALID_PRODUCTS = {p["id"]: p for p in data["products"]}
    return _VALID_PRODUCTS


# 적합/부적합 매핑 (product_details에서 추출)
PRODUCT_SUITABILITY = {
    "coin_01": {"suitable": ["국물", "면", "전골", "찌개"], "unsuitable": ["디저트", "음료", "샐러드"]},
    "coin_02": {"suitable": ["국물", "면", "죽", "찌개"], "unsuitable": ["디저트", "구이", "음료"]},
    "coin_03": {"suitable": ["국물", "면", "전골", "채식"], "unsuitable": ["디저트", "음료"]},
    "coin_04": {"suitable": ["국물", "면", "전골", "볶음"], "unsuitable": ["디저트", "음료", "죽"]},
    "season_01": {"suitable": ["구이", "볶음", "밥"], "unsuitable": ["국물", "디저트", "음료"]},
    "season_02": {"suitable": ["전골", "밥", "볶음"], "unsuitable": ["디저트", "음료", "샐러드"]},
    "season_03": {"suitable": ["닭요리", "볶음", "스낵"], "unsuitable": ["국물", "디저트", "해산물"]},
    "season_04": {"suitable": ["죽", "수프", "리조또"], "unsuitable": ["구이", "볶음", "스낵"]},
    "sauce_01": {"suitable": ["디핑", "샌드위치", "튀김", "샐러드"], "unsuitable": ["국물", "전골"]},
    "sauce_02": {"suitable": ["해산물", "냉채", "마리네이드"], "unsuitable": ["디저트", "볶음"]},
    "sauce_03": {"suitable": ["쌈", "월남쌈", "구이", "샐러드"], "unsuitable": ["국물", "디저트"]},
    "sauce_04": {"suitable": ["볶음", "면", "파스타"], "unsuitable": ["국물", "디저트", "디핑"]},
    "sauce_05": {"suitable": ["구이", "바비큐", "마리네이드"], "unsuitable": ["국물", "디저트", "음료"]},
    "sauce_06": {"suitable": ["치킨윙", "튀김", "글레이즈"], "unsuitable": ["국물", "죽"]},
    "food_01": {"suitable": ["음료", "디저트", "스무디", "토핑"], "unsuitable": ["국물", "볶음", "구이"]},
    "food_02": {"suitable": ["토핑", "안주", "스낵"], "unsuitable": ["국물", "디저트", "음료"]},
}

COMPETITOR_KEYWORDS = [
    "오뚜기", "CJ", "비비고", "bibigo", "삼양", "농심",
    "대상", "청정원", "샘표", "하인즈", "Heinz",
]


async def check_output(result: dict) -> dict:
    """GPT 응답 검증 — 문제 있으면 수정/경고 추가"""
    if not result or not isinstance(result, dict):
        return result

    warnings = []

    # 1. product_id 유효성
    pid = result.get("product_id", "")
    if pid and pid not in _get_valid_products():
        warnings.append(f"존재하지 않는 제품 ID: {pid}")
        result["product_id"] = ""

    # 2. 적합/부적합 검증 (recipe 타입만)
    if result.get("type") == "recipe" and pid in PRODUCT_SUITABILITY:
        category = result.get("category", "")
        unsuitable = PRODUCT_SUITABILITY[pid]["unsuitable"]
        if category and any(u in category for u in unsuitable):
            warnings.append(f"{pid}는 '{category}' 요리에 부적합")

    # 3. 경쟁사 언급 필터링
    reply = result.get("reply", "") or json.dumps(result, ensure_ascii=False)
    for comp in COMPETITOR_KEYWORDS:
        if comp.lower() in reply.lower():
            warnings.append(f"경쟁사 언급 감지: {comp}")
            # reply에서 경쟁사명 제거
            if "reply" in result:
                result["reply"] = result["reply"].replace(comp, "***")

    # 4. 가격 검증 (product_id가 있으면)
    if pid and pid in _get_valid_products():
        correct_price = _get_valid_products()[pid].get("price_display", "")
        if correct_price and "reply" in result:
            reply_text = result.get("reply", "")
            prices_in_reply = re.findall(r'₫[\d,.\s]+|[\d,]+\s*(?:VND|원|đ)', reply_text)
            for wrong_price in prices_in_reply:
                wrong_clean = re.sub(r'\s', '', wrong_price)
                correct_clean = re.sub(r'\s', '', correct_price)
                if wrong_clean != correct_clean:
                    result["reply"] = reply_text.replace(wrong_price, correct_price)
                    warnings.append(f"가격 교정: {wrong_price} → {correct_price}")

    if warnings:
        result["_guardrail_warnings"] = warnings
        logger.warning(f"Output Guardrail warnings: {warnings}")

    return result
