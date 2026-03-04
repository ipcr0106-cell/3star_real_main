"""
★ 직원 포탈 인증 라우터 — auth.py ★

[역할]
직원 코드 입력 → 세션에 name/initial/role 저장 → /portal 접근 허용
직원 코드는 data/admins.json 에서 관리

[사용하는 엔드포인트]
GET  /portal/login       → 로그인 페이지
POST /portal/login       → 코드 검증 + 세션 저장
GET  /portal/logout      → 세션 삭제
"""

import json
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ADMINS_FILE = Path("data/admins.json")


def load_admins() -> list[dict]:
    """data/admins.json에서 전체 직원 목록 반환"""
    if not ADMINS_FILE.exists():
        return []
    data = json.loads(ADMINS_FILE.read_text(encoding="utf-8"))
    return data.get("codes", [])


def find_admin(code: str) -> dict | None:
    """코드로 직원 정보 찾기 (대소문자 무시)"""
    for admin in load_admins():
        if admin["code"].upper() == code.strip().upper():
            return admin
    return None


def is_logged_in(request: Request) -> bool:
    return request.session.get("portal_auth") == "authenticated"


# ─── 로그인 페이지 ───
@router.get("/portal/login", response_class=HTMLResponse, tags=["인증"])
async def login_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/portal", status_code=302)
    return templates.TemplateResponse("b2b/login.html", {
        "request": request,
        "error": None
    })


# ─── 로그인 처리 ───
@router.post("/portal/login", response_class=HTMLResponse, tags=["인증"])
async def login_submit(request: Request, code: str = Form(...)):
    matched = find_admin(code)

    if matched:
        # 세션에 사용자 정보 저장
        request.session["portal_auth"]  = "authenticated"
        request.session["user_name"]    = matched["name"]
        request.session["user_initial"] = matched.get("initial", matched["name"][:2])
        request.session["user_role"]    = matched.get("role", "staff")
        return RedirectResponse("/portal", status_code=302)
    else:
        return templates.TemplateResponse("b2b/login.html", {
            "request": request,
            "error": "잘못된 직원 코드입니다. 다시 확인해 주세요."
        })


# ─── 로그아웃 ───
@router.get("/portal/logout", tags=["인증"])
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)