"""
★ E파트 — SNS 콘텐츠 생성 라우터 (sns_generator.py) ★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[담당 팀원] E파트
[수정 가능 범위] 이 파일 전체 + services/youtube_api.py + templates/b2b/sns.html의 {% block content %} 안

[이 파일이 해야 할 일]
  기본 엔드포인트 3개 + 확장 기능 구현:

  1) GET  /sns/trends        → 유튜브 먹방 트렌드 수집
  2) POST /sns/tiktok        → 틱톡 15초 대본 + 쇼츠 프롬프트 생성
  3) POST /sns/dm            → 인플루언서 DM 문구 생성 (발송 X, 문구만)

  🔥 추가로, PM이 별도 Flask 앱으로 만들어둔 기능을 FastAPI 구조로 이식함:
  4) POST /sns/shorts        → 베트남 유튜브 쇼츠 바이럴 영상 + 마케팅 기획안 생성
  5) GET  /sns/tiktokers     → TikTok 인플루언서(팔로워 수 범위 필터) 검색

  ※ main.py에서 include_router(..., prefix="/api") 로 연결되므로
     실제 경로는 /api/sns/... 형태가 됩니다.

[HTML(sns.html)이 보내는 요청]
  // 트렌드
  fetch('/api/sns/trends')

  // 틱톡 대본
  fetch('/api/sns/tiktok', {
    method: 'POST',
    body: JSON.stringify({ product: "코인육수" })
  })

  // DM 문구
  fetch('/api/sns/dm', {
    method: 'POST',
    body: JSON.stringify({ influencer_name: "@mukbang_hanoi", product: "코인육수" })
  })

  // 유튜브 쇼츠 바이럴 + 기획안
  fetch('/api/sns/shorts', {
    method: 'POST',
    body: JSON.stringify({ months_ago: 1 })
  })

  // TikTok 인플루언서 검색
  fetch('/api/sns/tiktokers?keyword=...&min_followers=10000&max_followers=30000&results_count=20')

[반드시 반환해야 하는 형식]
  // /api/sns/trends
  { "trends": [{ "title", "channel", "views", "thumbnail" }] }

  // /api/sns/tiktok
  { "script_vn": "베트남어 대본", "prompt_ko": "쇼츠 제작 프롬프트" }

  // /api/sns/dm
  { "dm_text": "DM 전문 (베트남어)" }

  // /api/sns/shorts
  { "videos": [{ "title", "url", "thumbnail", "likes", "comments", "top_comments", "idea" }] }

  // /api/sns/tiktokers
  {
    "results": [{ "name", "unique_id", "followers", "likes", "videos", "email", "bio", "link", "external_link", "has_email" }],
    "found": 10,
    "scanned": 123
  }

[틱톡 주의사항]
  · 틱톡 공식 API는 DM 발송을 지원하지 않음
  · DM 문구 생성 후 복사 버튼으로 수동 발송 → HTML에 이미 구현됨
  · 자동 발송 기능을 추가하면 계정 정지 위험 있음 — 절대 구현 금지

[AI 프롬프트 파일]
  prompts/PART_E_sns.md 참고

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[병합 규칙]
  · main.py 수정 금지
  · CSS 클래스명: .e- prefix (예: .e-trend-card)
  · YouTube API 할당량 주의: 일 10,000유닛 (검색 1회=100유닛)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import os
import json
import time
import re
from datetime import datetime, timedelta

import requests
from apify_client import ApifyClient
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

router = APIRouter()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_INFLUENCER_KEY = os.getenv("YOUTUBE_INFLUENCER_KEY") or os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APIFY_API_KEY = os.getenv("APIFY_API_TOKEN")

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
apify_client = ApifyClient(APIFY_API_KEY) if APIFY_API_KEY else None


class TiktokRequest(BaseModel):
    product: str


class DMRequest(BaseModel):
    influencer_name: str
    product: str


class ShortsRequest(BaseModel):
    months_ago: int = 1


def _ensure_openai_keys():
    if not OPENAI_API_KEY or not openai_client:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY가 설정되어 있지 않습니다. .env를 확인해 주세요.",
        )


def _ensure_youtube_key():
    if not YOUTUBE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="YOUTUBE_API_KEY가 설정되어 있지 않습니다. .env를 확인해 주세요.",
        )


def _ensure_apify_key():
    if not APIFY_API_KEY or not apify_client:
        raise HTTPException(
            status_code=500,
            detail="APIFY_API_KEY가 설정되어 있지 않습니다. .env를 확인해 주세요.",
        )


@router.get("/sns/trends", tags=["E-SNS콘텐츠"])
async def get_trends():
    """유튜브 베트남 먹방 트렌드를 수집합니다."""
    _ensure_youtube_key()

    search_url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=id,snippet&q=vietnam+mukbang+food&regionCode=VN&type=video"
        f"&order=viewCount&maxResults=10&key={YOUTUBE_API_KEY}"
    )
    try:
        search_resp = requests.get(search_url, timeout=15).json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube API 요청 실패: {e}")

    if "error" in search_resp:
        raise HTTPException(status_code=500, detail=f"YouTube API 오류: {search_resp['error'].get('message')}")

    items = search_resp.get("items", [])
    if not items:
        return {"trends": []}

    # 조회수 가져오기
    video_ids = ",".join(i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId"))
    stats_url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=statistics&id={video_ids}&key={YOUTUBE_API_KEY}"
    )
    stats_resp = requests.get(stats_url, timeout=15).json()
    stats_map = {
        v["id"]: v.get("statistics", {})
        for v in stats_resp.get("items", [])
    }

    trends = []
    for item in items:
        vid = item.get("id", {}).get("videoId", "")
        snippet = item.get("snippet", {})
        stats = stats_map.get(vid, {})
        view_count = int(stats.get("viewCount", 0))
        thumbnails = snippet.get("thumbnails", {})
        thumb = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url", "")
        )
        trends.append({
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "views": f"{view_count:,}",
            "thumbnail": thumb,
            "url": f"https://www.youtube.com/watch?v={vid}" if vid else ""
        })

    return {"trends": trends}


@router.post("/sns/tiktok", tags=["E-SNS콘텐츠"])
async def generate_tiktok_script(req: TiktokRequest):
    """틱톡 15초 대본과 쇼츠 프롬프트를 생성합니다."""
    _ensure_openai_keys()

    prompt = f"""
다미푸드의 '{req.product}' 제품을 홍보하는 틱톡 15초 숏폼 대본을 작성해주세요.
타겟: K-푸드에 관심 많은 베트남 2030세대 및 젊은 주부
톤: 밝고 트렌디하며, 실제 베트남 틱톡커 말투로

[반환 형식 — 반드시 이 구분자로 나눠주세요]
===SCRIPT_VN===
(베트남어 15초 대본 — 씬 별로 자막/나레이션 포함)
===PROMPT_KO===
(한국어 쇼츠 제작 프롬프트 — 촬영 방법, 편집 포인트, 추천 BGM, 해시태그 포함)
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "당신은 베트남 SNS 마케팅 전문가입니다. 현지 트렌드에 맞는 숏폼 콘텐츠를 기획합니다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=1500,
    )

    raw = response.choices[0].message.content or ""
    script_vn, prompt_ko = "", ""
    if "===SCRIPT_VN===" in raw and "===PROMPT_KO===" in raw:
        parts = raw.split("===PROMPT_KO===")
        script_vn = parts[0].replace("===SCRIPT_VN===", "").strip()
        prompt_ko = parts[1].strip()
    else:
        script_vn = raw.strip()

    return {"script_vn": script_vn, "prompt_ko": prompt_ko}


@router.post("/sns/dm", tags=["E-SNS콘텐츠"])
async def generate_dm(req: DMRequest):
    """인플루언서 DM 문구를 생성합니다 (발송 기능 없음)."""
    _ensure_openai_keys()

    prompt = f"""
베트남 틱톡 인플루언서 '{req.influencer_name}'에게 보낼 협찬 제안 DM 문구를 베트남어로 작성해주세요.
제품: 다미푸드 '{req.product}'
톤: 정중하지만 친근하게, 실제 베트남 비즈니스 메시지 말투로
내용: 자기소개 → 제품 소개 → 협찬 제안 → 연락 요청
길이: 3~5문단, 너무 길지 않게

마지막에 한국어 번역도 함께 붙여주세요.
형식:
[베트남어]
(DM 본문)

[한국어 번역]
(번역본)
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "당신은 베트남 인플루언서 마케팅 전문가입니다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=800,
    )

    dm_text = response.choices[0].message.content or ""
    return {"dm_text": dm_text}


# ─────────────────────────────────────────────
# 유튜브 쇼츠 바이럴 + 마케팅 기획안 (유튜브쇼츠/app.py 이식)
# ─────────────────────────────────────────────

def _get_viral_vn_shorts(months_ago: int):
    """
    베트남 바이럴 쇼츠를 가져오고 썸네일과 '실제 베스트 댓글 TOP 5'를 포함하여 필터링합니다.
    원본: 유튜브쇼츠/app.py:get_viral_vn_shorts
    """
    _ensure_youtube_key()

    now = datetime.utcnow()
    start_date = now - timedelta(days=30 * int(months_ago))
    published_after = start_date.isoformat("T") + "Z"

    search_queries = [
        "%23xuhuong+%23shorts+ẩm+thực",         # 베트남 트렌드 + 음식
        "mukbang+vietnam+%23fyp+đồ+ăn+Hàn",     # 먹방 + K-푸드
    ]

    seen_ids: set[str] = set()
    all_video_ids: list[str] = []

    for sq in search_queries:
        search_url = (
            "https://www.googleapis.com/youtube/v3/search"
            f"?part=id&q={sq}&regionCode=VN&relevanceLanguage=vi&type=video&videoDuration=short"
            f"&order=relevance&publishedAfter={published_after}&maxResults=50&key={YOUTUBE_API_KEY}"
        )
        search_response = requests.get(search_url, timeout=15).json()
        for item in search_response.get("items", []):
            vid = item["id"]["videoId"]
            if vid not in seen_ids:
                seen_ids.add(vid)
                all_video_ids.append(vid)

    if not all_video_ids:
        return []

    video_ids = ",".join(all_video_ids[:50])
    stats_url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,statistics&id={video_ids}&key={YOUTUBE_API_KEY}"
    )
    stats_response = requests.get(stats_url, timeout=15).json()

    # relevance로 가져온 결과를 조회수 기준 내림차순 재정렬
    if "items" in stats_response:
        stats_response["items"].sort(
            key=lambda x: int(x.get("statistics", {}).get("viewCount", 0)),
            reverse=True,
        )

    filtered_videos: list[dict] = []
    if "items" in stats_response:
        for item in stats_response["items"]:
            stats = item.get("statistics", {})
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))

            # 최소 임계치: 좋아요 3,000 이상
            if likes >= 3000:
                video_id = item["id"]

                comments_url = (
                    "https://www.googleapis.com/youtube/v3/commentThreads"
                    f"?part=snippet&videoId={video_id}&maxResults=5&order=relevance&key={YOUTUBE_API_KEY}"
                )
                comments_response = requests.get(comments_url, timeout=15).json()

                top_comments: list[str] = []
                if "items" in comments_response:
                    for c_item in comments_response["items"]:
                        comment_text = c_item["snippet"]["topLevelComment"]["snippet"]["textOriginal"]
                        comment_text = comment_text.replace("\n", " ")[:100]
                        top_comments.append(comment_text)

                top_comments_str = " / ".join(top_comments) if top_comments else "댓글 없음"

                thumbnails = item["snippet"].get("thumbnails", {})
                thumb_url = (
                    thumbnails.get("high", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url")
                )

                filtered_videos.append(
                    {
                        "title": item["snippet"]["title"],
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "thumbnail": thumb_url,
                        "likes": f"{likes:,}",
                        "comments": f"{comments:,}",
                        "top_comments": top_comments_str,
                    }
                )

            if len(filtered_videos) >= 10:
                break

    return filtered_videos


def _add_ideas_to_videos(videos: list[dict]):
    """
    각 영상별로 1:1 맞춤형 마케팅 기획안을 생성하여 합칩니다 (실제 댓글 분석 포함).
    원본: 유튜브쇼츠/app.py:add_ideas_to_videos
    """
    _ensure_openai_keys()

    if not videos:
        return []

    prompt = (
        f"다음은 베트남에서 바이럴 중인 유튜브 쇼츠 영상 제목과 실제 베스트 댓글(TOP 5) 총 {len(videos)}개입니다:\n"
    )
    for i, v in enumerate(videos):
        prompt += f"[{i + 1}] 제목: {v['title']}\n    실제 반응(댓글): {v['top_comments']}\n"

    prompt += f"""
당신의 임무는 위 {len(videos)}개의 각 영상(1번부터 {len(videos)}번까지 빠짐없이)의 트렌드와 '실제 현지인 댓글 반응'을 분석하여,
원본 영상의 '특정 행동, 춤, 대사, 상황극'을 유추하고 이를 패러디(Parody)하는 마케팅 기획안을 작성하는 것입니다. 
다미푸드의 주력 제품인 '코인육수, 가루 시즈닝, 액체 소스' 중 가장 잘 어울리는 제품을 자연스럽게 녹여주세요. 타겟은 K-푸드에 관심 많은 베트남 2030 및 젊은 주부입니다.

[필수 규칙]
1. 반드시 총 {len(videos)}개의 기획안을 작성해야 합니다. 중간에 멈추지 말고 끝까지 작성하세요.
2. 각 기획안 사이에는 반드시 '|||' (수직선 3개) 기호를 넣어 구분해주세요. (예: 1번내용 ||| 2번내용 ||| 3번내용)
3. 무조건 다 제안하지 말고, '숏폼 영상', 'SNS 이미지/카드뉴스', '프로모션/참여 유도' 이 3가지 포맷 중 가장 시너지가 날 것 같은 포맷 1가지만 골라서 기획해주세요.
4. 원본 영상의 어떤 시각적 행동(춤, 제스처, 표정, 특정 대사 등)을 어떻게 똑같이 따라 할 것인지(패러디) 구체적인 연출 포인트를 반드시 포함하세요.
5. 구매 전환(CTA) 문구는 번역투를 피하고, 실제 베트남 틱톡커가 쓸 법한 '트렌디한 요즘 말투, 호들갑, FOMO(품절 임박 등) 자극' 감성으로 이모지와 함께 작성하세요.

[양식]
🗣️ 바이럴 핵심 분석 (실제 댓글 기반): (제공된 '실제 반응(댓글)'을 바탕으로 이 영상의 어떤 포인트에서 현지인들이 빵 터지거나 공감했는지 분석)
🎭 행동/대사 패러디 연출 포인트: (제목과 댓글로 유추한 원본 영상의 핵심 행동, 춤, 대사를 배우가 어떻게 똑같이 따라 하면서 다미푸드 제품으로 패러디할 것인가?)
🎯 최적화 포맷 선정: (숏폼 영상 / SNS 이미지 / 프로모션 중 1개 선택 및 이유)
📝 상세 실행 기획안: (선택한 포맷에 맞춰 구체적이고 현실적인 기획 작성)
🛒 구매 전환 (CTA) 카피: 
   - 🇰🇷 [한국어]: 
   - 🇻🇳 [베트남어]: 
🎵 추천 BGM 및 현지 해시태그: (어울리는 베트남 트렌드 BGM 분위기 제안 및 복사해서 바로 쓸 수 있는 베트남어 해시태그 3~5개)
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 실제 데이터를 기반으로 팩트를 짚어내어, "
                    "바이럴 영상의 핵심 시각적 포인트(춤, 대사, 표정 등)를 완벽하게 패러디하는 "
                    "마케팅 액션을 도출하는 다미푸드의 수석 퍼포먼스 마케터입니다."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=4000,
    )

    raw_ideas = response.choices[0].message.content
    ideas_list = [idea.strip() for idea in raw_ideas.split("|||") if idea.strip()]

    for i, v in enumerate(videos):
        if i < len(ideas_list):
            v["idea"] = ideas_list[i]
        else:
            v["idea"] = (
                "기획안 생성 실패 (내용이 너무 길어 AI 답변이 누락되었습니다. 다시 요청해 주세요.)"
            )

    return videos


@router.post("/sns/shorts", tags=["E-SNS콘텐츠"])
async def generate_shorts_ideas(req: ShortsRequest):
    """
    베트남 유튜브 쇼츠 바이럴 영상 + 1:1 마케팅 기획안을 생성합니다.
    원본: 유튜브쇼츠/app.py 의 index 뷰를 JSON API로 변환.
    """
    videos = _get_viral_vn_shorts(req.months_ago)
    videos_with_ideas = _add_ideas_to_videos(videos)
    return {"videos": videos_with_ideas}

# 커서 이식 끝


# ─────────────────────────────────────────────
# TikTok 인플루언서 검색 (vietnam/app.py 이식, JSON API 버전)
# ─────────────────────────────────────────────
# 커서 이식 시작: vietnam/app.py


@router.get("/sns/tiktokers", tags=["E-SNS콘텐츠"])
async def search_tiktokers(
    keyword: str,
    min_followers: int = 10000,
    max_followers: int = 30000,
    country: str = "VN",
    results_count: int = 20,
):
    _ensure_apify_key()

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': f'🔍 [{keyword}] 키워드로 TikTok 검색 시작...'})}\n\n"

            run_input = {
                "hashtags": [keyword],
                "searchQueries": [keyword],
                "searchType": "user",
                "resultsPerPage": results_count,
                "maxProfilesPerQuery": results_count,
                "shouldDownloadVideos": False,
                "shouldDownloadCovers": False,
                "shouldDownloadSubtitles": False,
                "shouldDownloadSlideshowImages": False,
            }

            yield f"data: {json.dumps({'type': 'status', 'message': '⚙️ Apify 서버에서 데이터 수집 중... (30초~2분 소요)'})}\n\n"

            run = apify_client.actor("clockworks/tiktok-scraper").call(run_input=run_input)

            yield f"data: {json.dumps({'type': 'status', 'message': '📦 데이터 분석 및 필터링 중...'})}\n\n"

            found_count = 0
            total_scanned = 0

            for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                total_scanned += 1

                author_stats = item.get("authorStats", {})
                user_info = item.get("author", item.get("user", {}))

                followers = (
                    author_stats.get("followerCount", 0) or
                    item.get("followerCount", 0) or
                    user_info.get("followerCount", 0)
                )

                if not (min_followers <= followers <= max_followers):
                    continue

                nickname = (
                    user_info.get("nickname", "") or
                    user_info.get("name", "") or
                    item.get("nickname", "알 수 없음")
                )
                unique_id = (
                    user_info.get("uniqueId", "") or
                    user_info.get("id", "") or
                    item.get("uniqueId", "")
                )
                bio = (
                    user_info.get("signature", "") or
                    user_info.get("bio", "") or
                    item.get("signature", "")
                )

                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', bio)
                links = re.findall(r'https?://[^\s]+', bio)

                result = {
                    "type": "result",
                    "name": nickname,
                    "unique_id": unique_id,
                    "followers": followers,
                    "likes": author_stats.get("heartCount", author_stats.get("heart", 0)),
                    "videos": author_stats.get("videoCount", 0),
                    "email": emails[0] if emails else "N/A",
                    "bio": bio[:100] + "..." if len(bio) > 100 else bio,
                    "link": f"https://www.tiktok.com/@{unique_id}" if unique_id else "N/A",
                    "external_link": links[0] if links else "N/A",
                    "has_email": bool(emails),
                }

                found_count += 1
                yield f"data: {json.dumps(result)}\n\n"
                time.sleep(0.05)

            yield f"data: {json.dumps({'type': 'done', 'found': found_count, 'scanned': total_scanned})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ═══════════════════════════════════════════════════════════════
# ★ PM 추가 기능 — 밈 숏폼 영상 자동 생성 (팀원 코드와 완전 독립)
#
# [플로우]
#   1) YouTube Data API  → 특정 검색어 댓글 최대 50개 수집  (~101유닛)
#   2) Groq llama-3.3-70b → 댓글 분석 → 영어 프롬프트 1문장 생성 (무료)
#   3) Magic Hour API    → Text-to-Video, end_seconds=5 하드코딩
#
# [엔드포인트]  POST /api/sns/meme
# [HTML 호출]   fetch('/api/sns/meme', { method:'POST', body: JSON.stringify({query:'K-food Vietnam'}) })
# ═══════════════════════════════════════════════════════════════

MAGICHOUR_API_KEY = os.getenv("MAGICHOUR_AI_API_KEY")
GROQ_API_KEY      = os.getenv("GROQ_CLOUD_API_KEY")


def _ensure_magichour_key():
    if not MAGICHOUR_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="MAGICHOUR_AI_API_KEY가 설정되어 있지 않습니다. .env를 확인해 주세요."
        )


def _ensure_groq_key():
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_CLOUD_API_KEY가 설정되어 있지 않습니다. .env를 확인해 주세요."
        )


class MemeRequest(BaseModel):
    query: str = "K-food Vietnam mukbang"   # 유튜브 검색어


# ── Step 1: 유튜브 댓글 수집 ──────────────────────────────────
def _collect_youtube_comments(query: str, max_comments: int = 50) -> list[str]:
    """
    검색어로 유튜브 영상을 찾고 댓글 최대 50개를 반환합니다.
    YouTube API 소모: 검색 100유닛 + 댓글 1유닛 = ~101유닛
    """
    _ensure_youtube_key()

    # 영상 검색 (가장 조회수 높은 1개만)
    search_url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=id&q={requests.utils.quote(query)}&regionCode=VN"
        f"&type=video&order=viewCount&maxResults=1&key={YOUTUBE_API_KEY}"
    )
    search_resp = requests.get(search_url, timeout=15).json()
    items = search_resp.get("items", [])
    if not items:
        return []

    video_id = items[0]["id"]["videoId"]

    # 댓글 수집
    comments_url = (
        "https://www.googleapis.com/youtube/v3/commentThreads"
        f"?part=snippet&videoId={video_id}"
        f"&maxResults={max_comments}&order=relevance&key={YOUTUBE_API_KEY}"
    )
    comments_resp = requests.get(comments_url, timeout=15).json()

    comments = []
    for c in comments_resp.get("items", []):
        text = c["snippet"]["topLevelComment"]["snippet"]["textOriginal"]
        text = text.replace("\n", " ")[:150]
        comments.append(text)

    return comments


# ── Step 2: Groq로 영상 프롬프트 생성 ────────────────────────
def _generate_video_prompt_with_groq(comments: list[str]) -> str:
    """
    수집된 댓글을 Groq llama-3.3-70b로 분석해 영어 프롬프트 1문장을 생성합니다.
    """
    _ensure_groq_key()
    from groq import Groq

    groq_client = Groq(api_key=GROQ_API_KEY)

    comments_text = "\n".join(f"- {c}" for c in comments[:50])

    system_prompt = (
        "You are a viral marketing expert specializing in short-form video content for Vietnamese social media. "
        "Analyze YouTube comments and generate a single, punchy English prompt for a 5-second meme video."
    )

    user_prompt = f"""Here are YouTube comments about K-food in Vietnam:

{comments_text}

Based on the most positive and viral reactions above, generate exactly ONE short and powerful English prompt 
for a Text-to-Video AI to create a 5-second meme video promoting K-food (Korean food sauces, broths, seasonings).

Rules:
- Output ONLY the prompt sentence, nothing else
- Make it visually descriptive and energetic
- Include food visuals, Vietnamese cultural elements if relevant
- End with exactly this text: (Duration: Maximum 5 seconds)
"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=200,
    )

    prompt_text = response.choices[0].message.content.strip()

    # 안전장치: Duration 문구가 없으면 강제 추가
    if "(Duration: Maximum 5 seconds)" not in prompt_text:
        prompt_text += " (Duration: Maximum 5 seconds)"

    return prompt_text


# ── Step 3: Magic Hour Text-to-Video ─────────────────────────
def _create_magichour_video(prompt_text: str) -> dict:
    """
    Magic Hour Text-to-Video API 호출.
    end_seconds=5 하드코딩 (크레딧 방어)
    """
    _ensure_magichour_key()

    headers = {
        "Authorization": f"Bearer {MAGICHOUR_API_KEY}",
        "Content-Type": "application/json",
    }

    # 영상 생성 요청
    create_payload = {
        "end_seconds": 5,           # ★ 크레딧 방어 — 절대 변경 금지
        "orientation": "portrait",  # 틱톡/쇼츠용 세로 포맷
        "resolution": "480p",       # 크레딧 절약
        "style": {
            "prompt": prompt_text,
        },
    }

    create_resp = requests.post(
        "https://api.magichour.ai/v1/text-to-video",
        headers=headers,
        json=create_payload,
        timeout=30,
    )

    if create_resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=500,
            detail=f"Magic Hour 영상 생성 실패: {create_resp.text}"
        )

    result = create_resp.json()
    video_id = result.get("id")

    # 생성 요청만 전송하고 즉시 반환
    # (렌더링에 1~3분 소요 → 폴링 시 이벤트 루프 블로킹으로 브라우저 연결 끊김)
    # 완료된 영상은 Magic Hour 라이브러리에서 확인 가능
    return {"video_id": video_id, "status": "submitted", "prompt_used": prompt_text}


# ── 메인 엔드포인트 ───────────────────────────────────────────
@router.post("/sns/meme", tags=["E-SNS콘텐츠"])
async def generate_meme_video(req: MemeRequest):
    """
    유튜브 댓글 수집 → Groq 프롬프트 생성 → Magic Hour 5초 밈 영상 생성

    반환:
      { "video_url": "...", "video_id": "...", "prompt_used": "...", "comments_collected": 30 }
    """
    # Step 1: 유튜브 댓글 수집
    comments = _collect_youtube_comments(req.query, max_comments=50)
    if not comments:
        raise HTTPException(status_code=404, detail="댓글을 수집할 수 없었습니다. 검색어를 바꿔보세요.")

    # Step 2: Groq 프롬프트 생성
    prompt_text = _generate_video_prompt_with_groq(comments)

    # Step 3: Magic Hour 영상 생성
    video_result = _create_magichour_video(prompt_text)

    return {
        **video_result,
        "comments_collected": len(comments),
    }

# ═══════════════════════════════════════════════════════════════
# ★ YouTube 인플루언서 파인더 (팀원 유튜브구독자.html 이식)
#
# [플로우]  YouTube Search API → 채널 통계 → 구독자 필터 → SSE 스트리밍
# [엔드포인트]  GET /api/sns/youtubers
# [HTML 호출]   EventSource('/api/sns/youtubers?keyword=...&min_subs=...&max_subs=...&results_count=...')
# ═══════════════════════════════════════════════════════════════

# 커서 이식 시작: 유튜브구독자.html → FastAPI SSE 버전

@router.get("/sns/youtubers", tags=["E-SNS콘텐츠"])
async def search_youtubers(
    keyword: str,
    min_subs: int = 10000,
    max_subs: int = 500000,
    results_count: int = 20,
):
    """
    구독자 수 범위로 베트남 유튜브 인플루언서를 검색합니다.
    SSE 스트리밍 방식으로 결과를 실시간 전달합니다.
    """
    _ensure_youtube_key()

    def generate():
        import re as _re

        try:
            yield f"data: {json.dumps({'type': 'status', 'message': f'🔍 [{keyword}] 키워드로 YouTube 검색 시작...'})}\n\n"

            # ── Step 1: 영상 검색으로 채널 ID 수집 ──────────────
            search_url = (
                "https://www.googleapis.com/youtube/v3/search"
                f"?part=snippet&q={requests.utils.quote(keyword)}"
                f"&type=video&regionCode=VN&maxResults=50&key={YOUTUBE_INFLUENCER_KEY}"
            )
            search_resp = requests.get(search_url, timeout=15).json()

            if "error" in search_resp:
                yield f"data: {json.dumps({'type': 'error', 'message': search_resp['error'].get('message', 'YouTube API 오류')})}\n\n"
                return

            items = search_resp.get("items", [])
            if not items:
                yield f"data: {json.dumps({'type': 'done', 'found': 0, 'scanned': 0})}\n\n"
                return

            # 중복 채널 제거
            channel_ids = list({
                item["snippet"]["channelId"]
                for item in items
                if item.get("snippet", {}).get("channelId")
            })

            yield f"data: {json.dumps({'type': 'status', 'message': f'📦 채널 {len(channel_ids)}개 정보 수집 중...'})}\n\n"

            # ── Step 2: 채널 통계 일괄 조회 (50개씩) ────────────
            found_count = 0
            total_scanned = 0

            for i in range(0, len(channel_ids), 50):
                batch = ",".join(channel_ids[i:i+50])
                channels_url = (
                    "https://www.googleapis.com/youtube/v3/channels"
                    f"?part=snippet,statistics&id={batch}&key={YOUTUBE_INFLUENCER_KEY}"
                )
                ch_resp = requests.get(channels_url, timeout=15).json()

                for ch in ch_resp.get("items", []):
                    total_scanned += 1
                    stats = ch.get("statistics", {})
                    subscriber_count = int(stats.get("subscriberCount", 0))

                    # 구독자 수 필터
                    if not (min_subs <= subscriber_count <= max_subs):
                        continue

                    snippet = ch.get("snippet", {})
                    description = snippet.get("description", "")

                    # 이메일 추출
                    emails = _re.findall(
                        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                        description
                    )
                    links = _re.findall(r'https?://[^\s]+', description)

                    result = {
                        "type":        "result",
                        "name":        snippet.get("title", "(이름 없음)"),
                        "subscribers": subscriber_count,
                        "bio":         description[:120] + "..." if len(description) > 120 else description,
                        "email":       emails[0] if emails else "N/A",
                        "link":        f"https://www.youtube.com/channel/{ch['id']}",
                        "external_link": links[0] if links else "N/A",
                        "has_email":   bool(emails),
                    }

                    found_count += 1
                    yield f"data: {json.dumps(result)}\n\n"
                    time.sleep(0.05)

                    if found_count >= results_count:
                        break

                if found_count >= results_count:
                    break

            yield f"data: {json.dumps({'type': 'done', 'found': found_count, 'scanned': total_scanned})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )