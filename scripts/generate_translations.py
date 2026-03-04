#!/usr/bin/env python3
"""
72개 레시피 .md 파일을 읽어서 베트남어/영어 번역 JSON을 생성.
GPT-4o-mini를 사용하여 1회성으로 실행.
결과: data/translations.json
"""
import os, json, glob, re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RECIPE_DIR = "data/recipes"
OUTPUT_FILE = "data/translations.json"


def parse_recipe_md(filepath: str) -> dict:
    """레시피 .md 파일에서 id, 재료, 조리법, 팁 추출."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # frontmatter에서 id 추출
    id_match = re.search(r"^id:\s*(.+)$", content, re.MULTILINE)
    recipe_id = id_match.group(1).strip() if id_match else os.path.basename(filepath).replace(".md", "")

    name_match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
    name = name_match.group(1).strip() if name_match else ""

    name_vn_match = re.search(r"^name_vn:\s*(.+)$", content, re.MULTILINE)
    name_vn = name_vn_match.group(1).strip() if name_vn_match else ""

    name_en_match = re.search(r"^name_en:\s*(.+)$", content, re.MULTILINE)
    name_en = name_en_match.group(1).strip() if name_en_match else ""

    # 재료 추출 (## 재료 섹션)
    ingredients = []
    ing_match = re.search(r"## 재료.*?\n((?:- .+\n)+)", content)
    if ing_match:
        ingredients = [line.strip("- ").strip() for line in ing_match.group(1).strip().split("\n") if line.strip().startswith("-")]

    # 조리법 추출
    steps = []
    step_match = re.search(r"## 조리법\n((?:\d+\..+\n)+)", content)
    if step_match:
        steps = [re.sub(r"^\d+\.\s*", "", line).strip() for line in step_match.group(1).strip().split("\n") if line.strip()]

    # 팁 추출
    tips = []
    tip_match = re.search(r"## 팁\n((?:- .+\n?)+)", content)
    if tip_match:
        tips = [line.strip("- ").strip() for line in tip_match.group(1).strip().split("\n") if line.strip().startswith("-")]

    return {
        "id": recipe_id,
        "name": name,
        "name_vn": name_vn,
        "name_en": name_en,
        "ingredients": ingredients,
        "steps": steps,
        "tips": tips,
    }


def translate_recipe(recipe: dict, target_lang: str) -> dict:
    """GPT-4o-mini로 레시피의 재료/조리법/팁을 번역."""
    lang_name = "Vietnamese" if target_lang == "vi" else "English"

    prompt = f"""Translate the following Korean recipe data to {lang_name}.

RULES:
- Translate ingredient names, quantities, and cooking instructions naturally
- Keep measurement units appropriate for the target language
- Return ONLY valid JSON, no markdown backticks
- NEVER return empty strings. Every item must have actual translated content.

Input:
{{
  "ingredients": {json.dumps(recipe['ingredients'], ensure_ascii=False)},
  "steps": {json.dumps(recipe['steps'], ensure_ascii=False)},
  "tips": {json.dumps(recipe['tips'], ensure_ascii=False)}
}}

Output format (JSON only):
{{
  "ingredients": ["translated ingredient 1", ...],
  "steps": ["translated step 1", ...],
  "tips": ["translated tip 1", ...]
}}"""

    for attempt in range(2):  # 최대 2회 시도
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)

            # ★ 빈값 검증
            has_empty = False
            for field in ["ingredients", "steps", "tips"]:
                items = result.get(field, [])
                empty_count = sum(1 for item in items if not str(item).strip())
                if items and empty_count > len(items) * 0.3:
                    has_empty = True
                    print(f"  ⚠️ {recipe['id']} ({target_lang}) {field}: {empty_count}/{len(items)} empty")

            if not has_empty:
                return result
            elif attempt == 0:
                print(f"  🔄 Retrying {recipe['id']} ({target_lang})...")
                continue
            else:
                return result  # 재시도 후에도 빈값이면 그대로 반환

        except Exception as e:
            print(f"  ❌ Translation error for {recipe['id']} ({target_lang}): {e}")
            # 실패 시 원본 한국어 데이터 반환 (빈값보다 나음)
            return {"ingredients": recipe["ingredients"], "steps": recipe["steps"], "tips": recipe["tips"]}

    return {"ingredients": recipe["ingredients"], "steps": recipe["steps"], "tips": recipe["tips"]}


def main():
    # 모든 레시피 파일 읽기
    recipe_files = sorted(glob.glob(f"{RECIPE_DIR}/*.md"))
    print(f"Found {len(recipe_files)} recipe files")

    translations = {}

    for i, filepath in enumerate(recipe_files):
        recipe = parse_recipe_md(filepath)
        recipe_id = recipe["id"]

        if not recipe["ingredients"] and not recipe["steps"]:
            print(f"  skip {i+1}/{len(recipe_files)} {recipe_id} — no ingredients/steps")
            continue

        print(f"  {i+1}/{len(recipe_files)} {recipe_id}...", end=" ", flush=True)

        # 베트남어 번역
        vi_result = translate_recipe(recipe, "vi")

        # 영어 번역
        en_result = translate_recipe(recipe, "en")

        translations[recipe_id] = {
            "name": recipe["name"],
            "name_vn": recipe["name_vn"],
            "name_en": recipe["name_en"],
            "ko": {
                "ingredients": recipe["ingredients"],
                "steps": recipe["steps"],
                "tips": recipe["tips"],
            },
            "vi": {
                "ingredients": vi_result.get("ingredients", []),
                "steps": vi_result.get("steps", []),
                "tips": vi_result.get("tips", []),
            },
            "en": {
                "ingredients": en_result.get("ingredients", []),
                "steps": en_result.get("steps", []),
                "tips": en_result.get("tips", []),
            },
        }
        print("done")

    # JSON 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(translations)} recipes to {OUTPUT_FILE}")
    print(f"File size: {os.path.getsize(OUTPUT_FILE) / 1024:.1f} KB")

    # 품질 보고
    empty_fields = []
    for rid, data in translations.items():
        for lang in ["vi", "en"]:
            lang_data = data.get(lang, {})
            for field in ["ingredients", "steps"]:
                items = lang_data.get(field, [])
                if not items or all(not str(item).strip() for item in items):
                    empty_fields.append(f"{rid}/{lang}/{field}")

    print(f"\n📊 품질 보고:")
    print(f"   총 레시피: {len(translations)}")
    print(f"   완전 빈값 필드: {len(empty_fields)}")
    if empty_fields:
        print(f"   ⚠️ 빈값 목록:")
        for ef in empty_fields[:10]:
            print(f"      {ef}")


if __name__ == "__main__":
    main()
