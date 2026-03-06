"""Gemini 2.0 Flash 통합 클라이언트 (텍스트 + 이미지).

google-generativeai 패키지 사용, JSON 강제 출력.
무료 티어 한도(15 RPM, 1500 RPD)를 고려한 재시도 로직 포함.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from config import settings

logger = logging.getLogger(__name__)

# 재시도 설정
MAX_RETRIES = 3
BASE_DELAY = 2.0  # seconds


class GeminiError(Exception):
    pass


class GeminiRateLimited(GeminiError):
    pass


class GeminiClient:
    """Gemini 2.0 Flash 클라이언트."""

    def __init__(self, api_key: str | None = None, model_name: str = "gemini-2.0-flash"):
        key = api_key or settings.gemini_api_key
        if not key:
            raise GeminiError("GEMINI_API_KEY가 설정되지 않았습니다")
        genai.configure(api_key=key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name

    async def generate_json(
        self,
        prompt: str,
        *,
        images: list[Any] | None = None,
    ) -> dict[str, Any]:
        """텍스트(+이미지) → JSON 응답 생성.

        Args:
            prompt: 프롬프트 텍스트
            images: PIL Image 또는 bytes 리스트 (선택)

        Returns:
            파싱된 JSON dict
        """
        contents: list[Any] = []
        if images:
            for img in images:
                contents.append(img)
        contents.append(prompt)

        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
        )

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    contents,
                    generation_config=generation_config,
                )
                import json

                return json.loads(response.text)
            except google_exceptions.ResourceExhausted as e:
                last_error = e
                delay = BASE_DELAY * (2**attempt)
                logger.warning(
                    "Gemini rate limited (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    MAX_RETRIES,
                    delay,
                )
                await asyncio.sleep(delay)
            except google_exceptions.GoogleAPIError as e:
                logger.error("Gemini API error: %s", e)
                raise GeminiError(f"Gemini API 오류: {e}") from e
            except (ValueError, KeyError) as e:
                logger.error("Gemini response parse error: %s", e)
                raise GeminiError(f"Gemini 응답 파싱 실패: {e}") from e

        raise GeminiRateLimited(
            f"Gemini rate limit 초과 ({MAX_RETRIES}회 재시도 실패): {last_error}"
        )

    async def generate_text(self, prompt: str) -> str:
        """텍스트 프롬프트 → 텍스트 응답."""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
            )
            return response.text
        except google_exceptions.GoogleAPIError as e:
            logger.error("Gemini API error: %s", e)
            raise GeminiError(f"Gemini API 오류: {e}") from e
