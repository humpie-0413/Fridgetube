# FridgeTube — 실행 가능 계획 파이프라인 v3.0

> **작성일:** 2026-03-06  
> **작성자:** 성민재 (PM/Tech Lead)  
> **상태:** $0 MVP + Claude Code 에이전트 실행 계획

### v3.0 변경 로그 (무료 스택 전환 + Claude Code 에이전트 대응)
| 변경 | 내용 |
|------|------|
| **스택 전환** | LLM: Claude API($50+/월) → **Google Gemini 2.0 Flash 무료 티어**($0). Vision도 Gemini로 통합 |
| **호스팅 전환** | Vercel(상업 시 $20/월) → **Cloudflare Pages**($0, 상업 사용 무료). 백엔드: **Render Free**(750h/월) |
| **DB 전환** | Supabase Free 유지 (대안: Neon Free). 500MB 범위 내 운영 |
| **WBS 전면 개편** | 8주 → **Claude Code 에이전트팀용 30개 마이크로 태스크**로 세분화. 각 태스크는 독립 실행 가능 + 중간 체크포인트 포함 |
| **월 비용** | ~$50~200 → **$0/월** (무료 티어 조합) |

### v2.2 변경 로그
| 피드백 ID | 변경 내용 |
|----------|----------|
| P0-1 | Flow A LLM 제거 → typical_ingredients 기반 예상 GAP |
| P0-2 | Transcript 경로 재정렬 (설명란 → 자동자막 → 고정댓글 Phase 2) |
| P0-3 | DB 정합성 4건 수정 (search_history, recipe_cache UNIQUE, channel_id, user_ingredients) |
| P0-4 | GAP 런타임 계산 전환 |
| P1-1~3 | dish_name 300~500개, estimated_cost 제거, trigram Phase 2 |

---

## 0. 신규 아이디어 기술 검토

### 아이디어 ① 선호 유튜버 레시피만 추천

| 항목 | 분석 |
|------|------|
| **실현 가능성** | ✅ **높음** — YouTube Data API v3의 `channelId` 파라미터로 특정 채널 내 검색이 가능. 사용자가 즐겨찾는 채널 ID를 저장해두면 해당 채널의 영상만 필터링하여 검색 가능 |
| **기술 구현** | `GET /youtube/v3/search?channelId={id}&q={재료}&type=video` → 채널별 필터링 검색. 사용자 프로필에 `favorite_channels[]` 배열 저장 |
| **핵심 과제** | 채널 검색/추가 UX 설계 (채널명 자동완성), 채널별 자막 품질 편차 대응, 채널이 삭제/비공개 전환 시 fallback |
| **수익 연계** | 유튜버 공식 제휴 모델의 기반 — 프리미엄 채널 등록 시 우선 노출 수수료 |
| **우선순위** | **P0 (MVP)** — 구현 난이도 낮고 차별화 효과 큼 |

### 아이디어 ② 재료 사진 → 수량 측정

| 항목 | 분석 |
|------|------|
| **실현 가능성** | ⚠️ **중간** — Vision AI(Gemini 2.0 Flash)로 재료 "종류" 인식은 높은 정확도 달성 가능. 그러나 "수량/무게" 추정은 기술적 난이도가 높음 |
| **기술 구현** | 2단계 접근: (1) Vision AI로 재료 식별 + 개수 카운팅 (예: 계란 3개, 당근 2개) → 정확도 85~95%. (2) 무게 추정은 참조 객체(손, 접시) 기반 상대 크기 추정 → 정확도 60~75% |
| **핵심 과제** | 겹쳐 있는 재료 분리 인식, 비정형 재료(양념/소스 등) 수량 추정 불가, 조명/각도에 따른 정확도 편차. "대략적 추정 + 사용자 보정" UI가 현실적 |
| **현실적 스코프** | MVP에서는 **재료 종류 인식 + 대략적 수량(많음/보통/적음)** 으로 제한. 정확한 g 단위 측정은 Phase 3에서 검토 |
| **우선순위** | **P1** — 종류 인식은 MVP, 수량 추정은 Phase 2~3 |

**가정:** Vision AI 비용은 1회 호출당 약 $0.01~0.03. 하루 1만 건 기준 월 $300~900.  
**가정 변경 시 영향:** 비용이 2배 이상이면 무료 사용자 사진 인식 횟수를 하루 3회로 제한 필요.

### 아이디어 ③ 레시피북/외부 레시피 입력

| 항목 | 분석 |
|------|------|
| **실현 가능성** | ✅ **높음** — 여러 방식으로 접근 가능 |
| **입력 방식 A: 사진/스캔** | 레시피북 페이지 촬영 → OCR(Tesseract/Google Vision) → LLM 구조화. 한글 OCR 정확도 90%+ |
| **입력 방식 B: 텍스트 붙여넣기** | 블로그/웹사이트 레시피 복사 → LLM이 재료/순서 자동 파싱 |
| **입력 방식 C: URL 입력** | 만개의레시피, 네이버 블로그 등 URL → 웹 스크래핑 → LLM 구조화 |
| **핵심 과제** | OCR 후처리 (수기 메모 인식 한계), 다양한 레시피 포맷 대응, 저작권 이슈 (원본 레시피 재배포 vs 개인 사용) |
| **차별화 효과** | YouTube 종속성 탈피 → "모든 레시피의 허브" 포지셔닝. 사용자 자체 레시피 라이브러리 구축 가능 |
| **우선순위** | **P1** — 텍스트 입력은 MVP, 사진/URL은 Phase 2 |

---

## 1. 목표/범위 정의

### 프로젝트 정보

| 항목 | 내용 |
|------|------|
| **개요** | 냉장고 재료를 입력하면 YouTube 인기 요리 영상에서 AI가 레시피를 추출하고, 사용자 상황(인원수, 보유재료, 선호 유튜버)에 맞게 변환해 보여주는 웹 플랫폼 |
| **대상** | 20~40대 자취생/맞벌이 부부/요리 입문자 (한국 시장 우선) |
| **핵심 가치** | "냉장고를 열면 요리가 시작된다" — 재료 낭비 감소, 메뉴 결정 스트레스 해소, 검증된 인기 레시피로 실패 확률 최소화 |
| **스택** | Next.js 14 (App Router) + TypeScript / FastAPI (Python) / PostgreSQL (Neon Free) + Redis (Upstash Free) / **Cloudflare Pages + Render Free** / **Google Gemini 2.0 Flash (무료)** |
| **월 비용** | **$0** (전체 무료 티어 조합) |
| **현재 상태** | 기획 단계 완료, 개발 미착수 |

### MVP vs 이후 범위

```
┌─────────────────────────────────────────────────────────┐
│  MVP (Phase 1: ~8주)                                     │
│                                                          │
│  ✅ 재료 텍스트 입력 + 카테고리 선택                        │
│  ✅ YouTube 영상 검색 + 인기도 정렬                         │
│  ✅ AI 자막 기반 레시피 추출                                │
│  ✅ 영상 추천 모드 + 레시피 변환 모드                        │
│  ✅ 인원수 설정 + 분량 자동 조절                            │
│  ✅ 선호 유튜버 등록 + 채널 필터링 검색         ← NEW       │
│  ✅ 외부 레시피 텍스트 붙여넣기 → 구조화        ← NEW       │
│  ✅ 재료 사진 → 종류 인식 (수량은 대략적)       ← NEW       │
├─────────────────────────────────────────────────────────┤
│  Phase 2 (~12주 누적)                                    │
│                                                          │
│  🔲 재료 사진 → 정밀 수량 추정                              │
│  🔲 레시피북 사진 OCR → 구조화                              │
│  🔲 URL 입력 → 웹 레시피 스크래핑                           │
│  🔲 대체 재료 AI 추천                                      │
│  🔲 레시피 캐싱 DB + 검색 최적화                            │
│  🔲 사용자 계정 + 레시피 저장/히스토리                       │
├─────────────────────────────────────────────────────────┤
│  Phase 3 (~24주 누적)                                    │
│                                                          │
│  🔲 프리미엄 구독 결제                                      │
│  🔲 장보기 연동 (쿠팡/마켓컬리)                             │
│  🔲 레시피 비교 분석 (같은 요리 다른 유튜버)                  │
│  🔲 맛 프로필 시스템                                        │
│  🔲 유튜버 채널 공식 제휴                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 사용자 스토리 + 우선순위 (MoSCoW)

### Must Have (MVP 필수)

| ID | 사용자 스토리 | 인수 조건 |
|----|-------------|----------|
| US-01 | 사용자로서, 냉장고에 있는 재료를 텍스트로 입력하면 관련 YouTube 요리 영상을 보고 싶다 | 재료 1개 이상 입력 시 관련 영상 5~20개 인기도순 표시 |
| US-02 | 사용자로서, 인원수를 설정하면 레시피 분량이 자동 조절되길 원한다 | 1~10인분 슬라이더, 재료별 분량 비례/비비례 구분 표시 |
| US-03 | 사용자로서, 영상에서 추출된 구조화 레시피를 카드 형태로 보고 싶다 | 요리명, 재료목록, 조리순서, 예상시간, 난이도 표시 |
| US-04 | 사용자로서, "영상만 보기" 또는 "레시피 변환" 모드를 선택하고 싶다 | 토글 스위치로 모드 전환, 각 모드별 최적화 UI |
| US-05 | 사용자로서, 좋아하는 유튜버를 등록하면 그 채널의 레시피만 추천받고 싶다 | 채널 검색/추가/삭제 UI, 필터 ON/OFF 토글 |
| US-06 | 사용자로서, 냉장고 사진을 찍으면 재료를 자동으로 인식하고 싶다 | 사진 업로드 → 재료 태그 자동 생성 → 사용자 수정 가능 |
| US-07 | 사용자로서, 레시피북이나 블로그의 레시피 텍스트를 붙여넣으면 구조화해서 보고 싶다 | 자유 텍스트 입력 → JSON 구조화 → 레시피 카드 표시 |

### Should Have (Phase 2)

| ID | 사용자 스토리 | 인수 조건 |
|----|-------------|----------|
| US-08 | 사용자로서, 재료 사진에서 대략적인 양(g, 개수)도 파악되길 원한다 | 사진 내 참조 객체 기반 추정, 사용자 보정 UI |
| US-09 | 사용자로서, 레시피북 페이지를 사진으로 찍으면 레시피로 변환되길 원한다 | OCR → LLM 구조화, 한글 인식률 90%+ |
| US-10 | 사용자로서, 레시피 URL을 입력하면 자동으로 레시피를 가져오고 싶다 | 만개의레시피, 네이버 블로그 등 주요 사이트 지원 |
| US-11 | 사용자로서, 없는 재료의 대체재를 AI가 추천해주길 원한다 | 대체 재료 + 맛 변화 설명 표시 |
| US-12 | 사용자로서, 변환한 레시피를 저장하고 나중에 다시 보고 싶다 | 회원가입/로그인, 레시피 저장소, 검색 |

### Could Have (Phase 3)

| ID | 사용자 스토리 |
|----|-------------|
| US-13 | 같은 요리의 여러 유튜버 레시피를 비교해서 보고 싶다 |
| US-14 | 부족한 재료를 쿠팡/마켓컬리에서 바로 주문하고 싶다 |
| US-15 | 내 맛 프로필(매운맛 선호 등)에 맞는 레시피를 우선 추천받고 싶다 |
| US-16 | 프리미엄 구독으로 무제한 변환, 광고 제거를 이용하고 싶다 |

### Won't Have (이번 프로젝트 범위 외)

- 자체 레시피 커뮤니티/댓글 시스템
- 실시간 요리 코칭 (영상 통화)
- 식단/칼로리 관리 기능
- 네이티브 모바일 앱 (PWA로 대체)

---

## 3. 시스템 아키텍처 + 데이터 흐름

### 3.1 아키텍처 개요

```
┌──────────────────────────────────────────────────────────────┐
│                   CLIENT (Next.js 14 on Cloudflare Pages)     │
│                   ★ 무료: 무제한 대역폭, 상업 사용 가능         │
│                                                               │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐ │
│  │통합 검색  │ │ 사진업로드 │ │ 채널관리  │ │ 레시피텍스트입력   │ │
│  │(재료/요리)│ │   UI     │ │   UI     │ │      UI          │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬──────────────┘ │
│       └────────────┴────────────┴─────────────┘               │
│                         │ REST API                            │
└─────────────────────────┼────────────────────────────────────┘
                          │
┌─────────────────────────┼────────────────────────────────────┐
│                    API GATEWAY (FastAPI on Render Free)        │
│                    ★ 무료: 750h/월, 콜드스타트 ~30초            │
│                         │                                     │
│  ┌──────────────────────┼──────────────────────────────────┐  │
│  │                  Core Services                           │  │
│  │                                                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │  │
│  │  │  Query      │  │  Channel   │  │  Recipe Extract    │ │  │
│  │  │ Classifier  │  │  Index     │  │  Service (Gemini)     │ │  │
│  │  │             │  │  Service ★ │  │                    │ │  │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────────────┘ │  │
│  │        │               │               │                 │  │
│  │  ┌─────┴──────┐  ┌─────┴──────┐  ┌─────┴──────────────┐ │  │
│  │  │ Ingredient │  │ Transcript │  │  Recipe Transform  │ │  │
│  │  │  Service   │  │  Service   │  │  Service (Gemini)     │ │  │
│  │  └────────────┘  └────────────┘  └────────────────────┘ │  │
│  │        │               │               │                 │  │
│  │  ┌─────┴──────┐  ┌─────┴──────┐  ┌─────┴──────────────┐ │  │
│  │  │  Vision    │  │  Quota     │  │  Ingredient Gap    │ │  │
│  │  │  Service   │  │ Budgeter ★ │  │  Service           │ │  │
│  │  └────────────┘  └────────────┘  └────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────┬──────────────┬──────────────┬────────────────────────┘
        │              │              │
   ┌────┴────┐   ┌─────┴─────┐  ┌────┴────────────────────┐
   │Neon Free │   │ Upstash   │  │    External APIs (무료)  │
   │PostgreSQL│   │Redis Free │  │                         │
   │ 512MB    │   │ 10K/일    │  │ YouTube Data API v3     │
   │ users   │   │ yt_cache  │  │  - playlistItems (1u)   │
   │ channels│   │ recipe_   │  │  - videos.list (1u)     │
   │ recipes │   │   cache   │  │  - search.list (100u)★  │
   │ ingredi-│   │ rate_     │  │  - commentThreads (1u)  │
   │  ents   │   │   limits  │  │ Gemini 2.0 Flash (무료)  │
   │ dish_   │   │ quota_    │  │  - 텍스트 추출 (1500RPD)│
   │  names  │   │  budget   │  │  - 이미지 인식 (동일)    │
   │ channel │   │           │  │                         │
   │  _index │   │           │  │                         │
   └─────────┘   └───────────┘  └─────────────────────────┘

★ v3.0: 전체 $0/월 — Gemini 무료 + Cloudflare + Render + Neon + Upstash
```

### 3.2 핵심 데이터 흐름

#### Flow A: 통합 스마트 검색 (채널 인덱스 기반 ★v2.3)

**v2.3 핵심 변경:** search.list(100 units/회) 의존을 제거하고, **채널 인덱싱 기반 로컬 검색**을 MVP 코어로 전환합니다.

**YouTube API 쿼터 현실:**
- 기본 할당: 10,000 units/day/project
- search.list: **100 units/회** → 하루 최대 100회 검색 (MVP 50명이면 1인 2회로 끝)
- playlistItems.list: **1 unit/회** → 하루 10,000회 가능
- videos.list: **1 unit/회** → 하루 10,000회 가능

```
사용자 입력 (단일 필드)
    │
    ▼
[Query Classifier] 입력 의도 자동 판별 (규칙 기반, v2.1과 동일)
    │
    ├─── [재료 모드] "계란, 파, 두부"
    │        │
    │        ▼
    │    [Ingredient Service] 재료명 정규화
    │        │
    │        ▼
    │    ★ [역방향 요리명 추론] ← v2.3 신규
    │        │  typical_ingredient_ids 역조회:
    │        │  "계란 + 파 + 두부" 매칭 → ["두부계란찜","파전","계란볶음밥"...]
    │        │  매칭률 높은 상위 5~10개 후보 요리명
    │        │
    │        ▼
    │    [Channel Index Service] 로컬 DB 검색 (쿼터 소모 0)
    │        │  인덱싱된 채널 영상 중 후보 요리명 매칭
    │        │  PostgreSQL Full-Text Search (제목 + 설명란)
    │        │
    │        ├── 결과 충분 (5개+) → 바로 반환
    │        │
    │        └── 결과 부족 (<5개) + 쿼터 여유 시
    │              │
    │              ▼
    │           [Quota Budgeter] 일일 잔여 쿼터 확인
    │              │  ⚠️ 리셋 기준: Pacific Time 자정 (KST 아님) ← v2.4
    │              │  잔여 > 2000 units → search.list 1회 허용
    │              │  잔여 ≤ 2000 units → 로컬 결과만 반환 + "더 찾기" 비활성
    │              │
    │              ▼
    │           [YouTube search.list] 보조 검색 (100 units)
    │              │  query: "계란 파 두부 요리 레시피"
    │              │
    │              ▼
    │           [videos.list 배치] 상세 정보 (1 unit/요청, 최대 50개 배치)
    │              │  duration, view_count, like_count 보충
    │              │
    │              ▼
    │           ⚠️ [Client] search.list 결과는 **별도 탭**으로 분리 표시 (v2.4 정책)
    │              │  "YouTube 검색 결과" 탭: 원본 순서 유지, 재정렬 금지
    │              │  GAP 뱃지/오버레이 불가 (정책: 검색 결과 수정 금지)
    │              │  GAP 분석은 영상 클릭 후 Flow B에서만 제공
    │
    │
    └─── [요리명 모드] "김치찌개" / "까르보나라 파스타"
             │
             ▼
         [Channel Index Service] 로컬 DB 검색 (쿼터 소모 0)
             │  인덱싱된 채널 영상 중 요리명 매칭
             │  → 결과 있으면 바로 반환
             │
             ├── 결과 충분 → typical_ingredients 기반 예상 GAP 계산
             │
             └── 결과 부족 + 쿼터 여유 → search.list 보조 (별도 탭 분리)
             │
             ▼
         [Ingredient Gap Service] 예상 GAP (typical_ingredients 기반)
             │  LLM 미사용, DB 배열 비교, <5ms
             │  ⚠️ GAP 뱃지는 **로컬 인덱스 결과에만** 표시 가능
             │  ⚠️ search.list 결과 탭에서는 GAP 뱃지/정렬 금지
             │
             ▼
         [Client] 2개 탭 구조 (v2.4 정책 준수)
             │
             │  [탭 1: "내 채널 추천" (기본 활성)]
             │  - 로컬 인덱스 결과 (FridgeTube 자체 데이터)
             │  - "~2개 부족" GAP 뱃지 표시 가능
             │  - 정렬: 인기순 / 예상 부족 적은 순 (자유)
             │  - "FridgeTube 분석" 영역으로 GAP 분리 + "YouTube 제공 아님" 표기
             │
             │  [탭 2: "YouTube 검색 결과" (보조, search.list 사용 시만 표시)]
             │  - YouTube API 원본 순서 그대로, 재정렬 금지
             │  - GAP 뱃지/오버레이 없음
             │  - 카드 클릭 → Flow B에서 GAP 확인 가능
             │  - "YouTube 검색 결과입니다" 고지
```

**채널 인덱싱 프로세스 (백그라운드):**

```
[Channel Index Service] — Nightly Batch (17:00 KST = 00:00 PT, 쿼터 리셋 직후)
    │
    │  대상: 인덱싱 등록된 채널 (MVP: 큐레이션 20~30채널 + 사용자 선호 채널)
    │
    │  Step 1: channels.list → uploads playlist ID (1 unit/채널)
    │  Step 2: playlistItems.list → 최신 영상 목록 (1 unit/페이지, 50개/페이지)
    │           채널당 최근 200개 = 4 units
    │  Step 3: videos.list 배치 → 제목/설명란/통계 (1 unit/요청, 최대 50개/배치)
    │           200개 영상 = 4 units (4 배치 × 50개)
    │  Step 4: 로컬 DB 저장 (channel_video_index 테이블)
    │           제목 + 설명란 텍스트 → PostgreSQL tsvector 인덱싱
    │           expires_at = NOW() + 30일 (갱신) ← v2.4
    │  Step 5: youtube_video_snapshot 갱신 (같은 데이터로)
    │           expires_at = NOW() + 30일 (갱신)
    │  Step 6: 만료 데이터 정리 (v2.4 정책 준수)
    │           DELETE FROM channel_video_index WHERE expires_at < NOW()
    │           DELETE FROM youtube_video_snapshot WHERE expires_at < NOW()
    │
    │  예상 쿼터 소모:
    │  30채널 × (1 + 4 + 4) units = ~270 units/일
    │  → 일일 쿼터 10,000의 2.7%만 사용
```

**쿼터 예산 배분 (Pacific Time 기준 일일):**

| 용도 | 일일 할당 (units) | 비율 |
|------|-------------------|------|
| 채널 인덱싱 배치 | ~300 | 3% |
| videos.list 통계 refresh | ~500 | 5% |
| commentThreads.list (작성자 댓글) ← v2.4 | ~200 | 2% |
| 사용자 search.list (보조) | ~2,000 | 20% |
| 여유/긴급 | ~7,000 | 70% |
| **합계** | 10,000 | 100% |
```

**요리명 판별 예시:**

| 입력 | 판별 결과 | 근거 |
|------|----------|------|
| "계란, 파, 두부" | 재료 모드 | 쉼표 구분 + ingredient_master 일치 |
| "김치찌개" | 요리명 모드 | "OO찌개" 패턴 매칭 |
| "까르보나라 파스타" | 요리명 모드 | "OO파스타" 패턴 매칭 |
| "마파두부" | 요리명 모드 | dish_name DB 일치 |
| "탕수육" | 요리명 모드 | dish_name DB 일치 |
| "닭" | 재료 모드 | ingredient_master 일치 (단일 재료) |
| "닭볶음탕" | 요리명 모드 | "OO탕" 패턴 매칭 |
| "파스타" | 양쪽 모두 | 재료이기도 하고 요리 카테고리이기도 함 → 양쪽 결과 탭 표시 |

**가정:** dish_name DB에 한/중/양/일식 주요 요리명 300~500개 사전 등록 (MVP). 운영 로그 기반 주간 100개씩 확장.
**가정 변경 시 영향:** DB가 부실하면 요리명 인식률 하락 → LLM 기반 의도 분류로 전환 필요 (응답 지연 +0.5초, 비용 +$0.001/건)

#### Flow B: 영상 선택 → 레시피 추출/변환/GAP (★v2.3 자막 경로 재구성)

```
사용자가 영상 카드 클릭 (레시피 변환 모드)
    │
    ▼
[Transcript Service] 텍스트 확보 — 3단계 정식 경로 (v2.4)
    │
    │  ┌─────────────────────────────────────────────────────┐
    │  │ 🟢 정식 경로 (Compliance-safe, 항상 활성)            │
    │  │                                                      │
    │  │ 1순위: 설명란 텍스트 (YouTube Data API — 공식, 0 unit)│
    │  │   → snippets.description에서 레시피 패턴 탐지         │
    │  │   → 이미 인덱싱 시 저장됨, 추가 API 호출 불필요       │
    │  │                                                      │
    │  │ 2순위: 작성자 댓글 탐지 (공식 API) ★ v2.4 MVP 승격   │
    │  │   → commentThreads.list(order=relevance, 1 unit)     │
    │  │   → comment.authorChannelId == 영상 업로더 채널 ID    │
    │  │     로 필터 → "작성자 댓글" 중 레시피 패턴 탐지       │
    │  │   → 작성자가 댓글에 레시피를 적는 비율: ~20~30%       │
    │  │   → 설명란과 합산하면 자동 추출 커버리지: ~50~60%     │
    │  │                                                      │
    │  │ 3순위: Flow D 경로 안내                               │
    │  │   → 위 경로 모두 실패 시: "영상을 보고 레시피를       │
    │  │     직접 입력해보세요" + 텍스트 입력 모달 열기          │
    │  │   → 사용자 입력 데이터는 recipe_core에 캐싱            │
    │  ├──────────────────────────────────────────────────────┤
    │  │ ⛔ 비공식 경로 (프로덕션 OFF — v2.4 확정)             │
    │  │                                                      │
    │  │ 자동생성 자막 (youtube-transcript-api)                │
    │  │   → 환경변수: TRANSCRIPT_BETA=false (프로덕션 기본값) │
    │  │   → 개발/스테이징 환경에서만 테스트 가능              │
    │  │   → YouTube Developer Policies "스크래핑 금지" 조항   │
    │  │     위반 가능성으로 프로덕션 사용 불가 판단            │
    │  │   → 향후 자체 ASR(Whisper) 확보 시 코드 제거 예정     │
    │  │   → 프로덕션에서 한 번도 사용하지 않았음을 감사 시    │
    │  │     입증 가능한 구조 (환경변수 + 배포 로그)            │
    │  └─────────────────────────────────────────────────────┘
    │
    ▼
★ [Text Compressor] 텍스트 전처리 (v2.3 → v2.4 명칭 변경)
    │  목적: LLM 입력 토큰 절감 + 추출 정확도 향상
    │  대상: 설명란 텍스트, 작성자 댓글, (개발 전용) 자막
    │  처리:
    │  - 광고/링크/챕터 타임스탬프/구독 유도 문구 제거 (패턴 매칭)
    │  - 반복 문장 제거 (deduplicate)
    │  - 재료/계량/조리 키워드 주변 문장 우선 추출
    │  - 예상 LLM 비용 절감: ~40~60%
    │
    ▼
[Recipe Extract Service] LLM에 전달
    │  System: "요리 레시피 추출 전문가. JSON 반환."
    │  User: "설명란: {description}\n작성자댓글: {author_comment}\n(개발전용)자막: {transcript}"
    │  → 재료별 정확한 분량(숫자+단위) 추출 필수
    │  → base_servings 출처 명시: explicit(영상 언급) / inferred(재료량 추론) / default(4인분 가정)
    │
    ▼
[Recipe Transform Service] 사용자 조건 적용
    │  - 인원수: 4인분 → 2인분
    │  - 재료별 scaling_strategy 적용 (v2.3):
    │    linear: 단순 비례 (두부 1모 → 0.5모)
    │    stepwise: 정수 단위 반올림 (계란 3개 → 2개, 1.5 아님)
    │    to_taste: 비례하지 않음, 맛보며 조절 (소금, 후추)
    │    fixed: 인원수 무관 고정 (식용유 적당량)
    │  - 모호한 분량 → 표준 단위 변환
    │
    ▼
[Ingredient Gap Service] ★ 부족 재료 상세 분석 (런타임, 캐싱 안 함)
    │
    │  입력:
    │    - recipe_ingredients: 레시피가 요구하는 재료 + 분량
    │    - user_ingredients: 사용자가 보유한 재료 + 수량
    │
    │  분석 로직:
    │  ┌───────────────────────────────────────────────┐
    │  │ 재료별 4가지 상태 판정:                          │
    │  │                                                │
    │  │ ✅ SUFFICIENT  — 보유 & 충분                    │
    │  │    (사용자 계란 6개, 레시피 계란 2개 필요)         │
    │  │                                                │
    │  │ ⚠️ PARTIAL     — 보유하지만 부족할 수 있음       │
    │  │    (사용자 계란 1개, 레시피 계란 3개 필요)         │
    │  │    → 부족분: 2개 표시                            │
    │  │                                                │
    │  │ ❌ MISSING      — 미보유                        │
    │  │    (사용자 참기름 없음, 레시피 참기름 1큰술 필요)   │
    │  │    → 필요량 전체 표시 + 대체 재료 추천            │
    │  │                                                │
    │  │ ➖ BASIC        — 기본 양념 (소금/후추/식용유 등) │
    │  │    → 대부분 집에 있다고 가정, 별도 섹션 표시      │
    │  └───────────────────────────────────────────────┘
    │
    │  수량 비교가 가능한 경우 (양쪽 모두 숫자+단위 존재):
    │    → 정확한 부족분 계산 (필요 3개 - 보유 1개 = 부족 2개)
    │
    │  수량 비교가 불가능한 경우 (사용자 입력이 "있음"만):
    │    → 상태를 "보유(수량 미확인)"으로 표시
    │    → 레시피 필요량만 표시하여 사용자가 직접 판단
    │
    ▼
[PostgreSQL] recipe_core만 캐싱 (YouTube 메타 제외, 정책 준수)
    │  ⚠️ GAP 결과는 캐싱하지 않음 (사용자별 데이터)
    │  GAP은 항상 런타임 계산 (recipe_ingredients vs user_ingredients 배열 비교, <5ms)
    │  ⚠️ base_servings가 inferred/default이면 UI에 "인분 추정치" 배너 표시
    │
    ▼
[Client] 레시피 카드 렌더링
    │  ┌────────────────────────────────────────┐
    │  │  🍳 두부계란찜 (백종원의 요리비책)        │
    │  │  ⏱ 10분 | 👤 2인분 | ⭐ 쉬움            │
    │  │                                        │
    │  │  📦 재료 현황                            │
    │  │  ✅ 두부 ─── 0.5모 필요 (충분)           │
    │  │  ✅ 계란 ─── 2개 필요 (충분)             │
    │  │  ✅ 대파 ─── 약간 필요 (충분)            │
    │  │  ⚠️ 간장 ─── 2큰술 필요 (보유, 수량확인) │
    │  │  ❌ 참기름 ── 0.5큰술 필요 (미보유)       │
    │  │     └ 💡 대체: 들기름                    │
    │  │  ➖ 소금, 후추 (기본 양념)               │
    │  │                                        │
    │  │  🛒 부족 재료 요약                       │
    │  │  "1개 부족 (참기름)"                     │
    │  │  [장보기 목록에 추가]                     │
    │  └────────────────────────────────────────┘
```

#### Flow C: 재료 사진 → 인식

```
사용자가 냉장고 사진 촬영/업로드
    │
    ▼
[Vision Service] 이미지 → Vision AI 전달
    │  Prompt: "이 사진의 식재료를 식별하세요.
    │   각 재료의 이름(한국어), 대략적 수량,
    │   그리고 유사 후보 2~3개를 JSON 배열로 반환하세요."
    │
    ▼
[Ingredient Service] 인식 결과 정규화
    │  - 재료 DB와 매칭 (fuzzy matching)
    │  - 수량: "많음/보통/적음" 또는 개수
    │  - 유사 후보: 수정 시 드롭다운으로 제공
    │  - 양념/소스류: 인식 대신 "집에 있음/없음" 체크 UX로 전환
    │
    ▼
[Client] 인식된 재료 태그 표시
    │  - 각 태그 수정/삭제 가능
    │  - 수정 클릭 시 유사 후보 드롭다운 ("대파" → "쪽파 / 부추 / 실파")
    │  - "기본 양념 체크" 섹션 (소금/간장/식용유 등 있음/없음 토글)
    │  - "재료 추가" 버튼
    │  - 확인 후 Flow A로 진입
```

#### Flow D: 외부 레시피 텍스트 입력

```
사용자가 레시피 텍스트 붙여넣기
    │
    ▼
[Recipe Extract Service] LLM 구조화
    │  Prompt: "다음 텍스트에서 레시피를 추출하여
    │   표준 JSON으로 변환하세요."
    │  (유튜브 자막과 동일한 추출 프롬프트 재사용)
    │
    ▼
[Recipe Transform Service] 인원수 조절 적용
    │
    ▼
[Client] 레시피 카드 렌더링
    │  - 원본 텍스트 접기/펼치기
    │  - 구조화된 레시피 카드
    │  - 인원수 슬라이더
```

---

## 4. DB 스키마 초안

### ERD 관계

```
users ─┬── user_favorite_channels ──── youtube_channels
       │                                     │
       ├── user_ingredients                  └── channel_video_index ← v2.3
       │        │
       │        └── ingredient_master
       │
       ├── saved_recipes
       │        │
       │        └── recipe_core_ingredients
       │
       └── search_history

recipe_core (추출 레시피 — 장기 보관)  ← v2.3 분리
       │
       ├── recipe_core_ingredients
       │
       └── youtube_video_snapshot (YouTube 메타 — 30일 TTL)  ← v2.3 분리

ingredient_master (정규화된 재료 마스터)

dish_name_master (요리명 판별 + typical_ingredient_ids)
```

### 테이블 정의

#### `users`
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 사용자 고유 ID |
| email | VARCHAR(255) | UNIQUE, NULL | 이메일 (소셜 로그인) |
| nickname | VARCHAR(50) | NOT NULL | 표시 이름 |
| provider | VARCHAR(20) | NOT NULL | 'google' / 'kakao' / 'anonymous' |
| provider_id | VARCHAR(255) | | 소셜 로그인 ID |
| default_servings | INT | DEFAULT 2 | 기본 인원수 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

#### `youtube_channels`
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| channel_id | VARCHAR(50) | UNIQUE, NOT NULL | YouTube 채널 ID |
| channel_name | VARCHAR(200) | NOT NULL | 채널명 |
| thumbnail_url | TEXT | | 채널 프로필 이미지 |
| subscriber_count | BIGINT | | 구독자 수 |
| synced_at | TIMESTAMP | | 마지막 동기화 시점 |

#### `user_favorite_channels`
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| user_id | UUID | FK → users | |
| channel_id | UUID | FK → youtube_channels | |
| priority | INT | DEFAULT 0 | 정렬 우선순위 |
| created_at | TIMESTAMP | NOT NULL | |
| | | UNIQUE(user_id, channel_id) | 중복 방지 |

#### `user_ingredients` ← NEW (v2.2 추가)
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| user_id | UUID | FK → users | |
| ingredient_id | UUID | FK → ingredient_master, NULL | 매칭된 마스터 재료 |
| name | VARCHAR(100) | NOT NULL | 사용자 입력 재료명 |
| amount | FLOAT | NULL | 수량 (미입력 시 NULL = "있지만 양 모름") |
| unit | VARCHAR(20) | NULL | 단위 |
| source | VARCHAR(20) | DEFAULT 'manual' | 'manual' / 'photo' / 'receipt' |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

> **저장 전략:**
> - **회원:** `user_ingredients` 테이블에 저장. 세션 간 유지.
> - **비회원:** 프론트엔드 React state에서만 관리 (새로고침 시 초기화). 비회원이 재료를 입력한 상태에서 회원가입하면 현재 세션 데이터를 DB로 마이그레이션.
> - **localStorage 미사용** (Artifact 환경 제약 + 보안 고려)

#### `ingredient_master`
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| name | VARCHAR(100) | NOT NULL | 정규화된 이름 (예: "대파") |
| aliases | TEXT[] | | 별칭 배열 ["파", "쪽파", "green onion"] |
| category | VARCHAR(50) | NOT NULL | '채소'/'육류'/'해산물'/'양념'/'유제품'/... |
| default_unit | VARCHAR(20) | | 기본 단위 ('g'/'ml'/'개'/'줌') |
| icon_url | TEXT | | 재료 아이콘 |

#### `dish_name_master` ← NEW (요리명 판별용)
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| name | VARCHAR(200) | NOT NULL | 정규화된 요리명 (예: "김치찌개") |
| aliases | TEXT[] | | 별칭 ["김찌", "kimchi jjigae"] |
| cuisine_type | VARCHAR(20) | NOT NULL | '한식'/'중식'/'양식'/'일식'/'동남아'/'퓨전'/... |
| pattern_suffix | VARCHAR(20) | | 패턴 접미사 ("찌개","볶음","탕","파스타" 등) |
| typical_ingredients | TEXT[] | | 주요 재료 표시용 ["김치","돼지고기","두부"] |
| typical_ingredient_ids | UUID[] | | ingredient_master FK 배열 (정규화 매칭용) ← v2.3 |
| popularity_score | FLOAT | DEFAULT 0 | 검색 빈도 기반 인기도 |

#### `channel_video_index` ← v2.3 (채널 인덱싱) — v2.4 TTL 추가
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| channel_id | UUID | FK → youtube_channels | |
| video_id | VARCHAR(20) | NOT NULL | YouTube video ID |
| title | VARCHAR(500) | NOT NULL | 영상 제목 |
| description_text | TEXT | | 설명란 전체 텍스트 |
| has_recipe_in_desc | BOOLEAN | DEFAULT false | 설명란에 레시피 패턴 존재 여부 |
| published_at | TIMESTAMP | | 영상 게시일 |
| tsv_title | TSVECTOR | | 제목 Full-Text Search 벡터 |
| tsv_description | TSVECTOR | | 설명란 Full-Text Search 벡터 |
| indexed_at | TIMESTAMP | NOT NULL | 마지막 인덱싱 시점 |
| expires_at | TIMESTAMP | NOT NULL | **indexed_at + 30일 (정책 준수)** ← v2.4 |
| | | UNIQUE(video_id) | |

> **YouTube Developer Policies 준수 (v2.4):**
> YouTube API 데이터(제목/설명란/tsvector)는 `youtube_video_snapshot`뿐 아니라 `channel_video_index`에도 저장됩니다.
> 비승인 API 데이터의 30일 저장 제한에 따라, `expires_at`을 `indexed_at + 30일`로 설정합니다.
> **Nightly 배치가 매일 refresh하므로** 정상 운영 시 expires_at은 계속 갱신되어 만료 데이터는 발생하지 않습니다.
> 배치 실패 30일 이상 시 해당 데이터는 자동 삭제됩니다. (정책 위반 구조적 방지)

#### `recipe_core` ← v2.3 (기존 recipe_cache에서 분리 — 추출 레시피 데이터)
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| source_type | VARCHAR(20) | NOT NULL | 'youtube' / 'text' / 'ocr' / 'url' |
| source_id | VARCHAR(100) | NOT NULL | YouTube video_id 또는 텍스트 해시 |
| | | UNIQUE(source_type, source_id) | 복합 유니크 |
| dish_name | VARCHAR(200) | NOT NULL | 요리명 |
| base_servings | INT | NOT NULL | 원본 인원수 |
| base_servings_source | VARCHAR(20) | DEFAULT 'default' | 'explicit' / 'inferred' / 'default' ← v2.3 |
| steps | JSONB | NOT NULL | 조리 단계 배열 |
| cooking_time_min | INT | | 예상 조리 시간 (분) |
| difficulty | VARCHAR(10) | | 'easy' / 'medium' / 'hard' |
| raw_transcript | TEXT | | 원본 자막/텍스트 (YouTube 정책 외 데이터) |
| confidence_score | FLOAT | | AI 추출 신뢰도 (0~1) |
| prompt_version | VARCHAR(20) | | LLM 프롬프트 버전 (운영 추적) ← v2.3 |
| created_at | TIMESTAMP | NOT NULL | |

> **설계 결정:** YouTube API로 받은 데이터(조회수, 제목, 썸네일 등)는 `youtube_video_snapshot`에 분리 저장합니다. YouTube Developer Policies에 따라 비승인 데이터는 30일 초과 저장 금지이므로, 추출 레시피(recipe_core)와 YouTube 메타데이터의 생명주기를 분리합니다.

#### `youtube_video_snapshot` ← v2.3 신규 (YouTube API 데이터, 30일 TTL)
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| video_id | VARCHAR(20) | UNIQUE, NOT NULL | YouTube video ID |
| title | VARCHAR(500) | NOT NULL | 영상 제목 |
| yt_channel_id | VARCHAR(50) | | YouTube 채널 ID |
| channel_name | VARCHAR(200) | | 채널명 |
| view_count | BIGINT | | 조회수 |
| like_count | BIGINT | | 좋아요 수 |
| duration_seconds | INT | | 영상 길이 |
| thumbnail_url | TEXT | | 썸네일 |
| published_at | TIMESTAMP | | 게시일 |
| fetched_at | TIMESTAMP | NOT NULL | API 조회 시점 |
| expires_at | TIMESTAMP | NOT NULL | **30일 후 자동 만료** (정책 준수) |

> **운영:** Nightly 배치에서 `expires_at < now()` 데이터를 삭제하거나 videos.list로 refresh합니다. refresh 실패 시 삭제(soft delete)합니다.

#### `recipe_core_ingredients` (기존 recipe_cache_ingredients 대체)
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| recipe_id | UUID | FK → recipe_core | |
| ingredient_id | UUID | FK → ingredient_master, NULL | 매칭된 재료 |
| raw_name | VARCHAR(200) | NOT NULL | 원본 텍스트 ("간장 2큰술") |
| name | VARCHAR(100) | NOT NULL | 정규화된 이름 |
| amount | FLOAT | | 수량 |
| unit | VARCHAR(20) | | 단위 |
| scaling_strategy | VARCHAR(20) | DEFAULT 'linear' | 'linear'/'stepwise'/'to_taste'/'fixed' ← v2.3 |
| is_optional | BOOLEAN | DEFAULT false | 선택 재료 여부 |
| sort_order | INT | | 표시 순서 |

> **scaling_strategy 정의 (v2.3, 기존 is_scalable 대체):**
> - `linear`: 인원수에 비례 (두부 1모 → 0.5모)
> - `stepwise`: 정수 단위 반올림 (계란 4개 → 2개, 1.5개 아님)
> - `to_taste`: 비례하지 않음, 맛보며 조절 (소금 약간)
> - `fixed`: 인원수 무관 고정 (식용유 적당량, 참기름 한 바퀴)

#### `saved_recipes`
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| user_id | UUID | FK → users | |
| recipe_core_id | UUID | FK → recipe_core | |
| custom_servings | INT | | 저장 시 인원수 |
| notes | TEXT | | 개인 메모 |
| created_at | TIMESTAMP | NOT NULL | |

#### `search_history`
| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| user_id | UUID | FK → users, NULL | 비회원은 NULL |
| session_id | VARCHAR(100) | | 익명 세션 ID |
| query | TEXT | NOT NULL | 사용자 입력 원문 ("김치찌개" 또는 "계란, 파, 두부") |
| search_type | VARCHAR(20) | NOT NULL | 'dish_name' / 'ingredients' / 'ambiguous' |
| detected_dish_id | UUID | FK → dish_name_master, NULL | 요리명 모드일 때 매칭된 요리 |
| detected_ingredients | TEXT[] | NULL | 재료 모드일 때 파싱된 재료 배열 |
| servings | INT | | |
| mode | VARCHAR(20) | | 'video' / 'recipe' |
| channel_filter | BOOLEAN | DEFAULT false | 채널 필터 사용 여부 |
| created_at | TIMESTAMP | NOT NULL | |

### 인덱스 전략

```sql
-- 레시피 코어 (분리된 구조)
CREATE UNIQUE INDEX idx_recipe_core_source ON recipe_core(source_type, source_id);

-- YouTube 스냅샷 (30일 TTL 관리)
CREATE UNIQUE INDEX idx_yt_snapshot_video ON youtube_video_snapshot(video_id);
CREATE INDEX idx_yt_snapshot_expires ON youtube_video_snapshot(expires_at);

-- 채널 영상 인덱스 (로컬 검색 핵심 + 30일 TTL) ← v2.4 expires 추가
CREATE UNIQUE INDEX idx_channel_video ON channel_video_index(video_id);
CREATE INDEX idx_channel_video_channel ON channel_video_index(channel_id);
CREATE INDEX idx_channel_video_tsv_title ON channel_video_index USING GIN(tsv_title);
CREATE INDEX idx_channel_video_tsv_desc ON channel_video_index USING GIN(tsv_description);
CREATE INDEX idx_channel_video_expires ON channel_video_index(expires_at);

-- 한국어 fuzzy 검색 (pg_trgm) ← v2.4 MVP 승격
-- 로컬 검색이 MVP 코어이므로 오타/띄어쓰기 변형 대응 필수
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_channel_video_title_trgm ON channel_video_index USING GIN(title gin_trgm_ops);
CREATE INDEX idx_dish_name_trgm ON dish_name_master USING GIN(name gin_trgm_ops);
CREATE INDEX idx_ingredient_name_trgm ON ingredient_master USING GIN(name gin_trgm_ops);

-- 재료 검색 (GIN for array)
CREATE INDEX idx_ingredient_aliases ON ingredient_master USING GIN(aliases);

-- 요리명 검색
CREATE INDEX idx_dish_name ON dish_name_master(name);
CREATE INDEX idx_dish_aliases ON dish_name_master USING GIN(aliases);
CREATE INDEX idx_dish_cuisine ON dish_name_master(cuisine_type);
CREATE INDEX idx_dish_typical_ids ON dish_name_master USING GIN(typical_ingredient_ids);

-- 사용자 보유 재료
CREATE INDEX idx_user_ingredients_user ON user_ingredients(user_id);

-- 사용자 즐겨찾기
CREATE INDEX idx_user_channels ON user_favorite_channels(user_id);

-- 검색 히스토리
CREATE INDEX idx_search_history_user ON search_history(user_id, created_at DESC);
CREATE INDEX idx_search_history_type ON search_history(search_type);
```

---

## 5. API 설계 초안

### 5.1 공통 규약

| 항목 | 규칙 |
|------|------|
| Base URL | `https://api.fridgetube.kr/v1` |
| 인증 | Bearer Token (JWT), 비회원은 세션 토큰 |
| Content-Type | `application/json` |
| 에러 형식 | `{ "error": { "code": "ERR_CODE", "message": "설명", "details": {} } }` |
| 페이지네이션 | `?cursor={last_id}&limit={n}` (커서 기반) |
| Rate Limit | 비회원 30req/min, 회원 60req/min, 프리미엄 120req/min |

### 5.2 에러 코드 규약

| HTTP | 코드 | 의미 |
|------|------|------|
| 400 | INVALID_INPUT | 잘못된 입력 (빈 재료 등) |
| 401 | UNAUTHORIZED | 인증 필요 |
| 403 | RATE_LIMITED | 요청 제한 초과 |
| 403 | QUOTA_EXCEEDED | 무료 변환 횟수 초과 |
| 404 | NOT_FOUND | 리소스 없음 |
| 422 | EXTRACTION_FAILED | 레시피 추출 실패 |
| 502 | UPSTREAM_ERROR | YouTube/LLM API 오류 |
| 503 | SERVICE_UNAVAILABLE | 서비스 일시 중단 |

### 5.3 엔드포인트

#### `POST /v1/search/videos` — 통합 스마트 검색

```
Request:
{
  "query": "김치찌개",                          // 자유 입력 (재료 또는 요리명)
  "user_ingredients": [                        // 보유 재료 (부족분 계산용, 선택)
    { "name": "김치", "amount": 0.5, "unit": "포기" },
    { "name": "돼지고기", "amount": 200, "unit": "g" },
    { "name": "두부", "amount": 1, "unit": "모" },
    { "name": "대파", "amount": null, "unit": null }   // 수량 모르면 null
  ],
  "servings": 2,
  "mode": "video",                             // "video" | "recipe"
  "channel_filter": true,
  "sort_by": "relevance",                      // "relevance" | "view_count" | "least_missing"
  "limit": 10,
  "cursor": null
}

Response 200 (요리명 검색 시):
{
  "search_type": "dish_name",                  // "dish_name" | "ingredients" | "ambiguous"
  "detected_query": {
    "dish_name": "김치찌개",
    "cuisine_type": "한식",
    "ingredients": null
  },
  "videos": [
    {
      "video_id": "abc123",
      "title": "김치찌개 황금레시피! 이렇게 끓이면 식당보다 맛있어요",
      "channel": {
        "id": "UCyn-K7rZLXjGl7VXGweIlcA",
        "name": "백종원의 요리비책",
        "thumbnail": "https://..."
      },
      "thumbnail": "https://img.youtube.com/vi/abc123/maxresdefault.jpg",
      "view_count": 8500000,
      "like_count": 120000,
      "published_at": "2024-11-20T09:00:00Z",
      "duration_seconds": 540,
      "has_cached_recipe": true,
      "ingredient_gap_estimate": {             // ★ typical_ingredients 기반 "예상" GAP (LLM 미사용)
        "source": "typical_ingredients",       // "typical" = dish_name_master 기반 추정
        "is_estimate": true,                   // 프론트에서 "~" 표시 근거
        "typical_total": 6,
        "user_has": 4,
        "estimated_missing": 2,
        "estimated_missing_list": ["고춧가루", "멸치액젓"],
        "gap_score": 0.67,                     // 1.0 = 재료 완벽, 0.0 = 전부 부족
        "note": "영상을 선택하면 정확한 재료 분석을 볼 수 있어요"
      }
    },
    {
      "video_id": "def456",
      "title": "참치김치찌개 초간단 레시피",
      "channel": { "id": "UCyyy", "name": "수미네 반찬", "thumbnail": "https://..." },
      "thumbnail": "https://...",
      "view_count": 3200000,
      "like_count": 55000,
      "published_at": "2025-01-10T09:00:00Z",
      "duration_seconds": 380,
      "has_cached_recipe": false,
      "ingredient_gap_estimate": {
        "source": "typical_ingredients",
        "is_estimate": true,
        "typical_total": 6,
        "user_has": 2,
        "estimated_missing": 3,
        "estimated_missing_list": ["참치캔", "고춧가루", "다진마늘"],
        "gap_score": 0.50,
        "note": "영상을 선택하면 정확한 재료 분석을 볼 수 있어요"
      }
    }
  ],
  "next_cursor": "xyz789",
  "total_estimate": 47,
  "sort_applied": "relevance"                  // "least_missing" 선택 시 gap_score 내림차순 (예상치 기반)
}

Response 200 (재료 검색 시):
{
  "search_type": "ingredients",
  "detected_query": {
    "dish_name": null,
    "cuisine_type": null,
    "ingredients": ["계란", "대파", "두부"]
  },
  "videos": [
    {
      "video_id": "ghi789",
      "title": "두부계란찜 10분 완성!",
      // ... (위와 동일 구조)
      "ingredient_match_rate": 0.85,           // 재료 모드에서만 표시
      "ingredient_gap_estimate": null            // 재료 모드에서는 GAP 불필요
    }
  ]
}

Response 200 (모호한 입력 시 — "파스타"):
{
  "search_type": "ambiguous",
  "detected_query": {
    "dish_name": "파스타",
    "ingredients": ["파스타면"],
    "ambiguous_reason": "재료이면서 요리 카테고리"
  },
  "tabs": {
    "as_dish": { "label": "파스타 요리 레시피", "count": 120 },
    "as_ingredient": { "label": "'파스타면'으로 만들 수 있는 요리", "count": 85 }
  },
  "videos": [ /* 기본은 요리명(as_dish) 결과 표시 */ ]
}

Response 400:
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "검색어를 입력해주세요.",
    "details": { "field": "query" }
  }
}
```

#### `POST /v1/recipe/extract` — 영상 레시피 추출 + 재료 GAP 상세 분석

```
Request:
{
  "video_id": "abc123",
  "servings": 2,
  "user_ingredients": [                        // ★ 수량 포함 보유 재료
    { "name": "계란", "amount": 6, "unit": "개" },
    { "name": "대파", "amount": null, "unit": null },
    { "name": "두부", "amount": 1, "unit": "모" },
    { "name": "간장", "amount": null, "unit": null }
  ]
}

Response 200:
{
  "recipe": {
    "id": "rec_uuid",
    "dish_name": "두부계란찜",
    "source": {
      "type": "youtube",
      "video_id": "abc123",
      "video_title": "두부계란찜 10분 완성!",
      "channel_name": "백종원의 요리비책"
    },
    "base_servings": 4,
    "requested_servings": 2,
    "cooking_time_min": 10,
    "difficulty": "easy",
    "confidence_score": 0.92,

    "ingredients": [
      {
        "name": "두부",
        "amount": 0.5,
        "unit": "모",
        "original_amount": 1,
        "original_text": "두부 한 모",
        "scaling_strategy": "linear",
        "category": "MAIN",
        "gap_status": "SUFFICIENT",
        "gap_detail": {
          "user_has": 1.0,
          "user_unit": "모",
          "recipe_needs": 0.5,
          "shortage": 0,
          "shortage_display": null
        }
      },
      {
        "name": "계란",
        "amount": 2,
        "unit": "개",
        "original_amount": 4,
        "original_text": "계란 4개",
        "scaling_strategy": "linear",
        "category": "MAIN",
        "gap_status": "SUFFICIENT",
        "gap_detail": {
          "user_has": 6,
          "user_unit": "개",
          "recipe_needs": 2,
          "shortage": 0,
          "shortage_display": null
        }
      },
      {
        "name": "대파",
        "amount": 0.5,
        "unit": "대",
        "original_amount": 1,
        "original_text": "대파 1대",
        "scaling_strategy": "linear",
        "category": "SUB",
        "gap_status": "UNKNOWN_QTY",
        "gap_detail": {
          "user_has": null,
          "user_unit": null,
          "recipe_needs": 0.5,
          "shortage": null,
          "shortage_display": "보유 중 (수량 확인 필요: 0.5대)"
        }
      },
      {
        "name": "간장",
        "amount": 1,
        "unit": "큰술",
        "original_amount": 2,
        "original_text": "간장 2큰술",
        "scaling_strategy": "to_taste",
        "category": "SEASONING",
        "gap_status": "UNKNOWN_QTY",
        "gap_detail": {
          "user_has": null,
          "user_unit": null,
          "recipe_needs": 1,
          "shortage": null,
          "shortage_display": "보유 중 (수량 확인 필요: 1큰술)"
        }
      },
      {
        "name": "참기름",
        "amount": 0.5,
        "unit": "큰술",
        "original_amount": 1,
        "original_text": "참기름 한 큰술",
        "scaling_strategy": "to_taste",
        "category": "SEASONING",
        "gap_status": "MISSING",
        "gap_detail": {
          "user_has": 0,
          "user_unit": null,
          "recipe_needs": 0.5,
          "shortage": 0.5,
          "shortage_display": "0.5큰술 필요"
        }
      },
      {
        "name": "소금",
        "amount": null,
        "unit": null,
        "original_amount": null,
        "original_text": "소금 약간",
        "scaling_strategy": "to_taste",
        "category": "BASIC",
        "gap_status": "BASIC_ASSUMED",
        "gap_detail": {
          "user_has": null,
          "user_unit": null,
          "recipe_needs": null,
          "shortage": null,
          "shortage_display": "기본 양념 (대부분 보유)"
        }
      }
    ],

    "steps": [
      { "order": 1, "text": "두부를 깍둑썰기로 자릅니다.", "time_seconds": null },
      { "order": 2, "text": "계란을 풀어 간장 1큰술과 섞습니다.", "time_seconds": null },
      { "order": 3, "text": "중불에서 10분간 찝니다.", "time_seconds": 600 }
    ],

    "ingredient_gap_summary": {
      "total": 6,
      "sufficient": 2,
      "unknown_qty": 2,
      "missing": 1,
      "basic": 1,
      "gap_score": 0.83,
      "missing_items": [
        {
          "name": "참기름",
          "needed": "0.5큰술",
          "substitution": {
            "name": "들기름",
            "note": "맛은 비슷하나 향이 다소 약해집니다",
            "gap_status_if_substituted": "SUFFICIENT"
          }
        }
      ],
      "shopping_list": [
        { "name": "참기름", "amount": "0.5큰술", "note": "들기름으로 대체 가능" }
      ],
      "verdict": "거의 준비 완료! 참기름만 있으면 바로 요리할 수 있어요."
    }
  }
}

Response 422:
{
  "error": {
    "code": "EXTRACTION_FAILED",
    "message": "이 영상에서 레시피를 추출할 수 없습니다. ASMR/무음 영상이거나 자막이 비활성화되어 있습니다.",
    "details": { "reason": "no_transcript" }
  }
}
```

**gap_status 상태 정의:**

| 상태 | 의미 | UI 표현 |
|------|------|---------|
| `SUFFICIENT` | 보유 & 수량 충분 | ✅ 초록색 |
| `PARTIAL` | 보유하지만 부족 | ⚠️ 노란색 + "N개 더 필요" |
| `UNKNOWN_QTY` | 보유하지만 수량 미확인 | 🔵 파란색 + "수량 확인 필요: N" |
| `MISSING` | 미보유 | ❌ 빨간색 + 필요량 표시 + 대체재 |
| `BASIC_ASSUMED` | 기본 양념 (보유 가정) | ➖ 회색 + 접힌 상태 |

**객관적 한계 인정:**
- 사용자가 수량을 입력하지 않은 재료(`amount: null`)는 정확한 부족분 계산이 불가능합니다.
- 이 경우 `UNKNOWN_QTY` 상태로 처리하여 "보유 중이지만 레시피에는 N만큼 필요합니다"라고 안내하는 것이 사용자에게 정직한 UX입니다.
- 사진 인식(Flow C)에서 수량까지 잡아주면 이 문제가 줄어들지만, Phase 1에서는 대략적 추정만 가능합니다.

#### `POST /v1/recipe/parse-text` — 외부 레시피 텍스트 구조화

```
Request:
{
  "text": "재료: 돼지고기 300g, 양파 1개, 간장 3큰술...\n만드는 법: 1. 돼지고기를 한입 크기로...",
  "servings": 2
}

Response 200:
{
  "recipe": {
    "id": "rec_uuid",
    "dish_name": "돼지고기 간장불고기",
    "source": { "type": "text" },
    // ... (extract 응답과 동일 구조)
  }
}
```

#### `POST /v1/ingredients/recognize` — 사진 재료 인식

```
Request:
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",   // base64 또는
  "image_url": "https://..."                        // URL
}

Response 200:
{
  "ingredients": [
    { "name": "계란", "quantity": "6개", "confidence": 0.95 },
    { "name": "대파", "quantity": "2줄기", "confidence": 0.88 },
    { "name": "두부", "quantity": "1모", "confidence": 0.82 },
    { "name": "불명확한 재료", "quantity": null, "confidence": 0.35 }
  ],
  "low_confidence_items": ["불명확한 재료"],
  "message": "4개 재료를 인식했습니다. 확인 후 수정해주세요."
}
```

#### `GET/POST /v1/channels` — 선호 채널 관리

```
GET /v1/channels/search?q=백종원

Response 200:
{
  "channels": [
    {
      "channel_id": "UCyn-K7rZLXjGl7VXGweIlcA",
      "name": "백종원의 요리비책",
      "subscriber_count": 6200000,
      "thumbnail": "https://...",
      "video_count": 850
    }
  ]
}

POST /v1/channels/favorites
{
  "channel_id": "UCyn-K7rZLXjGl7VXGweIlcA"
}

Response 201:
{ "message": "채널이 추가되었습니다.", "total_favorites": 3 }

DELETE /v1/channels/favorites/{channel_id}
Response 204: (No Content)
```

---

## 6. 화면 목록 + UI 상태

### 6.1 화면 목록

| # | 화면 | 경로 | 설명 |
|---|------|------|------|
| S01 | 홈/재료 입력 | `/` | 메인 랜딩 + 재료 입력 인터페이스 |
| S02 | 검색 결과 | `/results` | 영상 목록 또는 레시피 카드 목록 |
| S03 | 레시피 상세 | `/recipe/{id}` | 레시피 카드 전체 + 영상 임베드 |
| S04 | 채널 관리 | `/channels` | 선호 유튜버 검색/추가/삭제 |
| S05 | 사진 인식 | `/scan` (모달) | 사진 업로드 → 인식 결과 확인 |
| S06 | 외부 레시피 입력 | `/import` (모달) | 텍스트 붙여넣기 → 구조화 |
| S07 | 마이페이지 | `/my` | 저장 레시피, 검색 히스토리, 설정 |

### 6.2 핵심 화면별 UI 상태

#### S01 홈/재료 입력

| 상태 | 조건 | UI 표현 |
|------|------|---------|
| 초기 | 첫 진입 | 큰 입력 필드 + "냉장고에 뭐가 있나요?" placeholder. 카테고리 바로가기 버튼. 인기 검색어 태그 |
| 입력 중 | 재료 1개 이상 | 입력된 재료 태그 표시 + 자동완성 드롭다운. 인원수 슬라이더 노출. 모드 토글 노출 |
| 채널 필터 ON | 선호 유튜버 있음 | "내 유튜버에서만 검색" 토글 활성. 등록 채널 아바타 미니 표시 |
| 채널 필터 ON + 채널 없음 | 유튜버 미등록 | "먼저 좋아하는 유튜버를 등록하세요" 링크 노출 |
| 사진 인식 후 | 사진 결과 반환 | 인식된 재료 태그 자동 채움 + "수정하세요" 안내 배너 |

#### S02 검색 결과

| 상태 | 조건 | UI 표현 |
|------|------|---------|
| 로딩 | API 호출 중 | 스켈레톤 카드 6개 + "맛있는 레시피를 찾고 있어요..." 메시지 |
| 영상 모드 결과 | 영상 있음 | 썸네일 카드 그리드. 재료 일치율 뱃지. 채널 아바타. 조회수/좋아요 |
| 레시피 모드 결과 | 레시피 있음 | 레시피 카드 리스트. 재료 보유/미보유 색상 구분. 난이도 뱃지 |
| 빈 상태 | 결과 0건 | 일러스트 + "이 재료 조합으로는 영상을 찾지 못했어요". 재료 수정 제안 또는 채널 필터 해제 제안 |
| 오류 | API 실패 | "잠시 문제가 발생했어요. 다시 시도해주세요." 재시도 버튼 |
| 채널 필터 결과 부족 | 필터 결과 < 3 | "선호 채널에서 {n}개 찾았어요. 전체 검색 결과도 볼까요?" 확장 버튼 |

#### S03 레시피 상세

| 상태 | 조건 | UI 표현 |
|------|------|---------|
| 로딩 | 레시피 추출 중 | "AI가 영상을 분석 중입니다..." 프로그레스 (예상 5~15초) |
| 추출 완료 | 레시피 있음 | 상단: 영상 임베드. 하단: 원본/변환 탭. 인원수 슬라이더. 재료 체크리스트. 조리 순서 스텝 |
| 추출 실패 | 자막 없음 등 | "이 영상에서 레시피를 자동 추출하지 못했어요." + 영상 직접 보기 링크 + 수동 입력 폼 |
| 분량 변경 | 인원수 조절 | 변경된 재료 하이라이트. 반올림된 수량 표시. "원본: 4인분 → 현재: 2인분" 안내 |
| 낮은 신뢰도 | confidence < 0.7 | "⚠️ AI 추출 정확도가 낮을 수 있습니다. 영상을 함께 참고해주세요." 경고 배너 |

#### S05 사진 인식 (모달)

| 상태 | 조건 | UI 표현 |
|------|------|---------|
| 초기 | 모달 오픈 | 카메라/갤러리 선택 버튼. "냉장고 안을 찍어주세요!" 가이드 일러스트 |
| 업로드 중 | 이미지 전송 | 업로드 프로그레스 바 |
| 분석 중 | Vision AI 처리 | "재료를 인식하고 있어요..." 로딩 애니메이션 |
| 결과 | 인식 완료 | 인식 재료 태그 목록. 각 태그 옆 ✕(삭제) 버튼. 수량 수정 드롭다운. 신뢰도 낮은 항목 노란 배경 + "맞나요?" |
| 빈 상태 | 인식 0개 | "재료를 인식하지 못했어요. 더 가까이 찍어보시거나 직접 입력해주세요." |
| 횟수 초과 | 무료 한도 도달 | "오늘 무료 사진 인식을 모두 사용했어요. 프리미엄으로 무제한 이용하세요." |

---

## 7. Claude Code 에이전트 실행 계획

### 설계 원칙

**모든 태스크가 Claude Code 에이전트팀의 단일 세션에서 완료 가능하도록 설계합니다.**

- 각 태스크는 **1~4시간** 단위로 분할
- 각 태스크에 **입력 조건 / 실행 내용 / 검증 기준 / 산출물**을 명시
- 태스크 간 **의존성을 최소화**하여 중간에 끊겨도 다음 태스크부터 재개 가능
- 각 스테이지 완료 시 **체크포인트 (동작 확인)** 수행
- 에이전트에게 줄 **프롬프트 예시** 포함

---

### Stage 0: 프로젝트 초기화 (Day 1)

> **목표:** 빈 프로젝트가 로컬에서 실행되고, 모든 외부 서비스 키가 준비됨

| # | 태스크 | 예상 시간 | 입력 | 산출물 | 검증 |
|---|--------|----------|------|--------|------|
| 0.1 | 모노레포 생성 + Next.js 14 초기화 | 30분 | 없음 | `/frontend` (Next.js + TS + Tailwind) | `npm run dev` → localhost:3000 접속 |
| 0.2 | FastAPI 백엔드 초기화 | 30분 | 0.1 | `/backend` (FastAPI + Poetry + uvicorn) | `uvicorn main:app` → localhost:8000/docs 접속 |
| 0.3 | Docker Compose (Neon 대신 로컬 PG + Redis) | 30분 | 0.1 | `docker-compose.yml` | `docker compose up` → PG/Redis 접속 확인 |
| 0.4 | `.env.example` + 환경변수 설정 | 20분 | 0.1~0.3 | `.env.example`, `.env.local` | 모든 키 placeholder 존재 확인 |
| 0.5 | ESLint + Prettier + Ruff 설정 | 20분 | 0.1~0.2 | lint 설정 파일 | `npm run lint` + `ruff check` 통과 |
| 0.6 | 외부 서비스 키 발급 가이드 작성 | 20분 | 없음 | `docs/API_KEYS.md` | YouTube, Gemini, Neon, Upstash, Sentry 키 목록 |

```
📋 에이전트 프롬프트 예시 (0.1):
"Next.js 14 App Router + TypeScript + Tailwind CSS 프로젝트를 /frontend 디렉토리에 생성해줘.
src/app/page.tsx에 'FridgeTube' 타이틀이 표시되면 OK. package.json에 dev/build/lint 스크립트 포함."
```

> **✅ 체크포인트 S0:** `docker compose up` → FE(3000) + BE(8000) + PG(5432) + Redis(6379) 모두 접속 가능

---

### Stage 1: 데이터베이스 + 시드 데이터 (Day 1~2)

> **목표:** 전체 스키마 생성 완료, 재료/요리명 시드 데이터 로딩됨

| # | 태스크 | 예상 시간 | 입력 | 산출물 | 검증 |
|---|--------|----------|------|--------|------|
| 1.1 | SQLAlchemy 모델 정의 (users, youtube_channels, user_favorite_channels) | 1시간 | 0.3 | `backend/models/user.py`, `backend/models/channel.py` | Alembic migration 성공 |
| 1.2 | SQLAlchemy 모델 정의 (ingredient_master, dish_name_master) | 1시간 | 1.1 | `backend/models/ingredient.py`, `backend/models/dish.py` | 테이블 생성 + pg_trgm 확장 확인 |
| 1.3 | SQLAlchemy 모델 정의 (channel_video_index, youtube_video_snapshot) | 1시간 | 1.1 | `backend/models/video.py` | tsvector 컬럼 + expires_at + 인덱스 확인 |
| 1.4 | SQLAlchemy 모델 정의 (recipe_core, recipe_core_ingredients, user_ingredients) | 1시간 | 1.1 | `backend/models/recipe.py` | 복합 유니크키 + FK 관계 확인 |
| 1.5 | SQLAlchemy 모델 정의 (search_history, saved_recipes) | 30분 | 1.1 | `backend/models/history.py` | 전체 스키마 migration 성공 |
| 1.6 | 재료 마스터 시드 데이터 (100개 한국 식재료) | 2시간 | 1.2 | `backend/seeds/ingredients.json` + 로딩 스크립트 | `SELECT count(*) FROM ingredient_master` = 100 |
| 1.7 | 요리명 마스터 시드 데이터 (300개 + typical_ingredient_ids) | 3시간 | 1.2, 1.6 | `backend/seeds/dishes.json` + 로딩 스크립트 | `SELECT count(*) FROM dish_name_master` = 300 |
| 1.8 | 패턴 접미사 + 별칭 데이터 보강 | 1시간 | 1.7 | 시드 데이터 업데이트 | "OO찌개" 패턴으로 "김치찌개" 매칭 확인 |

```
📋 에이전트 프롬프트 예시 (1.6):
"한국 요리에 사용되는 식재료 100개를 JSON 배열로 만들어줘.
각 항목: {name, aliases[], category, default_unit}.
카테고리: 채소(30), 육류(15), 해산물(15), 양념(20), 유제품(10), 기타(10).
예시: {name: '대파', aliases: ['파', '쪽파', 'green onion'], category: '채소', default_unit: '대'}"
```

> **✅ 체크포인트 S1:** `psql`에서 전체 테이블 조회 + 시드 데이터 카운트 확인. `SELECT * FROM dish_name_master WHERE name LIKE '%찌개%'` 결과 10개+

---

### Stage 2: YouTube 채널 인덱싱 서비스 (Day 2~3)

> **목표:** 큐레이션 채널 영상이 로컬 DB에 인덱싱되고, 검색 가능

| # | 태스크 | 예상 시간 | 입력 | 산출물 | 검증 |
|---|--------|----------|------|--------|------|
| 2.1 | YouTube API 클라이언트 래퍼 (channels, playlistItems, videos, commentThreads) | 2시간 | 0.4 | `backend/services/youtube_client.py` | 단위 테스트 3개 (모킹) |
| 2.2 | Channel Index Service (playlistItems → DB 저장 + tsvector 생성) | 2시간 | 2.1, 1.3 | `backend/services/channel_index.py` | 채널 1개 인덱싱 → channel_video_index 행 확인 |
| 2.3 | Quota Budgeter (Redis 기반, Pacific Time 리셋) | 1시간 | 0.3 | `backend/services/quota_budgeter.py` | `budget.can_spend(100)` → True/False 테스트 |
| 2.4 | 채널 인덱싱 배치 CLI (nightly batch 시뮬레이션) | 1시간 | 2.2, 2.3 | `backend/cli/index_channels.py` | `python -m cli.index_channels --channel UCxxx` 성공 |
| 2.5 | 큐레이션 채널 20개 선정 + 초기 인덱싱 실행 | 1시간 | 2.4 | `backend/seeds/curated_channels.json` + 실행 | `SELECT count(*) FROM channel_video_index` > 500 |
| 2.6 | 로컬 DB 검색 서비스 (tsvector + pg_trgm fuzzy) | 2시간 | 2.5, 1.2 | `backend/services/local_search.py` | "김치찌개" 검색 → 결과 5개+ |
| 2.7 | 30일 TTL 만료 데이터 정리 로직 | 30분 | 2.2 | `backend/cli/cleanup_expired.py` | expires_at < now() 행 삭제 확인 |

```
📋 에이전트 프롬프트 예시 (2.2):
"Channel Index Service를 만들어줘.
입력: YouTube channel_id 문자열
동작: (1) channels.list로 uploads playlist ID 획득
      (2) playlistItems.list로 최근 200개 영상 목록
      (3) videos.list 배치로 제목/설명란/통계
      (4) channel_video_index 테이블에 upsert
      (5) tsvector 자동 생성 (title + description)
      (6) expires_at = now() + 30일 설정
SQLAlchemy async 사용. httpx로 YouTube API 호출."
```

> **✅ 체크포인트 S2:** "김치찌개" 로컬 검색 → 인덱싱된 영상 5개+ 반환. "김치찌게"(오타) → pg_trgm fuzzy 매칭 확인

---

### Stage 3: 검색 API + Query Classifier (Day 3~4)

> **목표:** 통합 검색 API가 동작하고, 재료/요리명 자동 판별됨

| # | 태스크 | 예상 시간 | 입력 | 산출물 | 검증 |
|---|--------|----------|------|--------|------|
| 3.1 | Query Classifier (규칙 기반 의도 판별) | 2시간 | 1.2, 1.7 | `backend/services/query_classifier.py` | "김치찌개"→dish, "계란,파"→ingredients, "파스타"→ambiguous |
| 3.2 | 역방향 요리명 추론 (재료 → 후보 요리 top-k) | 1.5시간 | 1.7 | `backend/services/reverse_recipe.py` | "계란,파,두부" → ["두부계란찜","파전",...] top-5 |
| 3.3 | Ingredient Gap Service (typical_ingredients 기반 예상 GAP) | 1.5시간 | 1.7 | `backend/services/ingredient_gap.py` | 보유 재료 vs typical → gap_score 계산 |
| 3.4 | `/v1/search/videos` 엔드포인트 (로컬 검색 + search.list fallback) | 3시간 | 2.6, 3.1~3.3 | `backend/api/search.py` | curl 테스트 → 요리명/재료 모드 결과 반환 |
| 3.5 | `/v1/ingredients/search` 자동완성 엔드포인트 | 1시간 | 1.6 | `backend/api/ingredients.py` | "계"→"계란,계피" 자동완성 |

```
📋 에이전트 프롬프트 예시 (3.1):
"Query Classifier를 만들어줘. LLM 사용하지 않고 규칙 기반으로.
판별 로직:
1. ingredient_master DB에서 전체 일치 → 'ingredients'
2. 쉼표/공백 구분 다수 단어 → 'ingredients'
3. dish_name_master DB에서 일치 → 'dish_name'
4. 패턴 접미사(찌개,볶음,탕,파스타,카레 등) 매칭 → 'dish_name'
5. 위 모두 아님 → 'ambiguous'
반환: {search_type, dish_name?, ingredients?[]}"
```

> **✅ 체크포인트 S3:** `POST /v1/search/videos {query: "김치찌개"}` → 로컬 인덱스 결과 + 예상 GAP 반환. Swagger UI에서 확인

---

### Stage 4: 레시피 추출 + Gemini 연동 (Day 4~5)

> **목표:** 영상에서 레시피를 자동 추출하고, 사용자 인원수에 맞게 변환

| # | 태스크 | 예상 시간 | 입력 | 산출물 | 검증 |
|---|--------|----------|------|--------|------|
| 4.1 | Gemini API 클라이언트 (텍스트 + 이미지 통합) | 1시간 | 0.4 | `backend/services/gemini_client.py` | "안녕" → 응답 확인 |
| 4.2 | Text Compressor (설명란/댓글 전처리) | 1.5시간 | 없음 | `backend/services/text_compressor.py` | 광고/링크 제거 + 토큰 40% 절감 테스트 |
| 4.3 | Author Comment Service (commentThreads + 작성자 필터) | 2시간 | 2.1 | `backend/services/author_comment.py` | 영상 1개 → 작성자 댓글 추출 |
| 4.4 | Transcript Service (설명란 → 작성자 댓글 → Flow D 안내) | 1.5시간 | 4.2, 4.3 | `backend/services/transcript.py` | 영상 3개 테스트 → 텍스트 확보율 확인 |
| 4.5 | Recipe Extract Service (Gemini 프롬프트 + JSON 파싱) | 3시간 | 4.1, 4.4 | `backend/services/recipe_extract.py` | 설명란 텍스트 → 구조화 JSON (재료/단계/난이도) |
| 4.6 | Recipe Transform Service (scaling_strategy 기반 분량 조절) | 2시간 | 4.5 | `backend/services/recipe_transform.py` | 4인분→2인분 변환, linear/stepwise/to_taste 테스트 |
| 4.7 | `/v1/recipe/extract` 엔드포인트 | 2시간 | 4.5, 4.6, 3.3 | `backend/api/recipe.py` | curl → 영상 ID 입력 → GAP 포함 레시피 JSON |
| 4.8 | `/v1/recipe/parse-text` 엔드포인트 (외부 텍스트) | 1시간 | 4.5 | `backend/api/recipe.py` 추가 | 자유 텍스트 → 구조화 레시피 |
| 4.9 | Gemini vs Claude 정확도 PoC (5개 영상 비교) | 1시간 | 4.5 | `docs/GEMINI_POC_RESULTS.md` | 정확도 80%+ 확인 (미달 시 Claude Haiku 전환 결정) |

```
📋 에이전트 프롬프트 예시 (4.5):
"Google Gemini 2.0 Flash API를 사용해서 레시피 추출 서비스를 만들어줘.
모델: gemini-2.0-flash, temperature: 0.1
System prompt: '당신은 요리 레시피 추출 전문가입니다.'
User prompt: 설명란/댓글 텍스트를 넣으면 아래 JSON을 반환:
{dish_name, base_servings, base_servings_source, ingredients[{name,amount,unit,scaling_strategy}], steps[], cooking_time_min, difficulty}
scaling_strategy: linear|stepwise|to_taste|fixed
google-generativeai 파이썬 패키지 사용."
```

> **✅ 체크포인트 S4:** 영상 ID 입력 → Gemini가 레시피 추출 → 2인분 변환 → GAP 분석까지 E2E 동작. 응답 시간 < 10초

---

### Stage 5: 사진 인식 + 채널 관리 (Day 5~6)

> **목표:** 사진→재료 인식, 선호 채널 CRUD 완성

| # | 태스크 | 예상 시간 | 입력 | 산출물 | 검증 |
|---|--------|----------|------|--------|------|
| 5.1 | Vision Service (Gemini 이미지 입력, 재료 인식 + 유사 후보) | 2시간 | 4.1 | `backend/services/vision.py` | 냉장고 사진 → 재료 3개+ 인식 |
| 5.2 | `/v1/ingredients/recognize` 엔드포인트 | 1시간 | 5.1 | `backend/api/ingredients.py` 추가 | base64 이미지 → 재료 JSON |
| 5.3 | `/v1/channels` CRUD 엔드포인트 (검색/추가/삭제) | 1.5시간 | 1.1 | `backend/api/channels.py` | 채널 검색 → 추가 → 목록 → 삭제 |
| 5.4 | User Ingredients CRUD | 1시간 | 1.4 | `backend/api/user_ingredients.py` | 재료 추가/수정/삭제/조회 |
| 5.5 | 전체 API 통합 테스트 (pytest) | 2시간 | 3.4~5.4 | `backend/tests/` | 핵심 시나리오 10개 통과 |

> **✅ 체크포인트 S5:** Swagger UI에서 전체 API 동작. pytest 통과. 백엔드 100% 완성

---

### Stage 6: 프론트엔드 UI (Day 6~8)

> **목표:** 전체 화면 구현 + API 연동

| # | 태스크 | 예상 시간 | 입력 | 산출물 | 검증 |
|---|--------|----------|------|--------|------|
| 6.1 | 공통 레이아웃 + 라우팅 + 디자인 토큰 | 1.5시간 | 0.1 | `frontend/src/app/layout.tsx`, globals.css | 기본 레이아웃 렌더링 |
| 6.2 | S01: 홈/통합 검색 화면 (재료 태그 + 자동완성 + 인원수 + 모드 토글) | 3시간 | 6.1, 3.4~3.5 | `frontend/src/app/page.tsx` + 컴포넌트 | 재료 입력 → API 호출 → 결과 확인 |
| 6.3 | S02: 검색 결과 화면 (영상 카드 그리드 + GAP 뱃지 + 2탭 구조) | 3시간 | 6.2, 3.4 | `frontend/src/app/results/page.tsx` | 내 채널 탭 + YouTube 검색 탭 |
| 6.4 | S03: 레시피 상세 화면 (원본/변환 + 인원수 슬라이더 + GAP 체크리스트) | 3시간 | 6.3, 4.7 | `frontend/src/app/recipe/[id]/page.tsx` | 영상 임베드 + 재료 GAP 표시 |
| 6.5 | S04: 채널 관리 화면 (검색 + 추가/삭제) | 1.5시간 | 6.1, 5.3 | `frontend/src/app/channels/page.tsx` | 채널 검색 → 추가 → 목록 |
| 6.6 | S05: 사진 인식 모달 (업로드 + 결과 + 수정 + 양념 체크) | 2시간 | 6.2, 5.2 | 모달 컴포넌트 | 사진 업로드 → 인식 → 태그 |
| 6.7 | S06: 외부 레시피 입력 모달 (텍스트 붙여넣기) | 1시간 | 6.2, 4.8 | 모달 컴포넌트 | 텍스트 → 구조화 레시피 |
| 6.8 | 에러 상태 + 로딩 + 빈 상태 UI | 2시간 | 6.2~6.7 | 각 화면 엣지케이스 | 모든 화면에서 에러/빈상태 표시 |
| 6.9 | 반응형 + 모바일 최적화 | 1.5시간 | 6.2~6.8 | CSS 수정 | 모바일 360px에서 정상 표시 |

```
📋 에이전트 프롬프트 예시 (6.2):
"FridgeTube 메인 검색 페이지를 만들어줘. Next.js 14 App Router + Tailwind CSS.
구성요소:
1. 큰 검색 입력 필드 (placeholder: '냉장고에 뭐가 있나요? 또는 먹고 싶은 요리를 검색하세요')
2. 입력된 재료 태그 표시 (x 삭제 버튼)
3. 자동완성 드롭다운 (API: /v1/ingredients/search?q=)
4. 인원수 슬라이더 (1~10, 기본 2)
5. 모드 토글 ('영상 추천' / '레시피 변환')
6. 검색 버튼 → /results 페이지로 이동
API 호출은 fetch로, SWR이나 React Query 미사용. 깔끔한 한국어 UI."
```

> **✅ 체크포인트 S6:** 모든 화면 동작. "김치찌개" 검색 → 결과 → 클릭 → 레시피 추출 → GAP 확인 E2E 플로우 완성

---

### Stage 7: 배포 + 안정화 (Day 8~10)

> **목표:** Cloudflare Pages + Render Free 배포 완료, 퍼블릭 접속 가능

| # | 태스크 | 예상 시간 | 입력 | 산출물 | 검증 |
|---|--------|----------|------|--------|------|
| 7.1 | Neon Free PostgreSQL 생성 + 스키마 마이그레이션 | 1시간 | 1.1~1.5 | 클라우드 DB | psql 접속 확인 |
| 7.2 | Upstash Redis 생성 + 연동 테스트 | 30분 | 0.4 | 클라우드 Redis | PING → PONG |
| 7.3 | 시드 데이터 클라우드 DB에 로딩 | 30분 | 1.6~1.8, 7.1 | 데이터 | count 확인 |
| 7.4 | 큐레이션 채널 클라우드 인덱싱 실행 | 30분 | 2.5, 7.1 | channel_video_index 데이터 | 500+ 행 |
| 7.5 | FastAPI → Render Free 배포 | 1시간 | 0.2 | `render.yaml` | api.fridgetube.xxx/docs 접속 |
| 7.6 | Next.js → Cloudflare Pages 배포 | 1시간 | 0.1 | `wrangler.toml` 또는 Git 연동 | fridgetube.pages.dev 접속 |
| 7.7 | 환경변수 설정 (Render + Cloudflare) | 30분 | 0.4 | 각 플랫폼 환경변수 | API 호출 성공 |
| 7.8 | CORS + 프록시 설정 | 30분 | 7.5~7.6 | 프론트→백엔드 통신 | 검색 → 결과 E2E |
| 7.9 | GitHub Actions CI/CD (lint + test + 자동 배포) | 1시간 | 0.5 | `.github/workflows/ci.yml` | push → 자동 배포 |
| 7.10 | Sentry 연동 + 에러 모니터링 | 30분 | 7.5~7.6 | Sentry 프로젝트 | 테스트 에러 → Sentry 수신 |
| 7.11 | 최종 E2E 테스트 (프로덕션 환경) | 1시간 | 7.1~7.10 | 테스트 리포트 | 핵심 플로우 5개 통과 |

> **✅ 체크포인트 S7:** `fridgetube.pages.dev` 접속 → 검색 → 레시피 추출 → GAP 확인. 🚀 **MVP 라이브!**

---

### 전체 태스크 요약

| 스테이지 | 태스크 수 | 예상 시간 | 핵심 산출물 |
|---------|----------|----------|-----------|
| S0: 초기화 | 6 | 2.5h | 실행 가능한 빈 프로젝트 |
| S1: DB + 시드 | 8 | 10.5h | 전체 스키마 + 시드 데이터 |
| S2: 채널 인덱싱 | 7 | 10h | 로컬 검색 동작 |
| S3: 검색 API | 5 | 9h | 통합 검색 엔드포인트 |
| S4: 레시피 추출 | 9 | 15h | Gemini 레시피 추출 E2E |
| S5: 사진+채널 | 5 | 7.5h | 백엔드 100% 완성 |
| S6: 프론트엔드 | 9 | 19h | 전체 UI 완성 |
| S7: 배포 | 11 | 8h | 퍼블릭 라이브 |
| **합계** | **60** | **~81.5h** | **MVP 완성** |

### 에이전트 실행 가이드

**Claude Code로 실행 시 권장 패턴:**

```
1. 스테이지 단위로 작업 (S0 → S1 → ... → S7)
2. 각 태스크 시작 전: "현재 프로젝트 상태를 확인하고, 태스크 X.Y를 실행해줘"
3. 각 태스크 완료 후: "검증 기준에 맞춰 테스트해줘"
4. 체크포인트에서: "S{N} 체크포인트를 실행하고 결과를 알려줘"
5. 중간에 끊기면: "S{N}의 태스크 X.Y부터 이어서 해줘"
```

**끊김 대응 전략:**
- 각 태스크는 **독립 파일**을 생성하므로, 이전 태스크 산출물이 파일 시스템에 남아있음
- 에이전트가 재시작하면 `ls backend/services/` + `ls backend/api/`로 현재 상태 파악 가능
- DB 스키마는 Alembic migration으로 관리되므로, `alembic current`로 상태 확인
- `.env.local`에 모든 키가 있으므로 환경변수 재설정 불필요

---

## 8. 테스트 전략 + CI/CD

### 8.1 테스트 피라미드

| 레벨 | 범위 | 도구 | 커버리지 목표 | 실행 시점 |
|------|------|------|-------------|----------|
| **단위 테스트** | 서비스 로직, 유틸 함수, 분량 변환 로직, 재료 매칭 | pytest (BE), vitest (FE) | 80%+ | 매 커밋 |
| **통합 테스트** | API 엔드포인트, DB 쿼리, 외부 API 모킹 | pytest + httpx (BE), MSW (FE) | 70%+ | PR 머지 시 |
| **E2E 테스트** | 사용자 시나리오 전체 흐름 | Playwright | 핵심 플로우 5개 | 일 1회 + 배포 전 |

### 8.2 핵심 테스트 시나리오

| # | 시나리오 | 타입 | 우선순위 |
|---|---------|------|---------|
| T-01 | 재료 3개 입력 → 영상 10개 반환 → 첫 영상 클릭 → 레시피 카드 표시 | E2E | 필수 |
| T-02 | 인원수 4→2 변경 시 모든 scalable 재료 ÷2, non-scalable 재료 LLM 조절 확인 | Unit | 필수 |
| T-03 | 선호 채널 3개 등록 → 채널 필터 ON → 해당 채널 영상만 반환 | Integration | 필수 |
| T-04 | 냉장고 사진 업로드 → 3개 재료 인식 → 태그 자동 채움 → 수정 → 검색 | E2E | 필수 |
| T-05 | 외부 레시피 텍스트 붙여넣기 → 구조화 레시피 카드 표시 | E2E | 필수 |
| T-06 | 자막 없는 영상 → 적절한 에러 메시지 + fallback | Integration | 필수 |
| T-07 | YouTube API 할당량 초과 시 캐시 결과 반환 | Integration | 높음 |
| T-08 | 동시 100명 검색 시 응답 시간 < 3초 | Performance | 높음 |
| T-09 | Vision API 장애 시 텍스트 입력으로 자연스럽게 전환 | Integration | 보통 |

### 8.3 CI/CD 파이프라인

```
┌─────────────────────────────────────────────────────┐
│                   GitHub Actions                     │
│                                                      │
│  On Push (모든 브랜치):                                │
│    ├─ Lint (ESLint + Ruff)                           │
│    ├─ Type Check (TypeScript + mypy)                 │
│    └─ Unit Tests                                     │
│                                                      │
│  On PR → main:                                       │
│    ├─ 위 전부 +                                       │
│    ├─ Integration Tests (Docker Compose)             │
│    ├─ Build Check (Next.js build + FastAPI + Cloudflare)          │
│    └─ Cloudflare Preview Deploy → 자동 링크 코멘트         │
│                                                      │
│  On Merge → main:                                    │
│    ├─ 위 전부 +                                       │
│    ├─ E2E Tests (Playwright)                         │
│    ├─ Cloudflare Pages Production Deploy                       │
│    ├─ DB Migration (자동)                             │
│    ├─ Sentry Release                                 │
│    └─ Slack 알림 (성공/실패)                            │
│                                                      │
│  Nightly (매일 17:00 KST = 00:00 PT, 쿼터 리셋 직후):    │
│    ├─ E2E 전체 스위트                                  │
│    ├─ YouTube API 할당량 모니터링                       │
│    └─ 인기 레시피 사전 크롤링 배치                       │
└─────────────────────────────────────────────────────┘
```

### 8.4 환경 구성

| 환경 | 목적 | 도메인 | DB |
|------|------|--------|-----|
| Local | 개발 | localhost:3000 | Docker PostgreSQL |
| Preview | PR 리뷰 | {branch}.fridgetube.pages.dev | Neon dev branch |
| Production | 실 서비스 | fridgetube.pages.dev | Neon prod |

---

## 9. 리스크/대응

### 9.1 기술 리스크

| 리스크 | 확률 | 영향 | 대응 | 트리거 |
|--------|------|------|------|--------|
| **YouTube API 쿼터 소진** | **낮음** | 높음 | 채널 인덱싱(1u) 기반 전환 완료. Quota Budgeter(Pacific Time 리셋 기준). 인덱싱 ~300u/일 + commentThreads ~200u/일 | 일일 사용량 > 8,000 units |
| **레시피 자동 추출 성공률 부족** | 중간 | 높음 | v2.4: 설명란(~35%) + 작성자 댓글(~20%) = ~50~60% 커버리지. 나머지는 Flow D(사용자 입력). 사용자 입력 데이터 축적으로 점진 개선 | 자동 추출률 < 40% |
| **비공식 자막 경로 정책 위반** | ~~중간~~ **해소 (v2.4)** | 매우 높음 | 프로덕션 기본 OFF 확정. 코드 존재하나 프로덕션 미사용 입증 가능. 감사 시 환경변수 + 배포 로그로 대응 | N/A (프로덕션 미사용) |
| **YouTube Developer Policies 위반** | 낮음 | 매우 높음 | v2.4 대응: (1) 모든 YouTube API 데이터 테이블 30일 TTL (snapshot + channel_index) (2) search.list 결과 별도 탭, 수정/재정렬 금지 (3) 파생 지표 금지 (4) UI 분리 + 고지 | Google 정책 감사 통보 |
| **LLM API 비용 급증** | 중간 | 중간 | 검색 단계 LLM 없음. 텍스트 압축으로 토큰 절감. 레시피 캐시 적극 활용. 무료 일 3회 제한 | 월 LLM 비용 > $200 |
| **한국어 로컬 검색 품질 부족** | 중간 | 높음 | v2.4: pg_trgm MVP 승격. tsvector + trigram 이중 인덱스로 오타/띄어쓰기 변형 대응 | 검색→클릭률 < 10% |
| **Vision AI 재료 오인식** | 중간 | 중간 | 유사 후보 2~3개 제공. 양념류는 체크 UX. "수정하세요" 강조 | 사용자 수정률 > 40% |

### 9.2 성능 리스크

| 리스크 | 대응 |
|--------|------|
| 레시피 추출 응답 지연 (LLM 5~15초) | 스트리밍 응답 + 프로그레스 UI ("재료 분석 중... → 분량 계산 중... → 완료!") |
| 동시 사용자 급증 | Render Free 자동 슬립 + Cloudflare CDN + Redis 캐시 히트율 90% 목표 + CDN |
| 이미지 업로드 대용량 | 클라이언트 리사이즈 (max 1280px) + WebP 변환 후 전송 |

### 9.3 보안 리스크

| 리스크 | 대응 |
|--------|------|
| API 키 노출 | 서버사이드에서만 외부 API 호출, 환경변수 관리, GitHub Secret Scanning |
| Rate Limit 우회 | IP + 토큰 이중 제한, Cloudflare WAF |
| 사용자 입력 인젝션 | LLM 프롬프트 인젝션 방어 (입력 길이 제한 + 시스템 프롬프트 격리) |
| 이미지 악성 업로드 | 파일 타입 검증 + 서버사이드 리사이즈 + S3 격리 저장 |

### 9.4 일정 리스크

| 리스크 | 확률 | 대응 |
|--------|------|------|
| LLM 프롬프트 튜닝 예상보다 오래 걸림 | 높음 | Week 3부터 병렬 진행. 80% 정확도로 MVP 출시, 이후 점진 개선 |
| 재료 마스터 DB 구축 지연 | 중간 | 공공데이터 (식품영양성분DB) 활용 + 상위 300개만 먼저 |
| 사진 인식 정확도 미달 | 중간 | MVP에서 "베타" 뱃지 표시, 텍스트 입력을 기본으로 유지 |

### 9.5 기술 부채 관리

| 예상 부채 | 발생 시점 | 해소 시점 | 해소 방법 |
|----------|----------|----------|----------|
| 하드코딩된 프롬프트 | MVP | Phase 2 초 | 프롬프트 관리 시스템 (버전 관리 + A/B 테스트). `prompt_version` 필드로 추적 가능 |
| 비공식 자막 코드 잔존 | MVP | Phase 2 | 자체 ASR(Whisper) 확보 시 코드 완전 제거. 현재 프로덕션 OFF + 환경변수 격리 |
| typical_ingredients 기반 예상 GAP | MVP | Phase 2 | 캐시된 레시피 기반 정확 GAP으로 전환 (인기 레시피 사전 추출) |
| 채널 인덱스 수동 큐레이션 | MVP | Phase 2 | 사용자 추가 채널 자동 인덱싱 + 인기 채널 자동 발견 |
| search.list 별도 탭 분리 UX | MVP | Phase 2 | 쿼터 증액 심사 통과 후 통합 UI 검토. 또는 search.list 완전 제거 |
| 모노리스 FastAPI | MVP | Phase 3 | 서비스 분리 (영상검색 / 레시피추출 / 사용자) |

---

## 10. Claude Code 에이전트 실행 가이드

### 시작 전 준비 (사람이 해야 할 것)

**⚠️ 아래 3가지는 Claude Code가 할 수 없으므로, 에이전트 실행 전에 사람이 준비합니다.**

- [ ] Google Cloud Console → YouTube Data API v3 키 발급 + Gemini API 키 발급 (AI Studio)
- [ ] Neon.tech 가입 → Free PostgreSQL 생성 → CONNECTION_STRING 확보
- [ ] Upstash 가입 → Free Redis 생성 → REDIS_URL 확보

준비 완료 후 `.env.local`에 키를 채우고 첫 에이전트 세션을 시작합니다.

### 에이전트 세션 계획

아래와 같이 **세션을 나눠서** Claude Code를 실행합니다. 각 세션은 독립적이므로 중간에 끊겨도 다음 세션부터 재개 가능합니다.

| 세션 | 스테이지 | 예상 시간 | 시작 프롬프트 |
|------|---------|----------|-------------|
| 1 | S0 (초기화) | 2.5h | "FridgeTube 프로젝트를 초기화해줘. Next.js 14 + FastAPI + Docker Compose." |
| 2 | S1 (DB) | 10.5h | "이전에 만든 FridgeTube 백엔드에 SQLAlchemy 모델과 시드 데이터를 추가해줘." |
| 3 | S2 (인덱싱) | 10h | "YouTube 채널 인덱싱 서비스를 만들어줘. playlistItems 기반." |
| 4 | S3 (검색 API) | 9h | "통합 검색 API를 만들어줘. Query Classifier + 역방향 추론 + GAP." |
| 5 | S4 (레시피) | 15h | "Gemini 2.0 Flash로 레시피 추출 서비스를 만들어줘." |
| 6 | S5 (부가 API) | 7.5h | "사진 인식 + 채널 관리 + 사용자 재료 API를 완성해줘." |
| 7 | S6 (프론트) | 19h | "FridgeTube 프론트엔드 전체 UI를 만들어줘. 7개 화면." |
| 8 | S7 (배포) | 8h | "Cloudflare Pages + Render Free에 배포해줘." |

### 세션 간 끊김 복구 프롬프트

```
"FridgeTube 프로젝트 현재 상태를 확인해줘.
1. ls backend/services/ 로 완성된 서비스 목록 확인
2. ls backend/api/ 로 완성된 API 목록 확인
3. ls frontend/src/app/ 로 완성된 화면 목록 확인
4. alembic current 로 DB 마이그레이션 상태 확인
5. 어디까지 완료되었는지 알려주고, 다음 태스크부터 이어서 진행해줘."
```

### $0 스택 요약 (v3.0)

| 구성 | 서비스 | 비용 | 한도 |
|------|--------|------|------|
| FE 호스팅 | Cloudflare Pages | $0 | 무제한 대역폭, 상업 가능 |
| BE 호스팅 | Render Free | $0 | 750h/월, 콜드스타트 ~30초 |
| DB | Neon Free PostgreSQL | $0 | 512MB, pg_trgm 지원 |
| 캐시 | Upstash Redis Free | $0 | 10K 명령/일 |
| LLM | Gemini 2.0 Flash | $0 | 1,500 RPD, 15 RPM |
| Vision | Gemini 2.0 Flash | $0 | 이미지 입력 포함 |
| YouTube | YouTube Data API v3 | $0 | 10,000 units/일 |
| CI/CD | GitHub Actions | $0 | 2,000분/월 |
| 모니터링 | Sentry Free | $0 | 5K 이벤트/월 |
| **합계** | | **$0/월** | |

---

## 부록 A: 가정 변경 영향 분석

| 가정 | 현재 값 | 변경 시나리오 | 영향 |
|------|---------|-------------|------|
| LLM 모델 | Gemini 2.0 Flash (무료) | Gemini 정확도 80% 미달 시 | Claude Haiku($1/$5 MTok)로 전환, 월 $15~30 발생. 프롬프트 재작성 1~2일 |
| LLM 모델 | Gemini 2.0 Flash (무료) | Gemini 무료 티어 폐지/축소 시 | 즉시 Claude Haiku 전환. 또는 Gemini 유료($0.075/$0.30 per MTok)로 월 $5~15 |
| 검색 아키텍처 | 채널 인덱싱 + search.list 보조 | search.list 완전 제거 | 쿼터 안정화 ↑↑, 채널 밖 영상 커버리지 ↓ |
| 자막 경로 | 설명란 + 작성자 댓글 (공식) | 자동 추출 커버리지 60% 미달 시 | Flow D(사용자 입력) 강화 UX 또는 자체 ASR(Whisper, $100+/월) |
| 호스팅 | Cloudflare Pages + Render Free | Render 콜드스타트(~30초) 불만 시 | Railway($5 크레딧) 또는 Fly.io Free로 전환 |
| DB | Neon Free (512MB) | 스토리지 512MB 초과 시 | Neon Pro($19/월) 또는 오래된 channel_video_index 정리 |
| 인덱싱 채널 수 | MVP 20~30채널 | 100+ 채널로 확장 | 인덱싱 배치 쿼터 ~1,000u/일, 자동 발견 시스템 필요 |
| YouTube 정책 | 30일 캐시 TTL 준수 | Google이 더 엄격한 감사 요구 | youtube_video_snapshot + channel_video_index 즉시 삭제 |
| 외부 레시피 입력 | 텍스트 붙여넣기만 | URL 스크래핑 추가 | 사이트별 파서 개발 (0.5일/사이트), 저작권 법무 검토 |

## 부록 B: 경쟁사 분석 (v2.3 업데이트)

### 직접 경쟁 — "재료 → YouTube 레시피" 서비스

| 서비스 | 시장 | 핵심 기능 | FridgeTube 차별점 |
|--------|------|----------|------------------|
| **냉쿡** (iOS) | 한국 | 재료 입력 → 유튜브 영상 추천, 필수/있는/없는/대체 재료 분석, 채널 필터 | **가장 직접적 경쟁자.** 차별화 필요: 수량 기반 정밀 GAP, scaling_strategy, 외부 레시피 허브 |
| **냉파고** (iOS) | 한국 | 재료 입력 → 유튜브 영상 + AI 요약, 중복 없는 레시피 영상 | AI 요약 제공. FridgeTube는 구조화 레시피 + 분량 변환이 차별점 |
| **Video2Recipe** | 글로벌 | YouTube/Instagram/TikTok → 레시피 변환 | 재료 기반 검색/GAP 없음. FridgeTube는 "검색+변환+GAP" 통합 |
| **RecipeBro** | 글로벌 | YouTube 레시피 import + AI 추출 | 개인 레시피 관리 중심. FridgeTube는 "지금 만들 수 있는 것" 중심 |

### 간접 경쟁 — 재료 기반 레시피 추천

| 서비스 | 시장 | FridgeTube 차별점 |
|--------|------|------------------|
| 냉장고파먹기 / 만개의레시피 | 한국 | 자체 DB 기반 (정적). FridgeTube는 YouTube 실시간 콘텐츠 + AI 추출 |
| SuperCook | 글로벌 | 영상 없음, 텍스트 레시피만. FridgeTube는 영상 + 구조화 레시피 |

### v2.3 차별화 전략 (경쟁 대응)

냉쿡이 이미 유사 포지셔닝을 잡고 있으므로, **아이디어 유일성이 아닌 실행 품질**로 차별화해야 합니다.

| 차별화 축 | 설명 | 우선순위 |
|----------|------|---------|
| **정밀 GAP 분석** | UNKNOWN_QTY 포함 5단계 상태, 수량 비교, 장보기 리스트 | P0 (MVP 코어) |
| **분량 스케일링 신뢰성** | scaling_strategy(linear/stepwise/to_taste/fixed) | P0 (MVP 코어) |
| **선호 채널 인덱싱** | 큐레이션 + 사용자 채널 기반 고품질 추천 (쿼터 효율적) | P0 (MVP 코어) |
| **YouTube 의존 탈피** | 텍스트/OCR/URL로 데이터 소스 다변화 → "모든 레시피의 허브" | P1 (Phase 2) |

---

*문서 끝. 본 문서는 개발 진행에 따라 주간 업데이트됩니다.*
