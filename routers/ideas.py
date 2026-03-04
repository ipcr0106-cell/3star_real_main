"""
★ 인트라넷 라우터 — routers/intranet.py ★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[엔드포인트] (main.py에서 prefix="/api/intranet" 로 연결됨)
  GET    /api/intranet/ideas          → 아이디어 목록 조회 (파트/카테고리 필터)
  POST   /api/intranet/ideas          → 아이디어 등록
  PUT    /api/intranet/ideas/{id}     → 좋아요 토글
  DELETE /api/intranet/ideas/{id}     → 삭제 (작성자 본인만)
  GET    /api/intranet/ideas/meta     → 파트·카테고리 목록 반환
  GET    /api/intranet/documents      → 생성된 문서 파일 목록 반환 (Documents 드롭다운)
  GET    /api/intranet/download/competitor_history → competitor_history.xlsx 다운로드

[저장] data/ideas.json (서버 자동 생성, 최대 200건 보관)
[동시접속] 10명 이내 → JSON 파일 방식으로 충분히 안정적
"""

import json
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter()

IDEAS_PATH = Path("data/ideas.json")
MAX_IDEAS  = 200

# ── 파트 구분 (라벨 변경)
PARTS: dict[str, str] = {
    "A":  "B2C 마케팅",
    "B":  "레시피 챗봇",
    "C":  "뉴스 트렌드 분석",
    "D":  "리뷰 키워드 분석",
    "E":  "SNS 콘텐츠 제작",
    "F":  "유통 마켓",
    "PM": "기획/전략",
}

CATEGORIES: list[str] = ["기능 개선", "UI/UX", "데이터", "마케팅", "운영", "기타"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 아이디어 헬퍼
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load() -> list[dict]:
    try:
        if IDEAS_PATH.exists():
            return json.loads(IDEAS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[아이디어 읽기 실패] {e}")
    return []


def _save(ideas: list[dict]) -> None:
    if len(ideas) > MAX_IDEAS:
        ideas = ideas[-MAX_IDEAS:]
    IDEAS_PATH.parent.mkdir(exist_ok=True)
    IDEAS_PATH.write_text(json.dumps(ideas, ensure_ascii=False, indent=2), encoding="utf-8")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 스키마
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class IdeaCreate(BaseModel):
    author:   str
    part:     str
    category: str
    title:    str
    content:  str
    url:      Optional[str] = None  # ← 참고 URL (선택사항)


class LikeToggle(BaseModel):
    author: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 아이디어 엔드포인트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/ideas/meta")
async def get_meta():
    return {
        "parts":      [{"key": k, "label": v} for k, v in PARTS.items()],
        "categories": CATEGORIES,
    }


@router.get("/ideas")
async def list_ideas(
    part:     Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page:     int           = Query(1, ge=1),
    per_page: int           = Query(20, ge=1, le=50),
):
    ideas = _load()
    if part:
        ideas = [i for i in ideas if i.get("part") == part]
    if category:
        ideas = [i for i in ideas if i.get("category") == category]
    ideas.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(ideas)
    start = (page - 1) * per_page
    return {"total": total, "page": page, "per_page": per_page, "ideas": ideas[start: start + per_page]}


@router.post("/ideas", status_code=201)
async def create_idea(body: IdeaCreate):
    if body.part not in PARTS:
        raise HTTPException(400, detail=f"유효하지 않은 파트: {body.part}")
    if not body.author.strip():
        raise HTTPException(400, detail="작성자 이름을 입력해주세요.")
    if not body.title.strip():
        raise HTTPException(400, detail="제목을 입력해주세요.")
    if len(body.content) > 500:
        raise HTTPException(400, detail="내용은 500자 이내로 입력해주세요.")

    idea = {
        "id":         str(uuid.uuid4())[:8],
        "author":     body.author.strip(),
        "part":       body.part,
        "part_label": PARTS.get(body.part, body.part),
        "category":   body.category,
        "title":      body.title.strip(),
        "content":    body.content.strip(),
        "url":        body.url.strip() if body.url else None,  # ← 참고 URL 저장
        "likes":      [],
        "created_at": datetime.now().strftime("%Y.%m.%d %H:%M"),
    }
    ideas = _load()
    ideas.append(idea)
    _save(ideas)
    return {"success": True, "idea": idea}


@router.put("/ideas/{idea_id}")
async def toggle_like(idea_id: str, body: LikeToggle):
    ideas  = _load()
    target = next((i for i in ideas if i["id"] == idea_id), None)
    if not target:
        raise HTTPException(404, detail="아이디어를 찾을 수 없습니다.")
    likes = target.setdefault("likes", [])
    name  = body.author.strip()
    if name in likes:
        likes.remove(name)
        action = "unlike"
    else:
        likes.append(name)
        action = "like"
    _save(ideas)
    return {"success": True, "action": action, "like_count": len(likes)}


@router.delete("/ideas/{idea_id}")
async def delete_idea(idea_id: str, author: str = Query(...)):
    ideas  = _load()
    target = next((i for i in ideas if i["id"] == idea_id), None)
    if not target:
        raise HTTPException(404, detail="아이디어를 찾을 수 없습니다.")
    if target.get("author") != author.strip():
        raise HTTPException(403, detail="본인이 작성한 아이디어만 삭제할 수 있습니다.")
    ideas = [i for i in ideas if i["id"] != idea_id]
    _save(ideas)
    return {"success": True, "deleted_id": idea_id}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Documents 엔드포인트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/documents")
async def list_documents():
    files = []

    pdf_dir = Path("static/pdfs")
    if pdf_dir.exists():
        pdfs = sorted(pdf_dir.glob("*.pdf"), key=os.path.getmtime, reverse=True)
        for f in pdfs:
            stat   = f.stat()
            size   = f"{stat.st_size // 1024}KB" if stat.st_size >= 1024 else f"{stat.st_size}B"
            mtime  = datetime.fromtimestamp(stat.st_mtime).strftime("%Y.%m.%d")
            files.append({
                "name": f.name,
                "type": "pdf",
                "url":  f"/static/pdfs/{f.name}",
                "size": size,
                "date": mtime,
            })

    xlsx_path = Path("data/competitor_history.xlsx")
    if xlsx_path.exists():
        stat  = xlsx_path.stat()
        size  = f"{stat.st_size // 1024}KB" if stat.st_size >= 1024 else f"{stat.st_size}B"
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y.%m.%d")
        files.append({
            "name": "competitor_history.xlsx",
            "type": "xlsx",
            "url":  "/api/intranet/download/competitor_history",
            "size": size,
            "date": mtime,
        })

    return {"files": files}


@router.get("/download/competitor_history")
async def download_competitor_history():
    path = Path("data/competitor_history.xlsx")
    if not path.exists():
        raise HTTPException(404, detail="파일이 없습니다.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="competitor_history.xlsx",
    )
