This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## 광고 (쿠팡 파트너스)

코드는 `src/lib/ads.ts`, `src/components/coupang-slot.tsx`. 캠페인 8개마다 쿠팡 파트너스 다이나믹 배너(320×100) 한 칸을
넣고, 무한 스크롤로 내리는 동안 계속 넣는다. 각 칸에는 "광고" 표시와 수수료 고지 문구가 붙는다.

- 배너 코드는 iframe(srcdoc) 안에서 그대로 돌린다 — 쿠팡 스크립트가 우리 페이지 문서를 건드리지 않게.
- `NEXT_PUBLIC_COUPANG_ID=off`로 끈다. 배너를 바꾸면 `NEXT_PUBLIC_COUPANG_ID` / `NEXT_PUBLIC_COUPANG_TRACKING`.
- **호스팅 약관**: Vercel Hobby(무료)는 비상업적 사용만 허용한다. 제휴 수수료도 상업적 이용이라 Pro 플랜이 필요하다.
- **수집 대상 사이트의 약관·robots**: 수익이 생기면 법적 위험이 달라진다.
- 구글 애드센스는 2026-11-12에 뺐다 (git 기록에 남아 있음).

## 관리 페이지 (/admin)

수집 현황(플랫폼별 상태, 수집 회차별 결과, 새 캠페인이 들어온 시각)을 보는 페이지. Basic 인증으로 막혀 있다.

- Vercel 환경변수 `ADMIN_PASSWORD`(필수), `ADMIN_USER`(선택, 기본 `admin`)
- `ADMIN_PASSWORD`가 없으면 /admin은 404
- 이용 기록: `/admin/logs`(원본 기록 — 조건 조회·CSV), `/admin/logs/summary`(요약). 원본은 공개 키로 못 읽게 막혀 있어
  Vercel 환경변수 `SUPABASE_SERVICE_ROLE_KEY`(Supabase → Project Settings → API Keys의 service_role/secret 키, 서버 전용)가 필요하다.
  자유로운 쿼리는 Supabase SQL 편집기에서 `access_logs`를 조회한다.
- 수집 회차 기록은 `scraper/run_all.py`가 `scrape_runs` 테이블에 남긴다 (`supabase/migrations/20261105_scrape_runs.sql`)

## 서울오빠 수집 (가정용 PC)

서울오빠는 데이터센터 IP(GitHub Actions, Vercel 서울 리전)의 접속을 막아 정기 수집에서 빠져 있다 (`local_only`).
집·사무실 PC에서 따로 돌린다.

```bash
git clone https://github.com/MoonYongChoi/bleach.git && cd bleach/scraper
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# 저장소 루트의 .env.local 에 DATABASE_URL=... (Supabase → Connect → Session pooler 주소)
python run_all.py --only seoulouba --dry-run   # 수집·정제만, DB에 안 씀
python run_all.py --only seoulouba             # 적재 (/admin 수집 회차에 기록됨)
python reaper.py --only seoulouba --apply      # 목록에서 빠진 캠페인 종료 처리
```

하루 몇 번 돌리려면 cron(Mac/Linux) 또는 작업 스케줄러(Windows)에 위 적재 명령을 등록한다.
