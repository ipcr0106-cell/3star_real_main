"""
★ pdf_maker.py — 레시피 카드뉴스 PDF 생성 ★

[역할]
레시피 텍스트 + 음식 이미지 → 예쁜 카드뉴스 PDF
→ SNS 바이럴 유도용 다운로드 가능

[사용법]
from services.pdf_maker import create_recipe_pdf
pdf_path = await create_recipe_pdf(recipe_data, image_path)
"""


async def create_recipe_pdf(recipe: dict, image_path: str, output_path: str = "static/pdf/") -> str:
    """레시피 + 이미지 → PDF 카드뉴스 생성"""
    # TODO: reportlab으로 구현
    pass
