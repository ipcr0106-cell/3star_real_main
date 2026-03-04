"""
★ youtube_api.py — YouTube 트렌드 수집 ★

[역할]
YouTube Data API v3 → 베트남 인기 먹방/K-food 영상 조회수·해시태그 수집
무료 할당량: 하루 10,000 유닛

[사용법]
from services.youtube_api import search_food_trends
trends = await search_food_trends("K-food Vietnam")
"""

import os
from dotenv import load_dotenv

load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


async def search_food_trends(keyword: str = "K-food Vietnam", max_results: int = 10) -> list:
    """베트남 인기 먹방 영상 트렌드 수집"""
    # TODO: YouTube Data API v3 구현
    pass


async def get_channel_info(channel_id: str) -> dict:
    """인플루언서 채널 정보 (구독자, 평균 조회수)"""
    # TODO: 구현
    pass
