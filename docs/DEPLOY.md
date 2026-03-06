# FridgeTube 배포 가이드

## 아키텍처
- Frontend: Next.js (정적 빌드) → Cloudflare Pages
- Backend: FastAPI (Docker) → Render Free
- DB: PostgreSQL → Neon Free (512MB)
- Cache: Redis → Upstash Free (10K/일)

## 1. Neon PostgreSQL 설정
1. neon.tech 에서 프로젝트 생성
2. Connection string 복사 (postgresql+asyncpg://...)
3. 마이그레이션: `DATABASE_URL=... alembic upgrade head`
4. 시드: `python -m cli.seed_data`

## 2. Upstash Redis 설정
1. upstash.com 에서 Redis 생성
2. Redis URL 복사 (rediss://...)
3. REST URL이 아닌 Redis URL 사용

## 3. Render 배포 (Backend)
1. render.com 계정 + GitHub 리포 연동
2. New Web Service → Docker 선택
3. 환경변수 설정 (DEPLOY_ENV.md 참조)
4. Health Check Path: /health
5. Plan: Free (15분 비활성 시 슬립, RAM 512MB)

## 4. Cloudflare Pages 배포 (Frontend)
1. Cloudflare 대시보드 → Pages → Create project
2. GitHub 연동 → fridgetube 리포 선택
3. Build settings:
   - Build command: `cd frontend && npm ci && npm run build`
   - Build output directory: `frontend/out`
   - Environment variables:
     - NODE_VERSION: 18
     - NEXT_PUBLIC_API_URL: https://fridgetube-api.onrender.com

## 5. GitHub Secrets 설정
Settings > Secrets and variables > Actions 에서 추가:
- DATABASE_URL, REDIS_URL, YOUTUBE_API_KEY, GEMINI_API_KEY, SENTRY_DSN

## 6. Nightly 배치 확인
- .github/workflows/nightly.yml 이 매일 UTC 08:00 (KST 17:00) 실행
- YouTube 쿼터 리셋(PT 00:00) 직후 실행됨
- Actions 탭에서 실행 이력 확인

## Render Free 제약사항
- 15분 무활동 시 인스턴스 슬립 → 첫 요청 30~50초 콜드스타트
- RAM 512MB → Gemini 동시 호출 2~3개 제한
- 월 750시간 무료 (인스턴스 1개 충분)
- 아웃바운드 대역폭 100GB/월

## 트러블슈팅
- CORS 에러: ALLOWED_ORIGINS에 프론트엔드 도메인 추가
- 콜드스타트 느림: 프론트엔드에서 60초 타임아웃 설정됨
- DB 연결 실패: DATABASE_URL에 sslmode=require 확인
- Redis 연결 실패: rediss:// (TLS) URL 사용 확인
- 빌드 실패: NODE_VERSION=18 설정 확인
