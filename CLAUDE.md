# FridgeTube

냉장고 재료 → YouTube 인기 레시피 → AI 추출 → 내 상황에 맞게 변환하는 웹앱.

## 스택

| 레이어 | 기술 | 비용 |
|--------|------|------|
| FE | Next.js 14 (App Router) + TypeScript + Tailwind CSS | $0 |
| BE | FastAPI + Python 3.12 + SQLAlchemy + Alembic | $0 |
| DB | PostgreSQL (Neon Free 512MB) + pg_trgm | $0 |
| Cache | Redis (Upstash Free 10K/일) | $0 |
| LLM/Vision | Google Gemini 2.0 Flash (무료 1500RPD) | $0 |
| YouTube | YouTube Data API v3 (10K units/일) | $0 |
| FE 호스팅 | Cloudflare Pages (무제한 대역폭) | $0 |
| BE 호스팅 | Render Free (750h/월) | $0 |
| CI/CD | GitHub Actions (2000분/월) | $0 |

## 디렉토리 구조

```
fridgetube/
├── CLAUDE.md
├── .claude/agents/          # 서브에이전트 정의 (5개)
├── .claude/skills/          # 토큰 절약용 스킬 (4개)
├── frontend/                # Next.js 14
│   ├── src/app/             # App Router 페이지
│   ├── src/components/      # 재사용 컴포넌트
│   ├── src/lib/             # API 호출, 유틸
│   └── public/              # 정적 파일 + PWA manifest
├── backend/
│   ├── api/                 # FastAPI 라우터
│   ├── services/            # 비즈니스 로직
│   ├── models/              # SQLAlchemy 모델
│   ├── seeds/               # 시드 데이터 JSON
│   ├── cli/                 # 배치 CLI 명령
│   └── tests/               # pytest
├── docs/                    # 파이프라인, 가이드
├── docker-compose.yml
├── .env.example
└── .github/workflows/ci.yml
```

## 실행 계획 — 8 스테이지, 60 태스크

이 프로젝트는 아래 스테이지를 **순서대로** 실행합니다.
각 스테이지는 독립적이므로 중간에 끊겨도 다음 태스크부터 재개 가능합니다.
**반드시 스테이지 순서를 지키세요. 스테이지를 건너뛰지 마세요.**

### Stage 0: 프로젝트 초기화
1. `frontend/`: Next.js 14 + TypeScript + Tailwind CSS 초기화 (`npx create-next-app@latest`)
2. `backend/`: FastAPI + Python 3.12 프로젝트 초기화 (requirements.txt 또는 pyproject.toml)
3. `docker-compose.yml`: PostgreSQL 16 + Redis 7 (로컬 개발용)
4. `.env.example` → `.env.local` 복사 안내
5. ESLint + Prettier (FE) + Ruff (BE) 설정
6. PWA 기본 설정: `frontend/public/manifest.json` + `frontend/src/app/layout.tsx`에 meta 태그
7. **검증:** `docker compose up` → FE(3000) + BE(8000) + PG(5432) + Redis(6379) 접속

### Stage 1: 데이터베이스 + 시드 데이터
1. SQLAlchemy 모델: users, youtube_channels, user_favorite_channels
2. SQLAlchemy 모델: ingredient_master, dish_name_master (pg_trgm, typical_ingredient_ids UUID[])
3. SQLAlchemy 모델: channel_video_index (tsvector, expires_at 30일), youtube_video_snapshot (30일 TTL)
4. SQLAlchemy 모델: recipe_core (prompt_version, base_servings_source), recipe_core_ingredients (scaling_strategy)
5. SQLAlchemy 모델: user_ingredients, search_history, saved_recipes
6. Alembic 초기 migration + pg_trgm 확장 활성화
7. 시드 데이터: ingredient_master 100개 한국 식재료 (JSON → DB 로딩 스크립트)
8. 시드 데이터: dish_name_master 300개 (한중양일) + typical_ingredient_ids 매핑
9. 인덱스 생성: tsvector GIN, pg_trgm GIN, expires_at 등 (docs/PIPELINE.md 인덱스 전략 참조)
10. **검증:** `psql` → 전체 테이블 + 시드 카운트 + "김치찌개" 쿼리 테스트

### Stage 2: YouTube 채널 인덱싱 서비스
1. `backend/services/youtube_client.py`: YouTube API 래퍼 (channels, playlistItems, videos, commentThreads)
2. `backend/services/channel_index.py`: playlistItems → channel_video_index 저장 + tsvector + expires_at
3. `backend/services/quota_budgeter.py`: Redis 기반 쿼터 카운터 (Pacific Time 자정 리셋)
4. `backend/cli/index_channels.py`: 배치 인덱싱 CLI
5. `backend/seeds/curated_channels.json`: 큐레이션 채널 20개 + 인덱싱 실행
6. `backend/services/local_search.py`: tsvector + pg_trgm 한국어 퍼지 검색
7. 만료 데이터 정리: expires_at < now() 삭제 로직
8. **검증:** "김치찌개" 로컬 검색 → 5개+ 결과. "김치찌게"(오타) → pg_trgm 매칭

### Stage 3: 검색 API + Query Classifier
1. `backend/services/query_classifier.py`: 규칙 기반 (재료/요리명/모호 판별)
2. `backend/services/reverse_recipe.py`: 재료 → 후보 요리 top-k (typical_ingredient_ids 역조회)
3. `backend/services/ingredient_gap.py`: typical_ingredients 기반 예상 GAP (런타임 계산)
4. `backend/api/search.py`: POST /v1/search/videos (로컬 우선 + search.list fallback)
5. `backend/api/ingredients.py`: GET /v1/ingredients/search?q= (자동완성)
6. **검증:** curl POST /v1/search/videos {query: "김치찌개"} → 결과 + 예상 GAP

### Stage 4: 레시피 추출 (Gemini)
1. `backend/services/gemini_client.py`: Gemini 2.0 Flash 텍스트+이미지 통합 클라이언트
2. `backend/services/text_compressor.py`: 설명란/댓글 전처리 (광고/링크 제거)
3. `backend/services/author_comment.py`: commentThreads + authorChannelId 필터
4. `backend/services/transcript.py`: 설명란 → 작성자 댓글 → Flow D 안내 (3단계 정식 경로)
5. `backend/services/recipe_extract.py`: Gemini 프롬프트 → JSON 파싱 (scaling_strategy 포함)
6. `backend/services/recipe_transform.py`: scaling_strategy 기반 분량 조절
7. `backend/api/recipe.py`: POST /v1/recipe/extract + POST /v1/recipe/parse-text
8. **검증:** 영상 ID → Gemini 추출 → 2인분 변환 → GAP 분석 E2E. 응답 < 15초

### Stage 5: 사진 인식 + 부가 API
1. `backend/services/vision.py`: Gemini 이미지 인식 (재료 + 유사 후보)
2. `backend/api/ingredients.py`에 POST /v1/ingredients/recognize 추가
3. `backend/api/channels.py`: GET/POST/DELETE /v1/channels (선호 채널 CRUD)
4. `backend/api/user_ingredients.py`: 보유 재료 CRUD
5. `backend/tests/`: 전체 API 통합 테스트 (핵심 시나리오 10개)
6. **검증:** Swagger UI 전체 API 동작 + pytest 통과

### Stage 6: 프론트엔드 UI
1. 공통 레이아웃 + 라우팅 + 디자인 토큰 + PWA 서비스 워커
2. S01: 홈/통합 검색 (태그 입력 + 자동완성 + 인원수 슬라이더 + 모드 토글)
3. S02: 검색 결과 (2탭: "내 채널 추천" [GAP 뱃지] / "YouTube 검색" [수정 금지])
4. S03: 레시피 상세 (영상 임베드 + 원본/변환 탭 + GAP 체크리스트 + 인원수)
5. S04: 채널 관리 (검색 + 추가/삭제)
6. S05: 사진 인식 모달 (업로드 → 인식 → 유사 후보 드롭다운 → 양념 체크)
7. S06: 외부 레시피 텍스트 입력 모달
8. 에러/로딩/빈 상태 UI + 반응형 (모바일 360px~)
9. PWA 마무리: 오프라인 폴백, 설치 프롬프트, 앱 아이콘
10. **검증:** "김치찌개" 검색 → 결과 → 레시피 추출 → GAP E2E 플로우

### Stage 7: 배포 + 안정화
1. Neon Free PostgreSQL 생성 + 마이그레이션
2. Upstash Redis 생성 + 연동
3. 시드 데이터 + 채널 인덱싱 클라우드 실행
4. FastAPI → Render Free 배포
5. Next.js → Cloudflare Pages 배포
6. 환경변수 + CORS 설정
7. GitHub Actions CI/CD
8. Sentry 연동
9. 최종 E2E 테스트 (프로덕션)
10. **검증:** fridgetube.pages.dev 접속 → 검색 → 레시피 → GAP 확인 🚀

## 코딩 규칙

### Python (Backend)
- ruff 포매팅 + type hints 필수
- async def 우선 (SQLAlchemy async session)
- 에러: `{"error": {"code": "ERR_CODE", "message": "...", "details": {}}}`
- 로깅: `import logging; logger = logging.getLogger(__name__)`
- print() 프로덕션 금지

### TypeScript (Frontend)
- strict mode
- fetch 사용 (axios, SWR, React Query 금지 — 의존성 최소화)
- 컴포넌트: function 컴포넌트 + hooks
- 스타일: Tailwind CSS만 (CSS modules 금지)
- `'use client'` 필요한 곳에만

### API 규칙
- Base: `/v1/`
- 인증: Bearer JWT (비회원은 세션 토큰). MVP에서는 인증 미구현 OK
- 페이지네이션: `?cursor=&limit=`
- YouTube API 데이터: 모든 테이블에 `expires_at` (30일 TTL)
- search.list 결과: 별도 탭, 원본 순서 유지, 재정렬/뱃지 금지

### Gemini 규칙
- 모델: `gemini-2.0-flash`
- 패키지: `google-generativeai`
- JSON 강제: `generation_config={"response_mime_type": "application/json"}`
- 프롬프트: 한국어
- 비공식 자막 (youtube-transcript-api): 프로덕션 OFF. 코드 작성 금지

### PWA 규칙
- `manifest.json`: name, short_name, icons, start_url, display: standalone, theme_color
- 서비스 워커: next-pwa 또는 수동 등록. 오프라인 폴백 페이지
- meta viewport: `width=device-width, initial-scale=1, maximum-scale=1`

## DB 규칙 (YouTube Developer Policies 준수)
- YouTube API 데이터가 저장되는 **모든 테이블**에 `expires_at` (indexed_at + 30일)
- Nightly 배치에서 `DELETE WHERE expires_at < NOW()` 실행
- `recipe_core`(추출 레시피, 장기 보관)와 `youtube_video_snapshot`(YouTube 메타, 30일 TTL) 분리
- search.list 결과: UI에서 별도 탭, 원본 순서 유지, 재정렬/뱃지 오버레이 금지
- 파생 지표(조회수/좋아요 가중합 점수 등) 생성 금지
- FridgeTube 자체 분석(GAP 등): "YouTube 제공 아님" UI 표기

## 토큰 절약
- `.claude/skills/`의 스킬을 사전 로딩하여 파일 탐색 최소화
- 각 스테이지를 **별도 세션**으로 실행 (컨텍스트 리셋)
- 긴 세션에서 `/compact` 주기적 실행
- 서브에이전트 결과는 **요약만** 반환

## 차후 개발 (Phase 2~3)

### Phase 2 (MVP 출시 후)
- 사용자 인증 (Google/Kakao OAuth)
- 레시피 저장/히스토리
- OCR 레시피북 사진 → 구조화
- URL 입력 → 웹 레시피 스크래핑
- 대체 재료 AI 추천
- 채널 자동 인덱싱 확장

### Phase 3 (성장기)
- 프리미엄 구독 (₩2,900/월)
- 장보기 연동 (쿠팡/마켓컬리 affiliate)
- 레시피 비교 분석
- 맛 프로필 시스템
- React Native 또는 Capacitor 네이티브 앱 래핑
- 자체 ASR (Whisper) — 비공식 자막 대체
