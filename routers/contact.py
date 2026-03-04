"""
★ Contact Us 라우터 — contact.py ★

[현재 구현 범위]
- 문의 폼 UI 표시
- 폼 제출 시 성공 메시지 표시 (실제 메일 발송 미구현)

[나중에 메일 연동할 때]
1. Gmail SMTP: smtplib 사용 (무료)
2. SendGrid: pip install sendgrid (무료 티어 100통/일)
→ .env에 GMAIL_USER, GMAIL_PASSWORD 또는 SENDGRID_API_KEY 추가

[엔드포인트]
GET  /contact   → 문의 폼 페이지
POST /contact   → 폼 제출 처리 (현재: 성공 메시지만)
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/contact", response_class=HTMLResponse, tags=["A-B2C자사몰"])
async def contact_page(request: Request):
    """문의 페이지"""
    return templates.TemplateResponse("b2c/contact.html", {
        "request": request,
        "success": False,
        "error": None
    })


@router.post("/contact", response_class=HTMLResponse, tags=["A-B2C자사몰"])
async def contact_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...)
):
    """
    문의 폼 제출 처리
    TODO: 실제 메일 발송 구현 시 아래 주석 해제
    """
    # ── 나중에 Gmail SMTP 사용할 때 ──────────────────────────
    # import smtplib
    # from email.mime.text import MIMEText
    # from email.mime.multipart import MIMEMultipart
    # import os
    #
    # msg = MIMEMultipart()
    # msg['From'] = os.getenv("GMAIL_USER")
    # msg['To'] = os.getenv("CONTACT_RECEIVER_EMAIL")  # 받는 메일
    # msg['Subject'] = f"[Three Star 문의] {subject} — {name}"
    # body = f"보낸 사람: {name} <{email}>\n\n{message}"
    # msg.attach(MIMEText(body, 'plain'))
    #
    # with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
    #     server.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_PASSWORD"))
    #     server.send_message(msg)
    # ──────────────────────────────────────────────────────────

    print(f"[문의 접수] {name} <{email}> | 제목: {subject}")
    print(f"내용: {message}")

    return templates.TemplateResponse("b2c/contact.html", {
        "request": request,
        "success": True,
        "error": None
    })
