"""
★ F파트 — 유통 지도 라우터 (market_map.py) ★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[담당 팀원] F파트
[수정 가능 범위] 이 파일 전체 + data/markets.json + templates/b2b/map.html의 {% block content %} 안

⚠️ 이 파트는 우선순위가 낮습니다. B~E파트 완성 후 진행하세요.

[이 파일이 해야 할 일]
  1. GET /api/map/generate 엔드포인트 구현
  2. data/markets.json 에서 마켓 데이터 로드
  3. city, types 필터 적용
  4. folium으로 지도 HTML 생성 → static/maps/ 에 저장
  5. 저장된 파일 URL 반환

[HTML(map.html)이 보내는 요청]
  fetch('/api/map/generate?city=hcmc&types=supermarket,convenience')

[반드시 반환해야 하는 형식]
  { "map_url": "/static/maps/vietnam_map_hcmc.html" }

[data/markets.json 형식]
  {
    "markets": [
      {
        "name": "Vinmart+ Quận 1",
        "type": "convenience",    ← supermarket / convenience / retail
        "city": "hcmc",          ← hcmc / hanoi / danang / all
        "lat": 10.7769,
        "lng": 106.7009,
        "address": "123 Lê Lợi, Quận 1"
      }
    ]
  }

[실시간 유동인구 — 구현 안 해도 됨]
  · 구글 Popular Times API 비공개 → 공식 방법 없음
  · 유동인구 기능 제거 권장

[AI 프롬프트 파일]
  prompts/PART_F_map.md 참고

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[병합 규칙]
  · main.py 수정 금지
  · CSS 클래스명: .f- prefix
  · static/maps/ 폴더는 코드에서 자동 생성 (mkdir)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

MAPS_DIR = Path("static/maps")
MARKETS_FILE = Path("data/markets.json")


@router.get("/map/generate", tags=["F-유통지도"])
async def generate_map(city: str = "all", types: str = "supermarket,convenience,retail"):
    """
    베트남 유통마켓 지도를 생성합니다.

    TODO (F파트 팀원):
    1. data/markets.json 로드
    2. city, types 필터 적용
    3. folium으로 지도 생성 → static/maps/ 저장
    4. 저장 경로 URL로 반환
    """

    # static/maps 폴더 자동 생성
    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    # 임시 응답 (F파트 팀원이 교체)
    return {
        "map_url": None,
        "message": "⚠️ API 연결 전입니다. routers/market_map.py를 완성해 주세요.",
        "filter": {"city": city, "types": types.split(",")}
    }
