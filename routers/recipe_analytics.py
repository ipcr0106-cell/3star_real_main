"""
★ 분석 API 라우터 (recipe_analytics.py) ★

GET    /popular    — 인기 레시피 TOP 10
GET    /cart       — 장바구니 TOP 10
GET    /trends     — 맛/카테고리 트렌드        ← 대시보드용, 인증 없음
GET    /daily      — 일별 통계                ← 대시보드용, 인증 없음
GET    /languages  — 언어별 통계              ← 대시보드용, 인증 없음
POST   /log        — 이벤트 기록 (인증 불필요)
DELETE /reset      — 분석 데이터 초기화
"""

import glob
import os

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from services.admin_auth import verify_admin
from services.analytics import (
    get_cart_ranking,
    get_daily_stats,
    get_language_stats,
    get_popular_recipes,
    get_taste_trends,
    log_event,
)

router = APIRouter()


class LogRequest(BaseModel):
    event: str
    data: dict = {}


@router.post("/log")
async def post_log(body: LogRequest):
    log_event(body.event, body.data)
    return {"ok": True}


@router.get("/popular")
async def popular(days: int = Query(7, ge=1, le=90), _: dict = Depends(verify_admin)):
    return get_popular_recipes(days)


@router.get("/cart")
async def cart(days: int = Query(7, ge=1, le=90), _: dict = Depends(verify_admin)):
    return get_cart_ranking(days)


# ── 대시보드에서 직접 호출 — 포탈 로그인만 되어 있으면 OK ──
@router.get("/trends")
async def trends(days: int = Query(7, ge=1, le=90)):
    return get_taste_trends(days)


@router.get("/daily")
async def daily(days: int = Query(7, ge=1, le=90)):
    return get_daily_stats(days)


@router.get("/languages")
async def languages(days: int = Query(7, ge=1, le=90)):
    return get_language_stats(days)


@router.delete("/reset")
async def reset_analytics(_: dict = Depends(verify_admin)):
    for f in glob.glob("data/analytics/*.jsonl"):
        os.remove(f)
    return {"ok": True, "message": "Analytics data cleared"}