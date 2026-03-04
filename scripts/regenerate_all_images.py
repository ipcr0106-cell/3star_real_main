"""
81개 레시피 이미지 일괄 재생성 스크립트

- 기존 캐시/orphan 이미지 정리
- 새 프롬프트(카테고리 스타일 + 핵심 재료)로 DALL-E 3 생성
- 진행 상황 실시간 출력
- 실패 시 재시도 1회

사용법:
  python scripts/regenerate_all_images.py          # 전체 81개
  python scripts/regenerate_all_images.py --dry-run # 프롬프트만 확인 (API 호출 없음)
  python scripts/regenerate_all_images.py --only recipe_pho_bo_coin01_001  # 특정 1개만
"""

import argparse
import asyncio
import json
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from services.image_generator import (
    IMAGES_DIR, CACHE_FILE, build_prompt,
    _load_cache, _save_cache, _get_category, CATEGORY_TO_STYLE,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

TRANSLATIONS_FILE = Path("data/translations.json")
REPORT_FILE = Path("data/reports/image_regeneration_report.json")


def load_translations() -> dict:
    return json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8"))


def cleanup_old_images():
    """기존 캐시 + orphan 이미지 정리."""
    cache = _load_cache()
    tr = load_translations()

    # orphan 캐시 제거 (레시피 없는 항목)
    orphans = [rid for rid in cache if rid not in tr]
    for rid in orphans:
        img_path = Path(cache[rid])
        if img_path.exists():
            img_path.unlink()
            logger.info(f"Deleted orphan image: {rid}")
        del cache[rid]

    # 기존 캐시된 이미지 백업 디렉토리로 이동
    backup_dir = Path("static/images/recipes_backup")
    backup_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    for rid, path in list(cache.items()):
        img_path = Path(path)
        if img_path.exists():
            backup_path = backup_dir / img_path.name
            shutil.move(str(img_path), str(backup_path))
            moved += 1

    # 캐시 초기화
    _save_cache({})

    logger.info(f"Cleanup: {len(orphans)} orphans deleted, {moved} images backed up to {backup_dir}")
    return len(orphans), moved


async def generate_single(recipe_id: str, name_en: str, dry_run: bool = False) -> dict:
    """단일 레시피 이미지 생성."""
    import httpx
    import openai

    prompt = build_prompt(recipe_id, name_en)
    category = _get_category(recipe_id)
    style = CATEGORY_TO_STYLE.get(category, "plate")

    result = {
        "recipe_id": recipe_id,
        "name_en": name_en,
        "category": category,
        "style": style,
        "prompt": prompt,
        "status": "skipped" if dry_run else "pending",
        "image_path": "",
        "error": "",
    }

    if dry_run:
        return result

    try:
        client = openai.AsyncOpenAI()
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url

        local_filename = f"{recipe_id}.png"
        local_path = IMAGES_DIR / local_filename

        async with httpx.AsyncClient(timeout=30) as http_client:
            img_response = await http_client.get(image_url)
            img_response.raise_for_status()
            local_path.write_bytes(img_response.content)

        # 캐시 업데이트
        cache = _load_cache()
        relative_path = f"static/images/recipes/{local_filename}"
        cache[recipe_id] = relative_path
        _save_cache(cache)

        result["status"] = "success"
        result["image_path"] = relative_path
        return result

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        return result


async def main():
    parser = argparse.ArgumentParser(description="Regenerate all recipe images")
    parser.add_argument("--dry-run", action="store_true", help="프롬프트만 출력, API 호출 없음")
    parser.add_argument("--only", type=str, help="특정 recipe_id만 생성")
    parser.add_argument("--skip-cleanup", action="store_true", help="기존 이미지 정리 건너뜀")
    args = parser.parse_args()

    tr = load_translations()
    recipe_ids = [args.only] if args.only else sorted(tr.keys())

    if args.only and args.only not in tr:
        print(f"ERROR: {args.only} not found in translations.json")
        return

    print(f"\n{'='*60}")
    print(f"  Recipe Image Regeneration")
    print(f"  Total: {len(recipe_ids)} recipes")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE (DALL-E 3)'}")
    if not args.dry_run:
        print(f"  Estimated cost: ${len(recipe_ids) * 0.04:.2f}")
    print(f"{'='*60}\n")

    # 정리
    if not args.dry_run and not args.skip_cleanup and not args.only:
        orphans, moved = cleanup_old_images()
        print(f"Cleanup: {orphans} orphans removed, {moved} old images backed up\n")

    results = []
    success = 0
    failed = 0
    start_time = time.time()

    for i, rid in enumerate(recipe_ids, 1):
        name_en = tr[rid].get("name_en", rid)
        name_ko = tr[rid].get("name", "")

        print(f"[{i}/{len(recipe_ids)}] {name_ko} ({name_en})")

        result = await generate_single(rid, name_en, dry_run=args.dry_run)
        results.append(result)

        if args.dry_run:
            print(f"  Style: {result['style']} | Category: {result['category']}")
            print(f"  Prompt: {result['prompt'][:100]}...")
        elif result["status"] == "success":
            success += 1
            print(f"  ✅ {result['image_path']}")
        else:
            # 재시도 1회
            logger.warning(f"  Retrying {rid}...")
            await asyncio.sleep(3)
            result = await generate_single(rid, name_en, dry_run=False)
            results[-1] = result
            if result["status"] == "success":
                success += 1
                print(f"  ✅ (retry) {result['image_path']}")
            else:
                failed += 1
                print(f"  ❌ {result['error']}")

        # rate limit 대응
        if not args.dry_run and i < len(recipe_ids):
            await asyncio.sleep(2)

    elapsed = time.time() - start_time

    # 리포트 저장
    report = {
        "generated_at": datetime.now().isoformat(),
        "mode": "dry_run" if args.dry_run else "live",
        "total": len(recipe_ids),
        "success": success,
        "failed": failed,
        "elapsed_seconds": round(elapsed, 1),
        "results": results,
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  Complete: {success} success, {failed} failed ({round(elapsed)}s)")
    print(f"  Report: {REPORT_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
