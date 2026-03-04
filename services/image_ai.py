"""
★ image_ai.py — Together AI 음식 이미지 생성 ★

[역할]
레시피 설명 텍스트 → Together AI에 전달 → 음식 이미지 생성
가입 시 $5 무료 크레딧 → 약 1,500장 생성 가능

[사용법]
from services.image_ai import generate_food_image
result = await generate_food_image("Vietnamese pho with Korean coin broth")
"""

import os
from dotenv import load_dotenv

load_dotenv()
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")


async def generate_food_image(prompt: str, filename: str = "food.png") -> dict:
    """음식 설명 → 이미지 생성 → 저장"""
    # TODO: Together AI API 호출
    pass
