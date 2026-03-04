"""
★ add_search_keywords.py — 레시피 .md 파일에 search_keywords 자동 추가 ★

각 레시피의 frontmatter에서 name, name_vn, name_en, category, taste, ingredients_main을 읽고,
GPT를 호출하여 검색 키워드 10~15개를 생성한 뒤 frontmatter에 search_keywords 필드를 추가/갱신.

실행: python scripts/add_search_keywords.py
"""

import asyncio
import glob
import os
import re
import sys

import yaml
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_md(filepath):
    text = open(filepath, "r", encoding="utf-8").read()
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text, text
    fm = yaml.safe_load(m.group(1)) or {}
    body = FRONTMATTER_RE.sub("", text)
    return fm, body, text


async def generate_keywords(fm):
    from services.recipe_ai import call_gpt_mini

    name = fm.get("name", "")
    name_vn = fm.get("name_vn", "")
    name_en = fm.get("name_en", "")
    category = fm.get("category", "")
    taste = fm.get("taste", "")
    ingredients = fm.get("ingredients_main", "")

    prompt = f"""다음 레시피의 검색 키워드를 한국어, 베트남어, 영어로 10~15개 생성하세요.
키워드는 쉼표로 구분하여 한 줄로 반환하세요. 다른 텍스트 없이 키워드만 반환하세요.

레시피 정보:
- 한국어 이름: {name}
- 베트남어 이름: {name_vn}
- 영어 이름: {name_en}
- 카테고리: {category}
- 맛: {taste}
- 주요 재료: {ingredients}

키워드:"""

    result = await call_gpt_mini(prompt, max_tokens=200, temperature=0.3)
    return result.strip()


async def process_file(filepath):
    fm, body, original_text = parse_md(filepath)
    if not fm:
        print(f"  SKIP (no frontmatter): {filepath}")
        return False

    keywords = await generate_keywords(fm)
    if not keywords:
        print(f"  SKIP (no keywords generated): {filepath}")
        return False

    # frontmatter에 search_keywords 추가/갱신
    fm["search_keywords"] = keywords

    # YAML 덤프 → 파일 재작성
    yaml_str = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    new_text = f"---\n{yaml_str}---\n{body}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"  OK: {os.path.basename(filepath)} → {keywords[:60]}...")
    return True


async def main():
    files = sorted(glob.glob("data/recipes/*.md"))
    print(f"=== search_keywords 생성 시작 ({len(files)}개 파일) ===\n")

    success = 0
    for i, filepath in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {os.path.basename(filepath)}")
        try:
            if await process_file(filepath):
                success += 1
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n=== 완료: {success}/{len(files)}개 파일 처리됨 ===")


if __name__ == "__main__":
    asyncio.run(main())
