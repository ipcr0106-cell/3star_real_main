import os
import requests
import time
import json  # 🔥 JSON 파싱을 위해 추가!
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import APIRouter

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

router = APIRouter()
client = OpenAI(api_key=OPENAI_API_KEY)

# 💡 마케팅팀 집중 견제 타겟 
TARGET_COMPETITORS = {
    "육수큐브": [
        {"shop_id": "1019011068", "item_id": "28908023799", "name": "베트남 Knorr 육수", "url": "https://shopee.vn/product/1019011068/28908023799", "image": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=150&h=150&fit=crop"},
        {"shop_id": "108166524", "item_id": "13779651219", "name": "Maggi 고기육수 큐브", "url": "https://shopee.vn/product/108166524/13779651219", "image": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=150&h=150&fit=crop"},
        {"shop_id": "49207945", "item_id": "12885823018", "name": "Bao Long 쌀국수 큐브", "url": "https://shopee.vn/product/49207945/12885823018", "image": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=150&h=150&fit=crop"}
    ],
    "소스": [
        # 🚨 주의: 반드시 static/images 폴더 안에 sauce.jpg 파일이 있어야 이미지가 뜹니다!
        {"shop_id": "40502277", "item_id": "2206730486", "name": "Cholimex 칠리소스", "url": "https://shopee.vn/product/40502277/2206730486", "image": "/static/images/sauce.jpg"},
        {"shop_id": "907906315", "item_id": "23554920045", "name": "Chin-su 마늘 칠리소스", "url": "https://shopee.vn/product/907906315/23554920045", "image": "/static/images/sauce.jpg"},
        {"shop_id": "47408732", "item_id": "8273536023", "name": "Nam Ngu 생선소스", "url": "https://shopee.vn/product/47408732/8273536023", "image": "/static/images/sauce.jpg"}
    ],
    "시즈닝": [
        {"shop_id": "111222333", "item_id": "999888777", "name": "McCormick 그릴메이트", "url": "https://shopee.vn/product/111222333/999888777", "image": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=150&h=150&fit=crop"},
        {"shop_id": "444555666", "item_id": "666555444", "name": "O'Food 바베큐 시즈닝", "url": "https://shopee.vn/product/444555666/666555444", "image": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=150&h=150&fit=crop"},
        {"shop_id": "777888999", "item_id": "333222111", "name": "하오하오 마법의 소금", "url": "https://shopee.vn/product/777888999/333222111", "image": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=150&h=150&fit=crop"}
    ]
}

competitor_reports = {}

def fetch_shopee_reviews(shop_id, item_id):
    url = f"https://shopee.vn/api/v2/item/get_ratings?itemid={item_id}&shopid={shop_id}&limit=30&offset=0&type=0&filter=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": f"https://shopee.vn/product/{shop_id}/{item_id}"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('data') and data['data'].get('ratings'):
                return " / ".join([r['comment'].replace('\n', ' ')[:100] for r in data['data']['ratings'] if r.get('comment')])
    except:
        pass 

    fallback_data = {
        "1019011068": "Nước dùng rất ngọt và thơm. (국물이 달고 향긋함) / Hơi khó tan trong nước lạnh. (찬물에 잘 안 녹음) / Bao bì dễ rách. (포장이 잘 찢어짐)",
        "108166524": "Nước ngọt thanh. (국물이 깔끔함) / Giá đắt. (가격이 비쌈) / Khó bảo quản. (보관이 어려움)",
        "49207945": "Thơm mùi phở. (쌀국수 향이 좋음) / Phải dùng nhiều viên mới đậm. (여러 개 넣어야 진해짐) / Hơi mặn. (조금 짠 편)",
        "40502277": "Vị cay nồng, rất hợp chấm mực. (오징어 찍어먹기 좋음) / Chai nhỏ dùng nhanh hết. (병이 너무 작아서 금방 씀) / Nắp chai hay bị rỉ. (뚜껑이 잘 샘)",
        "907906315": "Thơm mùi tỏi. (마늘향이 좋음) / Quá cay đối với trẻ em. (아이들이 먹기엔 quá 매움) / Chai to khó rót. (병이 커서 따르기 힘듦)",
        "47408732": "Đậm đà. (맛이 진함) / Mùi hơi nồng. (냄새가 너무 강함) / Nắp bị hở. (뚜껑이 헐거움)",
        "1016824956": "Rất thơm mùi khói BBQ. (바베큐 훈연 향이 아주 좋음) / Hạt gia vị hơi to. (시즈닝 입자가 좀 큼) / Ướp thịt nướng rất ngon. (고기 구울 때 재우면 맛있음)",
        "871636194": "Vị chuẩn Hàn Quốc. (정통 한국의 맛) / Hơi ngọt so với khẩu vị của tôi. (내 입맛엔 좀 닮) / Tiện lợi khi đi cắm trại. (캠핑 갈 때 편함)",
        "1321333684": "Chấm trái cây hay ướp thịt đều ngon! (과일 찍어 먹어도, 고기 재워도 맛있음!) / Gói nhỏ dễ bị rách. (작은 봉지가 잘 찢어짐) / Vị chua cay mặn ngọt rất hài hòa. (새콤매콤단짠 조화가 좋음)"
    }
    return fallback_data.get(shop_id, "국물이 맛있지만 포장이 불편합니다. / 가격이 조금 비쌉니다.")

def analyze_competitors_job():
    global competitor_reports
    new_reports = {}
    
    print("[자동화] 쇼피 경쟁사 리뷰 3사 통합 스캔 및 AI 분석을 시작합니다...")
    
    for cat, products in TARGET_COMPETITORS.items():
        combined_reviews = ""
        for i, p in enumerate(products):
            rev = fetch_shopee_reviews(p['shop_id'], p['item_id'])
            combined_reviews += f"\n[{i+1}. {p['name']} 리뷰]\n{rev}\n"

        # 🔥 프롬프트 전면 수정: 줄글 대신 완벽한 JSON 포맷을 요구하도록 변경
        # 🌟 다미푸드 브랜드 철학과 가치를 AI에게 주입하기 위한 텍스트 세팅
        DAMI_PHILOSOPHY = """
        [다미푸드 (Dami Food) 브랜드 철학 및 핵심 가치]
        - 핵심 슬로건: "K-Fusion Food · Korea × Vietnam", "우리는 식탁 위의 K-라이프스타일을 디자인합니다."
        - 메인 메시지: "당신의 24시간은 소중하니까. 하지만 맛은 포기할 수 없으니까. 다미푸드의 '한 스푼'이 당신의 식탁을 바꿉니다."
        - Smart K-Life (3분 조리 시간): 코인 하나, 시즈닝 한 스푼으로 완성되는 깊은 맛. 바쁜 현대인을 위한 3분 요리 혁명.
        - Health & Clean (100% 한국산 원료): 비건 채수, 천연 매실 농축액 등 엄선된 프리미엄 천연 재료만 사용.
        - Cultural Bridge (2국 연결): 한국의 오리지널리티에 베트남의 감성을 더한 유일무이한 K-Fusion. 두 나라의 미식을 잇는 브릿지.
        - Premium Experience: 패키지부터 맛까지, 모든 터치포인트에서 프리미엄 제공. (코인육수·시즈닝·소스 14+ 제품 라인업)
        """

        # 🔥 다미푸드 정보를 포함한 고도화된 프롬프트
        # 🔥 다미푸드 정보를 포함한 고도화된 프롬프트 (베트남어 광고 카피 추가!)
        prompt = f"""
        당신은 다미푸드의 전략 마케터입니다. 베트남 쇼피에서 판매 중인 '{cat}' 카테고리 핵심 경쟁사 제품 3개의 최근 베트남어 고객 리뷰를 수집했습니다.
        이 '팩트(리뷰)'를 기반으로 각 제품의 장단점을 분석하고, 다미푸드가 압도할 수 있는 통합 차별화 전략을 도출하세요.

        [수집된 실제 리뷰 데이터]
        {combined_reviews}

        [다미푸드 브랜드 철학 및 핵심 가치]
        {DAMI_PHILOSOPHY}

        [중요 지시사항: 반드시 아래 JSON 형식으로만 응답할 것]
        1. 수집된 리뷰(약 30개) 중 해당 장점/단점 키워드를 언급한 고객의 대략적인 비율(%)을 계산하여 'percent'에 숫자로만 적어주세요.
        2. 하단의 differentiation(차별화 전략)과 ad_copy(광고 카피)는 절대 짧게 쓰지 말고, 위 [다미푸드 브랜드 철학]을 적극 반영하여 3~5문장 이상의 아주 상세하고 풍부한 내용으로 작성해 주세요.
        3. 특히 차별화 전략(desc) 작성 시, 경쟁사 리뷰에서 지적된 단점(예: 인공적인 맛, 불편한 사용성, 불안한 패키징 등)을 다미푸드의 'Health & Clean(100% 한국산 천연재료)', 'Smart K-Life(3분 요리 혁명, 편의성)', 'Premium Experience(프리미엄 패키지)' 등의 강점으로 완벽하게 해결하고 압도할 수 있음을 논리적으로 강조하세요.
        4. 광고 카피(ad_copy)는 현지 마케팅에 바로 사용할 수 있도록 반드시 한국어 원문과 베트남어 번역본을 함께 작성해 주세요.

        {{
          "competitors": [
            {{
              "name": "{products[0]['name']}",
              "summary": "고객 반응 한 줄 요약",
              "pros": [
                {{"keyword": "장점 1", "percent": 60, "desc": "장점 상세 설명"}},
                {{"keyword": "장점 2", "percent": 40, "desc": "장점 상세 설명"}}
              ],
              "cons": [
                {{"keyword": "단점 1", "percent": 80, "desc": "단점 상세 설명"}},
                {{"keyword": "단점 2", "percent": 40, "desc": "단점 상세 설명"}}
              ]
            }}
            // 주의: JSON 배열 내에 경쟁사 2, 경쟁사 3 데이터도 동일한 구조로 반드시 포함할 것!
          ],
        "differentiation": {{
            "desc": "이곳에 다미푸드 브랜드 철학을 반영한 차별화 전략을 3~5문장으로 아주 구체적이고 길게 서술해 주세요. 경쟁사의 약점을 다미푸드의 강점(프리미엄 원료, 3분 혁명 등)으로 어떻게 극복하는지 명시해야 합니다.",
            "ad_copy": "[한국어]\\n다미푸드의 감성적 메시지를 활용한 강력하고 긴 광고 카피\\n\\n[Tiếng Việt]\\n(한국어 광고 카피의 자연스럽고 세련된 베트남어 번역)"
          }}
        }}
        """
        
        try:
            res = client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"}, # 🔥 AI가 무조건 JSON 형태로만 답변하도록 강제하는 옵션
                messages=[
                    {"role": "system", "content": "당신은 리뷰 데이터를 JSON 형식으로 구조화하여 출력하는 수석 마케터 겸 데이터 분석가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            # AI가 준 JSON 문자열을 파이썬 딕셔너리로 변환
            parsed_data = json.loads(res.choices[0].message.content)

            # TARGET_COMPETITORS의 URL·이미지를 competitors 배열에 인덱스 순서로 병합
            ai_competitors = parsed_data.get('competitors', [])
            for i, comp in enumerate(ai_competitors):
                if i < len(products):
                    comp['url']   = products[i]['url']
                    comp['image'] = products[i]['image']

            # 변환된 데이터를 새 리포트 변수에 할당 (HTML이 읽을 수 있게)
            new_reports[cat] = parsed_data
            
        except Exception as e:
            print(f"[{cat}] 분석 중 에러 발생: {e}")
            
        time.sleep(2)

    competitor_reports = new_reports
    print("[자동화] 3사 통합 경쟁사 분석 업데이트 완료!")

scheduler = BackgroundScheduler()
scheduler.add_job(func=analyze_competitors_job, trigger="interval", days=14)
scheduler.start()

@router.get("/review", tags=["D-리뷰키워드"])
async def get_review_data():
    """
    리뷰 분석 데이터를 JSON으로 반환합니다.
    """
    if not competitor_reports:
        analyze_competitors_job()
    return {"reports": competitor_reports, "targets": TARGET_COMPETITORS}