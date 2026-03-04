"""
★ 레시피 관리자 CRUD + slowapi rate limiting ★

POST /login       — 로그인 (분당 5회)
GET  /recipes     — 레시피 목록
POST /recipes     — 레시피 생성 (분당 10회)
PUT  /recipes/{id} — 수정
DELETE /recipes/{id} — 삭제
"""

import logging
import os
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.admin_auth import create_access_token, verify_admin

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

RECIPES_DIR = Path("data/recipes")

# 환경변수 기반 어드민 계정
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "threestar2024")


# ─── Pydantic 모델 ───
class AdminLogin(BaseModel):
    username: str
    password: str


class RecipeCreate(BaseModel):
    id: str = Field(..., pattern=r"^recipe_[a-z0-9_]+$")
    name: str
    name_vn: str = ""
    name_en: str = ""
    product_id: str = ""
    category: str = ""
    taste: str = ""
    difficulty: str = "보통"
    cook_time: str = "30분"
    body: str = ""


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    name_vn: Optional[str] = None
    name_en: Optional[str] = None
    product_id: Optional[str] = None
    category: Optional[str] = None
    taste: Optional[str] = None
    difficulty: Optional[str] = None
    cook_time: Optional[str] = None
    body: Optional[str] = None


# ─── 헬퍼: YAML frontmatter 파싱 ───
def _parse_recipe_file(filepath: Path) -> dict | None:
    """마크다운 파일에서 YAML frontmatter + body 파싱."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    if not text.startswith("---"):
        return None

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    meta = yaml.safe_load(parts[1])
    body = parts[2].strip()
    meta["body"] = body
    return meta


def _build_frontmatter(meta: dict) -> str:
    """dict → YAML frontmatter + body 마크다운 문자열."""
    body = meta.pop("body", "")

    # taste boolean 필드 생성
    taste_list = [t.strip() for t in meta.get("taste", "").split(",") if t.strip()]
    all_tastes = ["매운", "고소", "담백", "달콤", "새콤", "짭짤", "바삭", "감칠맛", "얼큰"]
    for t in all_tastes:
        meta[f"taste_{t}"] = t in taste_list

    # cook_time_minutes 추출
    cook_str = meta.get("cook_time", "30분")
    minutes = int("".join(c for c in cook_str if c.isdigit()) or "30")
    meta["cook_time_minutes"] = minutes

    # 기본값
    meta.setdefault("image_url", None)
    meta.setdefault("base_servings", 2)

    fm = yaml.dump(meta, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{fm}---\n{body}"


def _sync_chromadb_add(recipe_id: str, content: str, meta: dict):
    """ChromaDB에 레시피 추가/업데이트."""
    try:
        from services.recipe_search import get_collection

        collection = get_collection()
        # ChromaDB metadata: string/int/float/bool만 허용
        chroma_meta = {}
        for k, v in meta.items():
            if k == "body":
                continue
            if isinstance(v, (str, int, float, bool)):
                chroma_meta[k] = v
            elif v is None:
                chroma_meta[k] = ""
            else:
                chroma_meta[k] = str(v)
        chroma_meta["type"] = "recipe"

        collection.upsert(
            ids=[recipe_id],
            documents=[content[:2000]],
            metadatas=[chroma_meta],
        )
        logger.info(f"ChromaDB synced: {recipe_id}")
    except Exception as e:
        logger.error(f"ChromaDB sync failed for {recipe_id}: {e}")


def _sync_chromadb_delete(recipe_id: str):
    """ChromaDB에서 레시피 삭제."""
    try:
        from services.recipe_search import get_collection

        collection = get_collection()
        collection.delete(ids=[recipe_id])
        logger.info(f"ChromaDB deleted: {recipe_id}")
    except Exception as e:
        logger.error(f"ChromaDB delete failed for {recipe_id}: {e}")


def _invalidate_caches():
    """ingredient_search 캐시 무효화."""
    try:
        from services.ingredient_search import invalidate_cache

        invalidate_cache()
    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")


# ─── POST /login ───
@router.post("/login")
@limiter.limit("5/minute")
async def admin_login(request: Request, body: AdminLogin):
    if body.username != ADMIN_USERNAME or body.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token({"sub": body.username, "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}


# ─── GET /recipes ───
@router.get("/recipes")
async def list_recipes(_: dict = Depends(verify_admin)):
    recipes = []
    for f in sorted(RECIPES_DIR.glob("recipe_*.md")):
        meta = _parse_recipe_file(f)
        if meta:
            recipes.append({
                "id": meta.get("id", f.stem),
                "name": meta.get("name", ""),
                "name_vn": meta.get("name_vn", ""),
                "product_id": meta.get("product_id", ""),
                "category": meta.get("category", ""),
                "difficulty": meta.get("difficulty", ""),
                "cook_time": meta.get("cook_time", ""),
            })
    return {"recipes": recipes, "total": len(recipes)}


# ─── POST /recipes ───
@router.post("/recipes", status_code=201)
@limiter.limit("10/minute")
async def create_recipe(
    request: Request, recipe: RecipeCreate, _: dict = Depends(verify_admin)
):
    filepath = RECIPES_DIR / f"{recipe.id}.md"
    if filepath.exists():
        raise HTTPException(status_code=409, detail=f"Recipe '{recipe.id}' already exists")

    meta = {
        "id": recipe.id,
        "name": recipe.name,
        "name_vn": recipe.name_vn,
        "name_en": recipe.name_en,
        "product_id": recipe.product_id,
        "product_name": "",
        "category": recipe.category,
        "taste": recipe.taste,
        "difficulty": recipe.difficulty,
        "cook_time": recipe.cook_time,
        "body": recipe.body,
        "ingredients_main": "",
    }

    content = _build_frontmatter(meta)
    filepath.write_text(content, encoding="utf-8")

    _sync_chromadb_add(recipe.id, content, _parse_recipe_file(filepath) or {})
    _invalidate_caches()

    return {"message": "Recipe created", "id": recipe.id}


# ─── PUT /recipes/{recipe_id} ───
@router.put("/recipes/{recipe_id}")
async def update_recipe(
    recipe_id: str, update: RecipeUpdate, _: dict = Depends(verify_admin)
):
    filepath = RECIPES_DIR / f"{recipe_id}.md"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")

    meta = _parse_recipe_file(filepath)
    if not meta:
        raise HTTPException(status_code=500, detail="Failed to parse recipe file")

    # Optional 필드만 업데이트
    updates = update.model_dump(exclude_none=True)
    meta.update(updates)

    content = _build_frontmatter(meta)
    filepath.write_text(content, encoding="utf-8")

    _sync_chromadb_add(recipe_id, content, _parse_recipe_file(filepath) or {})
    _invalidate_caches()

    return {"message": "Recipe updated", "id": recipe_id}


# ─── DELETE /recipes/{recipe_id} ───
@router.delete("/recipes/{recipe_id}")
async def delete_recipe(recipe_id: str, _: dict = Depends(verify_admin)):
    filepath = RECIPES_DIR / f"{recipe_id}.md"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")

    filepath.unlink()
    _sync_chromadb_delete(recipe_id)
    _invalidate_caches()

    return {"message": "Recipe deleted", "id": recipe_id}
