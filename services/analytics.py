"""
★ 사용 로그 수집 + 통계 집계 (analytics.py) ★

JSONL 파일 기반 이벤트 로깅.
저장: data/analytics/YYYY-MM-DD.jsonl
"""

import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

ANALYTICS_DIR = Path("data/analytics")
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

PRODUCTS_JSON = Path("data/products.json")


def _load_product_names() -> dict[str, str]:
    """products.json에서 id → 한글 이름 매핑 로드."""
    try:
        data = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
        return {p["id"]: p.get("name", p["id"]) for p in data.get("products", [])}
    except Exception:
        return {}


def log_event(event_type: str, data: dict):
    """이벤트를 JSONL 파일에 append. 실패해도 서비스 영향 없음."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        filepath = ANALYTICS_DIR / f"{today}.jsonl"
        entry = {
            "ts": datetime.now().isoformat(),
            "event": event_type,
            **data,
        }
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"log_event failed: {e}")


def _load_events(days: int = 7, event_type: str | None = None) -> list[dict]:
    """최근 N일 이벤트 로드. 파일 없으면 빈 리스트."""
    events = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        filepath = ANALYTICS_DIR / f"{date}.jsonl"
        if not filepath.exists():
            continue
        try:
            for line in filepath.read_text(encoding="utf-8").strip().split("\n"):
                if not line.strip():
                    continue
                entry = json.loads(line)
                if event_type is None or entry.get("event") == event_type:
                    events.append(entry)
        except Exception as e:
            logger.warning(f"_load_events failed for {date}: {e}")
    return events


def get_popular_recipes(days: int = 7) -> list[dict]:
    """recipe_id별 카운트, TOP 10."""
    events = _load_events(days, "recipe_search")
    counter = Counter()
    names = {}
    for e in events:
        rid = e.get("recipe_id", "")
        if rid:
            counter[rid] += 1
            if rid not in names:
                names[rid] = e.get("recipe_name", rid)
    return [
        {"recipe_id": rid, "name": names.get(rid, rid), "count": cnt}
        for rid, cnt in counter.most_common(10)
    ]


def get_cart_ranking(days: int = 7) -> list[dict]:
    """product_id별 카운트, TOP 10."""
    events = _load_events(days, "cart_add")
    product_names = _load_product_names()
    counter = Counter()
    for e in events:
        pid = e.get("product_id", "")
        if pid:
            qty = e.get("quantity", 1)
            counter[pid] += qty
    return [
        {"product_id": pid, "name": product_names.get(pid, pid), "count": cnt}
        for pid, cnt in counter.most_common(10)
    ]


CATEGORY_NORMALIZE = {
    "국물탕": "국물",
    "면볶음면": "면",
    "구이볶음": "구이/볶음",
    "쌈샐러드": "샐러드",
    "밥죽": "밥",
    "간식음료": "간식/음료",
}


def get_taste_trends(days: int = 7) -> list[dict]:
    """category+taste 조합별 카운트, TOP 15."""
    events = _load_events(days, "recipe_search")
    counter = Counter()
    for e in events:
        cat = e.get("category", "")
        cat = CATEGORY_NORMALIZE.get(cat, cat)
        taste = e.get("taste", "")
        if cat or taste:
            combo = f"{cat} + {taste}" if cat and taste else (cat or taste)
            counter[combo] += 1
    return [
        {"combination": combo, "count": cnt}
        for combo, cnt in counter.most_common(15)
    ]


def get_daily_stats(days: int = 30) -> list[dict]:
    """일별 통계."""
    result = []
    for i in range(days - 1, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        filepath = ANALYTICS_DIR / f"{date}.jsonl"
        searches = 0
        carts = 0
        total = 0
        if filepath.exists():
            try:
                for line in filepath.read_text(encoding="utf-8").strip().split("\n"):
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    total += 1
                    ev = entry.get("event", "")
                    if ev == "recipe_search":
                        searches += 1
                    elif ev == "cart_add":
                        carts += 1
            except Exception:
                pass
        result.append({
            "date": date,
            "total": total,
            "searches": searches,
            "carts": carts,
        })
    return result


def get_language_stats(days: int = 7) -> list[dict]:
    """언어별 통계."""
    events = _load_events(days, "recipe_search")
    counter = Counter()
    for e in events:
        lang = e.get("language", "unknown")
        counter[lang] += 1
    total = sum(counter.values()) or 1
    return [
        {"language": lang, "count": cnt, "percent": round(cnt / total * 100, 1)}
        for lang, cnt in counter.most_common()
    ]
