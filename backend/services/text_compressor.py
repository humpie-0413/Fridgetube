"""설명란/댓글 전처리 — 광고, 링크, 구독 유도, 챕터 타임스탬프 제거.

Gemini에 전달하기 전에 노이즈를 제거하여 토큰 절약 + 추출 정확도 향상.
"""

from __future__ import annotations

import re

# 제거 패턴들
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_HASHTAG_RE = re.compile(r"#\S+")
_TIMESTAMP_LINE_RE = re.compile(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s+.+$", re.MULTILINE)
_SUBSCRIBE_RE = re.compile(
    r"(구독|좋아요|알림|subscribe|like|bell|notification|팔로우|follow)"
    r".*?(눌러|클릭|해주|부탁|please|hit|press|click)",
    re.IGNORECASE,
)
_AD_KEYWORDS_RE = re.compile(
    r"(협찬|광고|제공|sponsored|ad\b|promotion|제휴|affiliate|쿠팡파트너스|내돈내산|PPL)",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_SOCIAL_RE = re.compile(
    r"(인스타|instagram|카카오|네이버|블로그|blog|tiktok|틱톡|twitter|트위터)"
    r"\s*[:：]?\s*\S+",
    re.IGNORECASE,
)
_EMPTY_LINES_RE = re.compile(r"\n{3,}")
_SEPARATOR_RE = re.compile(r"^[-=_*]{3,}\s*$", re.MULTILINE)


def compress(text: str) -> str:
    """설명란/댓글 텍스트에서 노이즈를 제거하고 핵심만 남긴다.

    Args:
        text: 원본 텍스트

    Returns:
        전처리된 텍스트
    """
    if not text:
        return ""

    lines = text.splitlines()
    cleaned_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue

        # 구독 유도 라인 제거
        if _SUBSCRIBE_RE.search(stripped):
            continue

        # 순수 타임스탬프 목차 라인 제거 (00:00 인트로 같은 챕터 목차)
        if _TIMESTAMP_LINE_RE.match(stripped):
            continue

        # 구분선 제거
        if _SEPARATOR_RE.match(stripped):
            continue

        # URL 제거
        stripped = _URL_RE.sub("", stripped)
        # 이메일 제거
        stripped = _EMAIL_RE.sub("", stripped)
        # 해시태그 제거
        stripped = _HASHTAG_RE.sub("", stripped)
        # SNS 계정 제거
        stripped = _SOCIAL_RE.sub("", stripped)

        stripped = stripped.strip()
        if stripped:
            cleaned_lines.append(stripped)

    result = "\n".join(cleaned_lines)
    # 연속 빈 줄 정리
    result = _EMPTY_LINES_RE.sub("\n\n", result)
    return result.strip()


def truncate(text: str, max_chars: int = 4000) -> str:
    """텍스트를 최대 길이로 자르되, 문장 단위로 끊는다."""
    if len(text) <= max_chars:
        return text

    # 마지막 완전한 문장까지 자르기
    truncated = text[:max_chars]
    last_period = max(
        truncated.rfind("."),
        truncated.rfind("다."),
        truncated.rfind("\n"),
    )
    if last_period > max_chars * 0.5:
        return truncated[:last_period + 1]
    return truncated
