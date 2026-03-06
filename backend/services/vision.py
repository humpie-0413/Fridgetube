"""Gemini Vision 기반 식재료 인식 서비스.

사진 → Gemini 2.0 Flash → 재료명 + 수량 + confidence + alternatives
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from services.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

VISION_PROMPT = """이 사진에서 보이는 식재료를 모두 식별해주세요.

각 재료에 대해 다음 정보를 JSON 배열로 반환하세요:
- name: 한국어 재료명 (예: "당근", "대파")
- estimated_amount: 대략적인 수량 (숫자, 확실하지 않으면 null)
- unit: 단위 (예: "개", "묶음", "g", 확실하지 않으면 null)
- confidence: 인식 신뢰도 (0.0~1.0)
  - 신선 채소/과일: 0.7~1.0
  - 가공식품(햄, 어묵 등): 0.5~0.8
  - 양념/소스류: 0.3~0.5 (정확한 종류 판별이 어려움)
  - 포장 제품(라벨 미확인): 0.2~0.4
- alternatives: 혼동될 수 있는 유사 재료 2~3개 (문자열 배열)

규칙:
1. 포장된 제품은 라벨이 보이면 정확히 식별, 아니면 confidence 낮게
2. 양념/소스는 정확한 종류 판별이 어려우므로 confidence 0.3~0.5
3. 가공식품(햄, 어묵, 두부 등)도 포함
4. 최소 1개 이상의 재료를 반환

응답 형식 (반드시 이 JSON 구조를 따라주세요):
{"ingredients": [{"name": "...", "estimated_amount": ..., "unit": "...", "confidence": ..., "alternatives": [...]}]}
"""


async def recognize_ingredients(
    image_bytes: bytes,
    gemini: GeminiClient | None = None,
) -> list[dict[str, Any]]:
    """이미지에서 식재료를 인식한다.

    Args:
        image_bytes: JPEG/PNG 이미지 바이트
        gemini: GeminiClient 인스턴스 (테스트용 주입)

    Returns:
        인식된 재료 리스트
    """
    client = gemini or GeminiClient()

    image_part = {
        "inline_data": {
            "mime_type": "image/jpeg",
            "data": base64.b64encode(image_bytes).decode(),
        }
    }

    result = await client.generate_json(VISION_PROMPT, images=[image_part])

    ingredients = result.get("ingredients", [])

    validated: list[dict[str, Any]] = []
    for ing in ingredients:
        if not ing.get("name"):
            continue
        validated.append({
            "name": str(ing["name"]),
            "estimated_amount": ing.get("estimated_amount"),
            "unit": str(ing["unit"]) if ing.get("unit") else None,
            "confidence": min(max(float(ing.get("confidence", 0.5)), 0.0), 1.0),
            "alternatives": [str(a) for a in ing.get("alternatives", [])],
        })

    return validated
