# F파트 — 유통마켓 지도 AI 프롬프트
> 이 파일의 내용을 MASTER_PROMPT.md 아래에 붙여넣어서 AI에게 전달하세요.  
> ⚠️ 이 파트는 우선순위가 낮습니다. B~E파트가 완성된 후에 진행하세요.

---

# [프롬프트]
## 마케팅 직원을 위한 유통마켓 지도 
>베트남의 오프라인 대형마트, 편의점, 소매점 위치를 표시해주는 지도를 띄우고 싶어
>google map 지도도 사용 가능. 
>대형마트, 편의점, 소매점 등 유통 채널을 체크박스로 선택해서 보여주게 할 수 있어
>html로 만들거야
```
[F파트 — 베트남 유통마켓 지도 작업]

내가 구현해야 할 파일:
- routers/market_map.py     (API 로직)
- templates/b2b/map.html    (화면 뼈대 있음, {% block content %} 안만 수정 가능)
- data/markets.json         (마켓 좌표 데이터)

[HTML이 기대하는 API 명세]
GET /api/map/generate?city=hcmc&types=supermarket,convenience
출력: { "map_url": "/static/maps/vietnam_map.html" }

[구현 방법]
1. data/markets.json 에서 마켓 좌표 데이터 로드
2. city, types 필터 적용
3. folium으로 지도 생성 → static/maps/ 폴더에 HTML 파일로 저장
4. 저장된 파일의 URL을 반환

[data/markets.json 형식]
{
  "markets": [
    {
      "name": "Vinmart+ Quận 1",
      "type": "convenience",
      "city": "hcmc",
      "lat": 10.7769,
      "lng": 106.7009,
      "address": "123 Lê Lợi, Quận 1"
    }
  ]
}

[Folium 지도 생성 코드 힌트]
import folium
m = folium.Map(location=[10.8231, 106.6297], zoom_start=12)  # 호치민 중심
folium.Marker([lat, lng], popup=name, icon=folium.Icon(color='red')).add_to(m)
map_path = "static/maps/vietnam_map.html"
m.save(map_path)

[실시간 유동인구 — 현실적 대안]
- 구글 Popular Times API는 비공개라 공식 방법 없음
- 대안 1: 고정 데이터로 "혼잡 예상 시간대" 표기 (가장 현실적)
- 대안 2: populartimes 비공식 라이브러리 (불안정, 사용 비권장)
- → 유동인구는 일단 제외하고 위치 지도만 완성하는 것을 권장

[화면 수정 시 규칙]
- CSS 클래스명에 .f- prefix 사용
- {% extends "base_b2b.html" %} 줄 절대 삭제 금지

이제 routers/market_map.py 를 완성해줘.
static/maps/ 폴더가 없으면 자동 생성하도록 해줘.
```

---

## 📁 F파트 담당 파일

| 파일 | 상태 | 할 일 |
|------|------|--------|
| `routers/market_map.py` | 뼈대만 있음 | **핵심 작업 위치** |
| `data/markets.json` | 샘플 데이터 있음 | 실제 마켓 데이터 추가 |
| `templates/b2b/map.html` | 뼈대 있음 | `{% block content %}` 안만 수정 가능 |
| `static/maps/` | 없음 | 자동 생성 (코드에서 mkdir) |

## ⚠️ F파트 주의사항
- `static/maps/` 폴더를 Git에 올리지 않아도 됨 (런타임에 생성)
- Folium이 생성한 HTML은 용량이 크므로 캐싱 필수
- 유동인구 기능은 구현하지 않아도 OK (우선순위 낮음)
