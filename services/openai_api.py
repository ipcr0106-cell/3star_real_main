"""
★ openai_api.py — OpenAI GPT-4o-mini 호출 함수 모음 ★

[역할]
여러 라우터(recipe_chatbot, news_summary, review_keyword, sns_generator)에서
공통으로 사용하는 OpenAI 호출 함수를 모아놓은 파일.

[사용법]
from services.openai_api import generate_recipe_text
result = await generate_recipe_text(ingredients, rag_context)
"""

import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def generate_recipe_text(ingredients: list, rag_context: str, language: str = "vi") -> dict:
    """[파트B용] 재료 + RAG 결과 → 레시피 생성"""
    # TODO: openai 패키지로 GPT-4o-mini 호출
    pass


async def summarize_news(articles: list) -> dict:
    """[파트C용] 베트남 뉴스 → 한국어 요약 + 마케팅 인사이트"""
    # TODO: 구현
    pass


async def extract_review_keywords(reviews: list) -> dict:
    """[파트D용] 리뷰 텍스트 → 긍정/부정 키워드 추출"""
    # TODO: 구현
    pass


async def generate_sns_content(trends: list, product: str) -> dict:
    """[파트E용] YouTube 트렌드 → 틱톡 대본 + DM 생성"""
    # TODO: 구현
    pass
