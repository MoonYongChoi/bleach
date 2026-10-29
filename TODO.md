# BLEACH 개발 TODO

> 기준 문서: `suggestions.md` (서비스 기획안) + 디자인 시안(Main/FilterSheet/Skeleton/EmptyState)
> 컨셉: 블로그 + 리뷰 + 서치 — 산발된 체험단 정보를 모아보는 서비스

---

## 0. 프로젝트 셋업

- [x] GitHub 레포지토리 생성 및 `git init`
- [x] Next.js 14+ (App Router) 프로젝트 생성
- [x] Tailwind CSS 설치 및 설정
- [x] shadcn/ui 설치 및 기본 컴포넌트(Button, Input, Sheet, Skeleton 등) 추가
- [x] Supabase 프로젝트 생성 (DB/Auth/REST API)
- [x] `.env.local` 환경변수 설정 (Supabase URL, anon key, DB 연결 문자열)
- [ ] Vercel 프로젝트 연동 (GitHub 레포 연결, 프리뷰 배포 확인)
- [x] 폰트(Noto Sans KR 등) 적용 — shadcn init 시 자동 반영

---

## 1주차 — AI 기반 MVP 개발

### Day 1: DB 스키마 & 파싱 규격 확정
- [x] Supabase `campaigns` 테이블 설계 (`supabase/schema.sql`)
  - [x] `platform` (레뷰/파블로/리뷰노트)
  - [x] `title` (체험단명/제목)
  - [x] `region_sido`, `region_gugun` (지역/위치)
  - [x] `deadline_date`, `announce_date` (마감일/발표일)
  - [x] `source_url` (원문 URL, Outlink — unique 키로 upsert 기준)
  - [x] `category` (맛집/뷰티/배송 등 — `src/lib/categories.ts`에 표준 8종 + 원본→표준 매핑)
  - [x] `created_at`, `updated_at`, `is_active`
- [x] 레뷰/파블로/리뷰노트 3곳 목록 페이지 구조 조사 및 셀렉터 정리 (각 스크래퍼 파일 상단 주석 참고)
- [x] 수집 데이터 → 표준 스키마 매핑 규칙 문서화

### Day 2~3: 스크래퍼 개발
- [x] Python + Playwright 환경 구성 (`scraper/.venv`, `requirements.txt`)
- [x] 레뷰(Revu) 스크래퍼 작성 — `scraper/revu_scraper.py` (로그인 필요, Playwright)
- [x] 파블로(Pavlovu) 스크래퍼 작성 — `scraper/pavlovu_scraper.py` (requests+BeautifulSoup)
- [x] 리뷰노트(Reviewnote) 스크래퍼 작성 — `scraper/reviewnote_scraper.py` (requests, `__NEXT_DATA__` 파싱)
- [x] Supabase에 upsert하는 적재 스크립트 작성 — `scraper/loader.py` (`source_url` 기준 ON CONFLICT)
- [x] GitHub Actions 워크플로 작성 — `.github/workflows/scrape.yml` (하루 4회: 09:30/15:30/21:30/03:30 KST)
  - [ ] GitHub repo secrets 등록 필요: `DATABASE_URL`, `REVU_ID`, `REVU_PW`
- [x] 플랫폼별 데이터 정제 레이어 — `scraper/normalize.py` (제목/마감일(KST)/인원/이미지/표준 8종 분류/지역/유형) + `scraper/tests/`
  - [x] 품질 리포트: `python run_all.py --dry-run`(수집 직후), `python quality.py`(DB)
  - [x] `supabase/migrations/20261029_normalize_fields.sql` 실행 (category_raw, campaign_type 컬럼) + `backfill.py`로 기존 행 재정제
  - [ ] 파블로 기자단 카드 제목 셀렉터 수정 (현재 제목 자리에 "5,000포인트" 같은 보상이 잡힘 → 비활성 처리 중)
  - [ ] 파블로 상세페이지 마감일 파싱 점검 (기존 행 마감일 채움률 3.9%)
- [x] 커넥터 구조 (`scraper/connectors/`) — 새 플랫폼은 Connector 파일 1개 + `connectors/__init__.py` 등록 1줄
- [x] 캠페인 유형(방문/배송/구매/기자단/재택) + 리뷰 채널(`review_channels`: 블로그/인스타/릴스/유튜브/쇼츠/틱톡/클립) 수집·정제
  - [ ] 실제 페이지로 채널 셀렉터 확인 (파블로 `.pvc_pl i`, 레뷰 카드 아이콘 alt, 리뷰노트 `channel` 값 종류)
- [ ] `platforms` 테이블 + `campaigns.platform`을 키(revu 등)로 전환, 프론트 PLATFORMS 상수 제거
- [x] 신규 커넥터: 디너의여왕, 모두블로그
- [ ] 보류: 서울오빠·강남맛집 — GitHub(해외) 서버에서 접속이 막힘. 필요하면 Vercel 서울 리전 경유 수집으로 재검토 (서울오빠 커넥터는 git 기록에 있음)
- [ ] `scrape_runs` 수집 기록 테이블 + Actions를 커넥터별 matrix로 분리
- [ ] 크롤링 실패/차단 대응 로직(재시도, 로그) 보강 — 현재는 플랫폼별 try/except로 한 곳 실패해도 나머지는 계속 진행하는 수준

### Day 4~5: 모바일 UI 컴포넌트 제작
- [ ] 헤더 컴포넌트 (로고 + 태그라인 "블로그 체험단 서치" + 검색 입력)
- [ ] 퀵 필터 칩 컴포넌트 (지역/카테고리/마감임박순)
- [ ] 체험단 리스트 카드 컴포넌트 (플랫폼 배지 + D-day + 제목 + 지역/일정)
- [ ] 인피드 네이티브 광고 카드 컴포넌트 (AD 라벨 포함)
- [ ] 하단 고정 배너 컴포넌트
- [ ] 필터 바텀시트 컴포넌트 (지역/카테고리/마감임박순 탭 + 칩 선택 + 적용/초기화)
- [ ] 스켈레톤 로딩 컴포넌트
- [ ] Empty State 컴포넌트 (결과 없음)

### Day 6: 데이터 연동 & 기능 구현
- [ ] Supabase REST API 연동 (목록 조회 쿼리)
- [ ] 지역/카테고리/마감임박순 필터링 로직 구현
- [ ] 검색어 Debounce(0.3s) 구현
- [ ] 무한 스크롤(Infinite Scroll) 구현
- [ ] URL Query Parameter 기반 필터 상태 저장/복원 구현 (`?region=&category=&sort=`)
- [ ] 외부 플랫폼 Outlink 클릭 트래킹(선택)

### Day 7: 1차 동작 테스트
- [ ] 전체 플로우 테스트 (크롤링 → DB 적재 → 프론트 노출)
- [ ] iOS/Android 모바일 웹 1차 점검
- [ ] 1주차 마감 체크리스트 정리

---

## 2주차 — UI/UX 고도화

- [ ] Bottom Sheet 필터 UX 다듬기 (한 손 조작, 애니메이션)
- [ ] Skeleton 로딩 타이밍/표시 조건 보완
- [ ] Empty State 문구/CTA 보완
- [ ] 인피드 광고(5번째/10번째 카드) 위치 로직 구현
- [ ] 하단 고정 배너 레이아웃 고정 및 실제 광고 SDK 연동 준비 (카카오 애드핏/구글 애드센스)
- [ ] 실기기(iOS/Android) QA — 터치 영역, 패딩, 세이프 에리어
- [ ] 접근성 점검 (명도 대비, 포커스 이동, aria-label)

---

## 3주차 — 실배포 & 홍보

- [ ] Vercel 프로덕션 배포
- [ ] 커스텀 도메인 연동
- [ ] 메타 태그/OG 이미지/SEO 기본 설정
- [ ] 피드백 수집용 Google Form 제작
- [ ] 블로거 제안서 메시지 템플릿 최종화 (`suggestions.md` 4.1 참고)
- [ ] 체험단 리뷰 상위 블로거 20~30명 리스트업
- [ ] 1차 홍보 메시지 발송 (블로그 안부글/쪽지/이메일)

---

## 4주차 — 피드백 반영 & 광고 신청 & 회고

- [ ] 수집된 피드백 정리 및 우선순위화
- [ ] UX/검색 속도 개선 패치 적용
- [ ] 트래픽 확인 후 카카오 애드핏 심사 신청
- [ ] 트래픽 확인 후 구글 애드센스 심사 신청
- [ ] B2B 스폰서십([추천 체험단] 영역) 노출 구조 설계(선택, 2차 확장)
- [ ] KPT(Keep/Problem/Try) 회고 진행 및 문서화

---

## R&R (역할 분담)

- **PM/UIUX**: 와이어프레임, 블로거 제안서, 피드백 폼
- **AI Developer**: 스크래퍼, Next.js + Supabase 구축, 배포
