---
name: api-spec
description: FridgeTube API 엔드포인트 스펙. Backend와 Frontend 에이전트가 사용.
---

# API 스펙

## 공통
- Base: /v1/
- Content-Type: application/json
- 에러: {"error": {"code": "ERR_CODE", "message": "...", "details": {}}}
- 에러 코드: INVALID_INPUT(400), RATE_LIMITED(403), QUOTA_EXCEEDED(403), NOT_FOUND(404), EXTRACTION_FAILED(422), UPSTREAM_ERROR(502)

## 1. POST /v1/search/videos — 통합 스마트 검색
```json
Request: {
  "query": "김치찌개",
  "user_ingredients": [{"name":"김치","amount":0.5,"unit":"포기"}],
  "servings": 2,
  "mode": "video|recipe",
  "channel_filter": true,
  "sort_by": "relevance|view_count|least_missing",
  "limit": 10, "cursor": null
}
Response: {
  "search_type": "dish_name|ingredients|ambiguous",
  "detected_query": {"dish_name":"김치찌개","cuisine_type":"한식"},
  "videos": [{
    "video_id": "abc123",
    "title": "...", "channel": {"id":"UCxxx","name":"..."},
    "thumbnail": "...", "view_count": 8500000,
    "duration_seconds": 540, "has_cached_recipe": true,
    "ingredient_gap_estimate": {
      "source": "typical_ingredients", "is_estimate": true,
      "estimated_missing": 2, "gap_score": 0.67
    }
  }],
  "next_cursor": "...", "total_estimate": 47
}
```

## 2. GET /v1/ingredients/search?q={query} — 자동완성
```json
Response: {"ingredients": [{"id":"uuid","name":"계란","category":"기타"}]}
```

## 3. POST /v1/recipe/extract — 영상 레시피 추출
```json
Request: {
  "video_id": "abc123", "servings": 2,
  "user_ingredients": [{"name":"계란","amount":6,"unit":"개"}]
}
Response: {
  "recipe": {
    "dish_name": "두부계란찜",
    "base_servings": 4, "base_servings_source": "explicit",
    "requested_servings": 2, "confidence_score": 0.92,
    "ingredients": [{
      "name":"두부", "amount":0.5, "unit":"모",
      "scaling_strategy":"linear",
      "gap_status":"SUFFICIENT",
      "gap_detail": {"user_has":1.0,"recipe_needs":0.5,"shortage":0}
    }],
    "steps": [{"order":1,"text":"...","time_seconds":null}],
    "ingredient_gap_summary": {
      "total":6, "sufficient":2, "missing":1,
      "gap_score":0.83, "verdict":"거의 준비 완료!",
      "shopping_list": [{"name":"참기름","amount":"0.5큰술"}]
    }
  }
}
```

## 4. POST /v1/recipe/parse-text — 외부 텍스트 구조화
```json
Request: {"text": "재료: 돼지고기 300g...", "servings": 2}
Response: (extract와 동일 구조)
```

## 5. POST /v1/ingredients/recognize — 사진 재료 인식
```json
Request: {"image": "data:image/jpeg;base64,..."}
Response: {
  "ingredients": [
    {"name":"계란","quantity":"6개","confidence":0.95,
     "alternatives":["메추리알","오리알"]}
  ]
}
```

## 6. /v1/channels — 선호 채널 CRUD
- GET /v1/channels/search?q=백종원
- POST /v1/channels/favorites {"channel_id":"UCxxx"}
- GET /v1/channels/favorites
- DELETE /v1/channels/favorites/{channel_id}

## 7. /v1/user/ingredients — 보유 재료 CRUD
- GET /v1/user/ingredients
- POST /v1/user/ingredients {"name":"계란","amount":6,"unit":"개"}
- PUT /v1/user/ingredients/{id} {"amount":3}
- DELETE /v1/user/ingredients/{id}

## GAP 상태 5가지
- SUFFICIENT: 보유 & 충분 (✅ 초록)
- PARTIAL: 보유하지만 부족 (⚠️ 노란)
- UNKNOWN_QTY: 보유, 수량 미확인 (🔵 파란)
- MISSING: 미보유 (❌ 빨간)
- BASIC_ASSUMED: 기본 양념 가정 (➖ 회색)

## scaling_strategy 4가지
- linear: 단순 비례 (두부 1모→0.5모)
- stepwise: 정수 반올림 (계란 4개→2개)
- to_taste: 비비례, 맛보며 조절 (소금)
- fixed: 인원수 무관 고정 (식용유 적당량)
