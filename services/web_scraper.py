"""
★ web_scraper.py — 쇼피/라자다 리뷰 스크래핑 ★

[역할]
경쟁사 제품 URL → Playwright로 브라우저 자동 조종 → 리뷰 텍스트 수집
Apify(유료) 대신 Playwright(무료)로 대체!

[사용법]
from services.web_scraper import scrape_shopee_reviews
reviews = await scrape_shopee_reviews("https://shopee.vn/product/12345")
"""


async def scrape_shopee_reviews(product_url: str, max_reviews: int = 50) -> list:
    """쇼피 제품 URL → 리뷰 텍스트 수집"""
    # TODO: Playwright 구현
    pass


async def scrape_lazada_reviews(product_url: str, max_reviews: int = 50) -> list:
    """라자다 제품 URL → 리뷰 텍스트 수집"""
    # TODO: Playwright 구현
    pass
