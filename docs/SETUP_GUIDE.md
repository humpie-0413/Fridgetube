# FridgeTube 사전 준비 가이드

> **이 가이드의 모든 작업은 사람이 직접 해야 합니다.**
> Claude Code가 할 수 없는 외부 서비스 가입/키 발급입니다.
> 모든 준비가 완료된 후 Claude Code를 실행하세요.

---

## 1단계: 필수 도구 설치 확인

Windows Git Bash에서 아래 명령이 모두 동작하는지 확인:

```bash
node --version      # v18+ 필요
npm --version       # v9+ 필요
python --version    # 3.12+ 권장
pip --version
git --version
docker --version    # Docker Desktop 설치 필요
claude --version    # Claude Code CLI
```

없는 것이 있으면 먼저 설치:
- Node.js: https://nodejs.org/ (LTS)
- Python: https://www.python.org/downloads/ (3.12+)
- Docker Desktop: https://www.docker.com/products/docker-desktop/
- Claude Code: `npm install -g @anthropic-ai/claude-code`

---

## 2단계: API 키 발급 (15~20분)

### ① YouTube Data API v3
1. https://console.cloud.google.com/ 접속 → 로그인
2. 새 프로젝트 생성 ("FridgeTube")
3. "API 및 서비스" → "라이브러리" → "YouTube Data API v3" 검색 → **사용 설정**
4. "API 및 서비스" → "사용자 인증 정보" → **API 키 만들기**
5. 키 복사 → `.env.local`의 `YOUTUBE_API_KEY`에 붙여넣기

### ② Google Gemini API
1. https://aistudio.google.com/apikey 접속
2. **Create API Key** 클릭
3. 키 복사 → `.env.local`의 `GEMINI_API_KEY`에 붙여넣기

### ③ Neon PostgreSQL (Free)
1. https://neon.tech/ 접속 → 가입
2. **Create Project** → 이름: "fridgetube", Region: Asia (Singapore)
3. Connection string 복사 (postgresql://...)
4. 주의: `postgresql://`를 `postgresql+asyncpg://`로 변경
5. → `.env.local`의 `DATABASE_URL`에 붙여넣기

### ④ Upstash Redis (Free)
1. https://upstash.com/ 접속 → 가입
2. **Create Database** → 이름: "fridgetube", Region: AP-Northeast-1
3. REST URL이 아닌 **Redis URL** (redis://...) 복사
4. → `.env.local`의 `REDIS_URL`에 붙여넣기

### ⑤ Sentry (Free, 선택)
1. https://sentry.io/ 접속 → 가입
2. 프로젝트 생성 (Python + Next.js)
3. DSN 복사 → `.env.local`의 `SENTRY_DSN`에 붙여넣기

---

## 3단계: 프로젝트 폴더 생성

```bash
# 원하는 위치에 프로젝트 폴더 생성
mkdir fridgetube
cd fridgetube

# Git 초기화
git init

# 스타터킷 파일 복사 (이 패키지의 파일들을 모두 여기로)
# CLAUDE.md, .claude/, .env.example, docs/ 등

# 환경변수 설정
cp .env.example .env.local
# .env.local을 열어서 2단계에서 발급한 키를 모두 입력
```

---

## 4단계: Claude Code 실행

```bash
# 프로젝트 루트에서
cd fridgetube

# Claude Code 시작 (Max 5x 사용)
claude

# 첫 명령:
# "CLAUDE.md를 읽고 Stage 0부터 순서대로 실행해줘.
#  각 태스크 완료 시 검증하고, 스테이지 체크포인트를 확인해줘."
```

---

## 5단계: 스테이지별 실행 가이드

### 세션 분리 권장 (토큰 절약)

| 세션 | 스테이지 | 시작 프롬프트 |
|------|---------|-------------|
| 1 | S0 | "CLAUDE.md를 읽고 Stage 0(프로젝트 초기화)를 실행해줘." |
| 2 | S1 | "Stage 1(DB + 시드 데이터)를 실행해줘. .claude/skills/db-schema.md를 참조해." |
| 3 | S2 | "Stage 2(YouTube 채널 인덱싱)를 실행해줘." |
| 4 | S3 | "Stage 3(검색 API + Query Classifier)를 실행해줘." |
| 5 | S4 | "Stage 4(Gemini 레시피 추출)를 실행해줘." |
| 6 | S5 | "Stage 5(사진 인식 + 부가 API + 테스트)를 실행해줘." |
| 7 | S6 | "Stage 6(프론트엔드 UI)를 실행해줘. .claude/skills/ui-screens.md 참조." |
| 8 | S7 | "Stage 7(배포)를 실행해줘. Cloudflare Pages + Render Free." |

### 중간에 끊겼을 때

```
"프로젝트 현재 상태를 확인해줘.
ls backend/services/ 와 ls backend/api/ 로 완성된 파일 확인하고,
어디까지 완료되었는지 알려줘. 다음 태스크부터 이어서 진행해."
```

---

## 체크리스트

- [ ] Node.js 18+ 설치됨
- [ ] Python 3.12+ 설치됨
- [ ] Docker Desktop 설치 + 실행 중
- [ ] Claude Code 설치됨 (`claude --version`)
- [ ] YouTube Data API v3 키 발급 완료
- [ ] Gemini API 키 발급 완료
- [ ] Neon PostgreSQL 생성 완료
- [ ] Upstash Redis 생성 완료
- [ ] `.env.local` 파일에 모든 키 입력 완료
- [ ] 프로젝트 폴더에 CLAUDE.md + .claude/ 폴더 존재

**모든 항목 체크 완료 후 Claude Code를 실행하세요!**
