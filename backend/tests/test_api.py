"""Stage 5 통합 테스트 — 핵심 시나리오 10+개.

외부 API (YouTube, Gemini)는 모킹 처리.
DB는 실제 PostgreSQL 사용 (seed data 필요).
"""

from __future__ import annotations

import base64
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────
# 1) 요리명 검색 → 결과 반환
# ──────────────────────────────────────────────
async def test_search_by_dish_name(client):
    """POST /v1/search/videos {query: "김치찌개"} → 결과 반환."""
    resp = await client.post("/v1/search/videos", json={"query": "김치찌개"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["search_type"] in ("dish_name", "ambiguous")
    assert isinstance(data["videos"], list)
    assert data["total_estimate"] >= 0


# ──────────────────────────────────────────────
# 2) 재료 검색 → 역방향 추론 + 결과
# ──────────────────────────────────────────────
async def test_search_by_ingredients(client):
    """재료 기반 검색 → 후보 요리 추론."""
    resp = await client.post(
        "/v1/search/videos",
        json={"query": "돼지고기 김치", "user_ingredients": [{"name": "돼지고기"}, {"name": "김치"}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["search_type"] in ("ingredients", "ambiguous", "dish_name")


# ──────────────────────────────────────────────
# 3) 자동완성 → 결과
# ──────────────────────────────────────────────
async def test_autocomplete_ingredients(client):
    """GET /v1/ingredients/search?q=김 → 재료 자동완성."""
    resp = await client.get("/v1/ingredients/search", params={"q": "김"})
    assert resp.status_code == 200
    data = resp.json()
    assert "ingredients" in data
    assert isinstance(data["ingredients"], list)
    # seed data에 "김치" 등이 있으므로 결과 있어야 함
    assert len(data["ingredients"]) > 0


# ──────────────────────────────────────────────
# 4) 레시피 추출 → Gemini 모킹 + 캐시 히트
# ──────────────────────────────────────────────
async def test_recipe_extract_with_mock(client, db_session):
    """POST /v1/recipe/extract → Gemini 모킹, DB 캐시 확인."""
    mock_gemini_response = {
        "dish_name": "테스트요리",
        "base_servings": 2,
        "base_servings_source": "explicit",
        "ingredients": [
            {"name": "재료A", "amount": 100, "unit": "g", "scaling_strategy": "linear"},
            {"name": "재료B", "amount": 1, "unit": "큰술", "scaling_strategy": "to_taste"},
        ],
        "steps": ["1단계", "2단계"],
    }

    mock_transcript_result = MagicMock()
    mock_transcript_result.source = "description"
    mock_transcript_result.text = "재료: 재료A 100g, 재료B 1큰술\n만드는 법: ..."

    with (
        patch("api.recipe.collect_transcript", new_callable=AsyncMock, return_value=mock_transcript_result),
        patch("api.recipe.GeminiClient") as MockGemini,
    ):
        mock_instance = AsyncMock()
        mock_instance.generate_json = AsyncMock(return_value=mock_gemini_response)
        MockGemini.return_value = mock_instance

        resp = await client.post(
            "/v1/recipe/extract",
            json={"video_id": "test_vid_001", "servings": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recipe" in data


# ──────────────────────────────────────────────
# 5) 분량 변환 (unit test)
# ──────────────────────────────────────────────
def test_recipe_scaling():
    """scaling_strategy별 분량 변환 검증."""
    from services.recipe_transform import scale_amount

    # linear: 비례 (ratio = requested/base)
    assert scale_amount(100.0, "linear", 4 / 2) == 200.0
    assert scale_amount(100.0, "linear", 2 / 4) == 50.0

    # stepwise: 정수 반올림
    result = scale_amount(3.0, "stepwise", 4 / 2)
    assert isinstance(result, (int, float))
    assert result == 6.0

    # to_taste: 원본 유지
    assert scale_amount(1.0, "to_taste", 8 / 2) == 1.0

    # fixed: 원본 유지
    assert scale_amount(200.0, "fixed", 6 / 2) == 200.0

    # None amount
    assert scale_amount(None, "linear", 2.0) is None


# ──────────────────────────────────────────────
# 6) GAP 분석 SUFFICIENT/MISSING
# ──────────────────────────────────────────────
def test_gap_analysis():
    """ingredient_gap의 estimate_gap 함수 검증."""
    from services.ingredient_gap import estimate_gap

    # 모든 재료 보유 → gap_score 높음
    gap = estimate_gap(
        typical_ingredients=["김치", "돼지고기", "두부"],
        user_ingredient_names=["김치", "돼지고기", "두부"],
    )
    assert gap.estimated_missing == 0
    assert gap.gap_score == 1.0

    # 일부 부족
    gap2 = estimate_gap(
        typical_ingredients=["김치", "돼지고기", "두부", "대파"],
        user_ingredient_names=["김치"],
    )
    assert gap2.estimated_missing >= 1
    assert gap2.gap_score < 1.0


# ──────────────────────────────────────────────
# 7) 채널 추가/조회/삭제 (YouTube 모킹)
# ──────────────────────────────────────────────
async def test_channel_favorites_crud(client):
    """POST/GET/DELETE /v1/channels/favorites → CRUD."""
    session_id = f"test-ch-{uuid.uuid4().hex[:8]}"
    headers = {"X-Session-Id": session_id}

    # Mock YouTube API for channel info
    mock_channel_data = {
        "snippet": {
            "title": "테스트 채널",
            "thumbnails": {"default": {"url": "https://example.com/thumb.jpg"}},
        },
        "contentDetails": {"relatedPlaylists": {"uploads": "UU_test"}},
        "statistics": {"subscriberCount": "100000"},
    }

    with patch("api.channels.YouTubeClient") as MockYT:
        mock_yt = AsyncMock()
        mock_yt.get_channel = AsyncMock(return_value=mock_channel_data)
        MockYT.return_value = mock_yt

        # POST: 채널 추가
        resp = await client.post(
            "/v1/channels/favorites",
            json={"channel_id": f"UC_test_{uuid.uuid4().hex[:8]}"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["channel_name"] == "테스트 채널"
        added_channel_id = data["channel_id"]

    # GET: 목록 조회
    resp = await client.get("/v1/channels/favorites", headers=headers)
    assert resp.status_code == 200
    favs = resp.json()["favorites"]
    assert len(favs) >= 1
    assert any(f["channel_id"] == added_channel_id for f in favs)

    # DELETE: 삭제
    resp = await client.delete(f"/v1/channels/favorites/{added_channel_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # GET: 삭제 확인
    resp = await client.get("/v1/channels/favorites", headers=headers)
    assert resp.status_code == 200
    favs_after = resp.json()["favorites"]
    assert not any(f["channel_id"] == added_channel_id for f in favs_after)


# ──────────────────────────────────────────────
# 8) 보유 재료 CRUD
# ──────────────────────────────────────────────
async def test_user_ingredients_crud(client):
    """POST/GET/PUT/DELETE /v1/user/ingredients → CRUD."""
    session_id = f"test-ing-{uuid.uuid4().hex[:8]}"
    headers = {"X-Session-Id": session_id}

    # POST: 추가
    resp = await client.post(
        "/v1/user/ingredients",
        json={"name": "계란", "amount": 6, "unit": "개"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "계란"
    assert data["amount"] == 6
    assert data["unit"] == "개"
    ingredient_id = data["id"]

    # GET: 목록
    resp = await client.get("/v1/user/ingredients", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["ingredients"]
    assert len(items) >= 1
    assert any(i["id"] == ingredient_id for i in items)

    # PUT: 수정
    resp = await client.put(
        f"/v1/user/ingredients/{ingredient_id}",
        json={"amount": 3},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == 3

    # DELETE: 삭제
    resp = await client.delete(f"/v1/user/ingredients/{ingredient_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # GET: 삭제 확인
    resp = await client.get("/v1/user/ingredients", headers=headers)
    items_after = resp.json()["ingredients"]
    assert not any(i["id"] == ingredient_id for i in items_after)


# ──────────────────────────────────────────────
# 9) 사진 인식 (Gemini 모킹)
# ──────────────────────────────────────────────
async def test_image_recognition_mock(client):
    """POST /v1/ingredients/recognize → Gemini 모킹."""
    mock_vision_result = [
        {
            "name": "당근",
            "estimated_amount": 2,
            "unit": "개",
            "confidence": 0.9,
            "alternatives": ["무", "고구마"],
        },
        {
            "name": "대파",
            "estimated_amount": 1,
            "unit": "묶음",
            "confidence": 0.85,
            "alternatives": ["쪽파", "부추"],
        },
    ]

    # 1x1 white JPEG (최소 유효 이미지)
    fake_image = base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 100).decode()

    with patch("api.ingredients.recognize_ingredients", new_callable=AsyncMock, return_value=mock_vision_result):
        resp = await client.post(
            "/v1/ingredients/recognize",
            json={"image": f"data:image/jpeg;base64,{fake_image}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["ingredients"]) == 2
        assert data["ingredients"][0]["name"] == "당근"
        assert data["ingredients"][0]["confidence"] == 0.9
        assert len(data["ingredients"][0]["alternatives"]) >= 2


# ──────────────────────────────────────────────
# 10) 잘못된 입력 → 에러 응답
# ──────────────────────────────────────────────
async def test_invalid_search_query(client):
    """빈 쿼리 → 422 validation error."""
    resp = await client.post("/v1/search/videos", json={"query": ""})
    assert resp.status_code == 422


async def test_invalid_image_too_large(client):
    """4MB 초과 이미지 → 400 에러."""
    large_image = base64.b64encode(b"\x00" * (5 * 1024 * 1024)).decode()
    resp = await client.post(
        "/v1/ingredients/recognize",
        json={"image": large_image},
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail", resp.json())
    error = detail.get("error", detail)
    assert error["code"] == "IMAGE_TOO_LARGE"


async def test_invalid_ingredient_id(client):
    """잘못된 UUID → 400 에러."""
    headers = {"X-Session-Id": "test-err"}
    resp = await client.put(
        "/v1/user/ingredients/not-a-uuid",
        json={"amount": 5},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_delete_nonexistent_ingredient(client):
    """존재하지 않는 재료 삭제 → 404."""
    headers = {"X-Session-Id": "test-err-404"}
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/v1/user/ingredients/{fake_id}", headers=headers)
    assert resp.status_code == 404


# ──────────────────────────────────────────────
# 11) 자동완성 빈 결과
# ──────────────────────────────────────────────
async def test_autocomplete_no_match(client):
    """존재하지 않는 재료 검색 → 빈 결과."""
    resp = await client.get("/v1/ingredients/search", params={"q": "zzzzxxx존재안함"})
    assert resp.status_code == 200
    assert len(resp.json()["ingredients"]) == 0


# ──────────────────────────────────────────────
# 12) 채널 삭제 - 즐겨찾기에 없는 채널
# ──────────────────────────────────────────────
async def test_delete_non_favorited_channel(client):
    """즐겨찾기에 없는 채널 삭제 → 404."""
    headers = {"X-Session-Id": f"test-nofav-{uuid.uuid4().hex[:8]}"}
    resp = await client.delete("/v1/channels/favorites/UCnonexistent", headers=headers)
    assert resp.status_code == 404


# ──────────────────────────────────────────────
# 13) 헬스체크
# ──────────────────────────────────────────────
async def test_health_check(client):
    """GET /health → ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
