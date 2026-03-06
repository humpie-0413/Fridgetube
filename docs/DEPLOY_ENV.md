# FridgeTube 배포 환경변수 가이드

## Render (Backend)

| 변수 | 설명 | 예시 |
|------|------|------|
| DATABASE_URL | Neon PostgreSQL 연결 문자열 | postgresql+asyncpg://user:pass@host/db?sslmode=require |
| REDIS_URL | Upstash Redis URL | rediss://default:pass@host:6379 |
| YOUTUBE_API_KEY | YouTube Data API v3 키 | AIza... |
| GEMINI_API_KEY | Google Gemini API 키 | AIza... |
| SENTRY_DSN | Sentry 프로젝트 DSN (선택) | https://xxx@sentry.io/xxx |
| ALLOWED_ORIGINS | CORS 허용 오리진 (쉼표 구분) | https://fridgetube.pages.dev |
| TRANSCRIPT_BETA | 비공식 자막 사용 여부 | false |
| ENVIRONMENT | 실행 환경 | production |

## Cloudflare Pages (Frontend)

| 변수 | 설명 | 예시 |
|------|------|------|
| NEXT_PUBLIC_API_URL | Backend API 주소 | https://fridgetube-api.onrender.com |
| NODE_VERSION | Node.js 버전 | 18 |

## GitHub Actions Secrets

CI/CD와 Nightly 배치에 필요한 시크릿:
- DATABASE_URL
- REDIS_URL
- YOUTUBE_API_KEY
- GEMINI_API_KEY
- SENTRY_DSN

## 보안 주의사항
- NEXT_PUBLIC_ 접두사 변수만 프론트엔드 빌드에 포함됨
- API 키에 절대 NEXT_PUBLIC_ 붙이지 말 것
- .env.local, .env.production에 실제 값 넣지 말 것 (placeholder만)
- git log --all -S "AIza" 로 커밋된 키 확인
