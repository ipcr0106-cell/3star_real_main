"""
레시피 메타데이터 강화 — 1회성 마이그레이션 스크립트
- taste 불리언 9종 추가
- cook_time_minutes 추가
- ingredients_main + base_servings 추가
"""

import glob
import re
import yaml

TASTE_LIST = ["매운", "고소", "담백", "달콤", "새콤", "짭짤", "바삭", "감칠맛", "얼큰"]

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_md(filepath):
    """frontmatter(dict)와 body(str)를 분리하여 반환."""
    text = open(filepath, "r", encoding="utf-8").read()
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    fm_raw = m.group(1)
    body = text[m.end():]
    fm = yaml.safe_load(fm_raw)
    return fm, body


def add_taste_booleans(fm):
    """taste 문자열을 파싱하여 9개 불리언 필드 추가."""
    taste_str = fm.get("taste", "")
    tastes = [t.strip() for t in str(taste_str).split(",") if t.strip()]
    for t in TASTE_LIST:
        fm[f"taste_{t}"] = t in tastes


def add_cook_time_minutes(fm):
    """cook_time에서 숫자 추출하여 cook_time_minutes 추가."""
    ct = str(fm.get("cook_time", ""))
    nums = re.findall(r"\d+", ct)
    fm["cook_time_minutes"] = int(nums[0]) if nums else 30


def extract_ingredient_name(line):
    """재료 줄에서 재료명만 추출."""
    # "- 소고기 200g" -> "소고기"
    # "- 쌀국수(Bánh phở) 200g" -> "쌀국수"
    # "- Da-Mi Food Cheongyang Mayo Sauce × 3큰술" -> skip (제품)
    line = line.strip().lstrip("- ").strip()
    if not line:
        return None
    # 제품 라인 스킵
    if "Da-Mi" in line or "da-mi" in line.lower():
        return None
    # 괄호 제거
    name = re.sub(r"\([^)]*\)", "", line).strip()
    # 수량/단위 패턴 제거: 숫자, g, ml, L, 큰술, 작은술, 개, 장, 대, 줌, etc.
    name = re.sub(
        r"\s*[\d½⅓¼/.,]+\s*"
        r"(g|kg|ml|L|l|큰술|작은술|스푼|개|장|대|줌|쪽|봉|조각|컵|적당량|약간|한\s*줌|cm)?"
        r"[\s]*.*$",
        "",
        name,
    ).strip()
    # × 이후 제거
    name = re.split(r"\s*[×x]\s*", name)[0].strip()
    # 남은 게 너무 짧거나 없으면 스킵
    if len(name) < 1:
        return None
    return name


def add_ingredients_and_servings(fm, body):
    """본문에서 재료 섹션을 파싱하여 ingredients_main, base_servings 추가."""
    # base_servings 추출
    servings_match = re.search(r"##\s*재료\s*\((\d+)인분\)", body)
    fm["base_servings"] = int(servings_match.group(1)) if servings_match else 2

    # 재료 섹션 추출
    ingredients_section = re.search(
        r"##\s*재료[^\n]*\n(.*?)(?=\n##|\Z)", body, re.DOTALL
    )
    if not ingredients_section:
        fm["ingredients_main"] = ""
        return

    lines = ingredients_section.group(1).strip().split("\n")
    ingredients = []
    for line in lines:
        line = line.strip()
        if not line.startswith("-"):
            continue
        name = extract_ingredient_name(line)
        if name and len(ingredients) < 6:
            ingredients.append(name)

    fm["ingredients_main"] = ",".join(ingredients)


def rebuild_md(fm, body):
    """frontmatter와 body를 합쳐서 .md 텍스트로 재구성."""
    fm_str = yaml.dump(
        fm, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    # yaml.dump 끝의 trailing newline 제거 후 다시 추가
    fm_str = fm_str.rstrip("\n")
    return f"---\n{fm_str}\n---\n{body}"


def main():
    files = sorted(glob.glob("data/recipes/*.md"))
    updated = 0
    skipped = 0

    for filepath in files:
        fm, body = parse_md(filepath)
        if fm is None:
            print(f"SKIP (no frontmatter): {filepath}")
            skipped += 1
            continue

        # 멱등성: 이미 처리된 파일 스킵
        if "taste_매운" in fm:
            print(f"SKIP (already processed): {filepath}")
            skipped += 1
            continue

        add_taste_booleans(fm)
        add_cook_time_minutes(fm)
        add_ingredients_and_servings(fm, body)

        result = rebuild_md(fm, body)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(result)

        updated += 1

    print(f"\nDone: {updated} updated, {skipped} skipped, {len(files)} total")


if __name__ == "__main__":
    main()
