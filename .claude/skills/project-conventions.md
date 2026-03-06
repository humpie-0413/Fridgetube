---
name: project-conventions
description: FridgeTube 프로젝트 공통 규칙. 모든 에이전트가 사용.
---

# 공통 규칙

## Python
- ruff 포매팅, type hints 필수, async def 우선
- 에러 응답: `{"error": {"code": "ERR_CODE", "message": "...", "details": {}}}`
- 로깅: `logging.getLogger(__name__)`, print 금지

## TypeScript
- strict mode, fetch만 사용 (axios/SWR 금지)
- Tailwind CSS만, 'use client' 필요 시에만

## API
- prefix: /v1/
- 페이지네이션: cursor + limit
- YouTube API 데이터: 모든 테이블 expires_at 30일

## Gemini
- 모델: gemini-2.0-flash
- 패키지: google-generativeai
- JSON: response_mime_type="application/json"
- 비공식 자막 코드 작성 금지

## 환경변수 (.env.local)
- YOUTUBE_API_KEY
- GEMINI_API_KEY
- DATABASE_URL (Neon)
- REDIS_URL (Upstash)
- SENTRY_DSN
- NEXT_PUBLIC_API_URL (백엔드 URL)
